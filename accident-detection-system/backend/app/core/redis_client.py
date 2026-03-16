"""
Redis client singleton (asyncio-compatible).
Used for: caching, pub/sub, session store, rate-limit counters.
"""
import structlog
from redis.asyncio import ConnectionPool, Redis
from app.core.config import settings

log = structlog.get_logger(__name__)

_pool: ConnectionPool = None
_redis: Redis = None


async def get_redis() -> Redis:
    global _pool, _redis
    if _redis is None:
        _pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=50,
            decode_responses=True,
        )
        _redis = Redis(connection_pool=_pool)
        await _redis.ping()
        log.info("redis.connected")
    return _redis


async def close_redis():
    global _redis, _pool
    if _redis:
        await _redis.aclose()
        _redis = None
    if _pool:
        await _pool.aclose()
        _pool = None
    log.info("redis.closed")
