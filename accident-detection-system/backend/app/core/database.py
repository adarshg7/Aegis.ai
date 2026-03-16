"""
Async SQLAlchemy engine with PostGIS, TimescaleDB, and pgvector support.
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from app.core.config import settings

log = structlog.get_logger(__name__)


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency that provides a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Initialize database extensions and tables.
    Called on application startup.
    """
    async with engine.begin() as conn:
        # Enable PostGIS for geospatial support
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        # Enable TimescaleDB for time-series
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE"))
        # Enable pgvector for AI embedding similarity search
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Enable UUID generation
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        log.info("database.initialized", extensions=["postgis", "timescaledb", "vector"])


async def close_db():
    """Dispose of the connection pool gracefully."""
    await engine.dispose()
    log.info("database.closed")
