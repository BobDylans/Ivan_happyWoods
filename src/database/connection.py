"""
Database Connection Management

Provides async database connectivity using SQLAlchemy and asyncpg.
"""

import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
# 导入相关的信息
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy import text

from .models import Base

logger = logging.getLogger(__name__)


# 将数据库的url进行拼接，生成具体可用的url
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

# 初始化数据库连接池
async def init_db(config, echo: bool = False) -> tuple[Optional[AsyncEngine], Optional[async_sessionmaker]]:
    """
    Initialize database connection pool with auto-fallback support.

    Args:
        config: DatabaseConfig object
        echo: Whether to echo SQL statements

    Returns:
        Tuple of (AsyncEngine, async_sessionmaker) if successful,
        (None, None) if connection failed

    Note:
        不再使用全局变量。引擎和会话工厂应该存储到 app.state。
        使用 core.dependencies.get_db_engine() 和 get_db_session() 获取实例。
    """
    try:
        # 调用方法获取到url
        database_url = get_database_url(config)

        # Create async engine
        engine = create_async_engine(
            # 将相关参数带入，创建数据库引擎
            database_url,
            echo=echo,
            poolclass=AsyncAdaptedQueuePool,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_pre_ping=True,  # Enable connection health checks
            pool_recycle=3600,   # Recycle connections after 1 hour
            connect_args={"timeout": 5}  # 5秒连接超时
        )

        # 测试连接
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        # Create session factory
        session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        logger.info(f"✅ Database connection pool initialized: {config.host}:{config.port}/{config.database}")
        return engine, session_factory

    except Exception as e:
        logger.warning(f"⚠️ Database connection failed: {e}")
        logger.info("📝 System will fallback to memory-only mode")
        return None, None

# 根据项目中的类来创建对应的数据库表
async def create_tables(engine: AsyncEngine):
    """
    Create all tables defined in models.

    Args:
        engine: AsyncEngine instance

    Note: In production, use Alembic migrations instead.
    """
    # 🔧 确保 CheckpointModel 被导入，以便 Base.metadata.create_all 能创建表
    try:
        from .checkpointer import CheckpointModel  # noqa: F401
        logger.debug("CheckpointModel imported for table creation")
    except ImportError as e:
        logger.warning(f"Could not import CheckpointModel: {e}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database tables created successfully")


async def drop_tables(engine: AsyncEngine):
    """
    Drop all tables defined in models.

    Args:
        engine: AsyncEngine instance

    Warning: This will delete all data!
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    logger.warning("Database tables dropped")


async def close_db(engine: AsyncEngine):
    """
    Close database connection pool.

    Args:
        engine: AsyncEngine instance
    """
    if engine is not None:
        await engine.dispose()
        logger.info("Database connection pool closed")


# ============================================================================
# 向后兼容的辅助函数（将被弃用）
# ============================================================================

def get_db_engine() -> AsyncEngine:
    """
    [已弃用] 获取全局数据库引擎

    警告：此函数仅用于向后兼容，未来版本将移除。
    请使用 core.dependencies.get_db_engine() 通过依赖注入获取引擎。

    Raises:
        RuntimeError: 始终抛出，因为不再使用全局变量
    """
    raise RuntimeError(
        "get_db_engine() is deprecated and no longer uses global state. "
        "Use core.dependencies.get_db_engine(request) with dependency injection instead."
    )


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    [已弃用] 获取异步数据库会话

    警告：此函数仅用于向后兼容，未来版本将移除。
    请使用 core.dependencies.get_db_session() 通过依赖注入获取会话。

    Raises:
        RuntimeError: 始终抛出，因为不再使用全局变量
    """
    raise RuntimeError(
        "get_async_session() is deprecated and no longer uses global state. "
        "Use core.dependencies.get_db_session(request) with dependency injection instead."
    )
    yield  # This line will never be reached, but needed for type checking


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    [已弃用] FastAPI 依赖函数

    警告：此函数仅用于向后兼容，未来版本将移除。
    请使用 core.dependencies.get_db_session() 通过依赖注入获取会话。

    Raises:
        RuntimeError: 始终抛出，因为不再使用全局变量
    """
    raise RuntimeError(
        "get_session() is deprecated and no longer uses global state. "
        "Use core.dependencies.get_db_session(request) with dependency injection instead."
    )
    yield  # This line will never be reached, but needed for type checking


async def check_db_health(engine: AsyncEngine) -> bool:
    """
    Check database connectivity.

    Args:
        engine: AsyncEngine instance

    Returns:
        True if database is reachable, False otherwise
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def get_db_stats(engine: AsyncEngine) -> dict:
    """
    Get database statistics.

    Args:
        engine: AsyncEngine instance

    Returns:
        Dictionary with connection pool stats
    """
    if engine is None:
        return {"status": "not_initialized"}

    pool = engine.pool

    return {
        "status": "initialized",
        "pool_size": pool.size(),  # type: ignore[attr-defined]
        "checked_in": pool.checkedin(),  # type: ignore[attr-defined]
        "checked_out": pool.checkedout(),  # type: ignore[attr-defined]
        "overflow": pool.overflow(),  # type: ignore[attr-defined]
        "total_connections": pool.size() + pool.overflow(),  # type: ignore[attr-defined]
    }


