"""
Database Connection Management

Provides async database connectivity using SQLAlchemy and asyncpg.
"""

import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from sqlalchemy import text

from .models import Base

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[async_sessionmaker] = None


def get_database_url(config) -> str:
    """
    Construct database URL from config.
    
    Args:
        config: DatabaseConfig object
        
    Returns:
        Database URL string
    """
    return (
        f"postgresql+asyncpg://{config.user}:{config.password}"
        f"@{config.host}:{config.port}/{config.database}"
    )


async def init_db(config, echo: bool = False) -> AsyncEngine:
    """
    Initialize database connection pool.
    
    Args:
        config: DatabaseConfig object
        echo: Whether to echo SQL statements
        
    Returns:
        AsyncEngine instance
    """
    global _engine, _async_session_factory
    
    if _engine is not None:
        logger.warning("Database already initialized, returning existing engine")
        return _engine
    
    database_url = get_database_url(config)
    
    # Create async engine
    _engine = create_async_engine(
        database_url,
        echo=echo,
        poolclass=AsyncAdaptedQueuePool,
        pool_size=config.pool_size,
        max_overflow=config.max_overflow,
        pool_pre_ping=True,  # Enable connection health checks
        pool_recycle=3600,   # Recycle connections after 1 hour
    )
    
    # Create session factory
    _async_session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    logger.info(f"Database connection pool initialized: {config.host}:{config.port}/{config.database}")
    
    return _engine


async def create_tables():
    """
    Create all tables defined in models.
    
    Note: In production, use Alembic migrations instead.
    """
    global _engine
    
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created successfully")


async def drop_tables():
    """
    Drop all tables defined in models.
    
    Warning: This will delete all data!
    """
    global _engine
    
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    logger.warning("Database tables dropped")


async def close_db():
    """Close database connection pool."""
    global _engine, _async_session_factory
    
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
        logger.info("Database connection pool closed")


def get_db_engine() -> AsyncEngine:
    """
    Get the global database engine.
    
    Returns:
        AsyncEngine instance
        
    Raises:
        RuntimeError: If database not initialized
    """
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _engine


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session.
    
    Yields:
        AsyncSession instance
        
    Example:
        async with get_async_session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
    """
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_health() -> bool:
    """
    Check database connectivity.
    
    Returns:
        True if database is reachable, False otherwise
    """
    try:
        async with get_async_session() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def get_db_stats() -> dict:
    """
    Get database statistics.
    
    Returns:
        Dictionary with connection pool stats
    """
    if _engine is None:
        return {"status": "not_initialized"}
    
    pool = _engine.pool
    
    return {
        "status": "initialized",
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total_connections": pool.size() + pool.overflow(),
    }

