"""
FastAPI application entry point.
Configures middleware, routes, lifespan, observability.
"""
import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.redis_client import get_redis, close_redis
from app.core.kafka_client import get_producer, stop_producer
from app.api import auth, accidents, websocket_routes
import structlog

# ── Structured logging ───────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]
)
log = structlog.get_logger(__name__)

# ── Rate limiter ─────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


# ── Lifespan ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup.begin", env=settings.APP_ENV)
    await init_db()
    await get_redis()
    await get_producer()

    # Start Kafka consumer for AI engine events in background
    from app.core.kafka_client import consume_loop
    from app.services.accident_service import AccidentService
    from app.core.database import AsyncSessionLocal

    stop_event = asyncio.Event()

    async def handle_ai_event(event: dict):
        async with AsyncSessionLocal() as db:
            svc = AccidentService(db)
            await svc.create_accident(
                lat=event["lat"],
                lon=event["lon"],
                severity=event.get("severity", "HIGH"),
                source="AI_CAMERA",
                confidence_score=event.get("confidence"),
                camera_id=event.get("camera_id"),
                screenshot_url=event.get("screenshot_url"),
                ai_model_version=event.get("model_version"),
                metadata=event.get("metadata"),
            )

    consumer_task = asyncio.create_task(
        consume_loop(settings.KAFKA_ACCIDENT_TOPIC, "backend-processor", handle_ai_event, stop_event)
    )

    log.info("startup.complete")
    yield

    # Shutdown
    stop_event.set()
    consumer_task.cancel()
    await close_redis()
    await stop_producer()
    await close_db()
    log.info("shutdown.complete")


# ── App factory ──────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Advanced AI Accident Detection System — Government & Driver Platform",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

# ── Middleware ───────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def request_logger(request: Request, call_next):
    response = await call_next(request)
    log.info(
        "http.request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        ip=request.client.host if request.client else None,
    )
    return response


# ── Routes ───────────────────────────────────────────────────────────
API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(accidents.router, prefix=API_PREFIX)
app.include_router(websocket_routes.router)


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "ws_connections": ws_manager.active_connections_count,
    }


# ── Prometheus metrics ───────────────────────────────────────────────
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Import for health endpoint
from app.websocket.manager import ws_manager
