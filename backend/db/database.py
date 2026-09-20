"""
EduGenAI - Database Connection & Session Management
Supports PostgreSQL (via asyncpg) with graceful SQLite fallback.
"""
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.orm import declarative_base
from config import DATABASE_URL, DEFAULT_SQLITE_URL

logger = logging.getLogger("EduGenAI.Database")

Base = declarative_base()

# Active engine & session factory
_engine: AsyncEngine | None = None
_async_session_factory = None
_using_fallback = False


def _create_engine_instance(url: str) -> AsyncEngine:
    """Create an AsyncEngine with appropriate connection pool settings."""
    if url.startswith("sqlite"):
        return create_async_engine(
            url,
            echo=False,
            connect_args={"check_same_thread": False},
        )
    else:
        return create_async_engine(
            url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )


def get_engine() -> AsyncEngine:
    global _engine, _async_session_factory
    if _engine is None:
        try:
            _engine = _create_engine_instance(DATABASE_URL)
        except Exception as e:
            logger.warning(f"Failed to create engine with {DATABASE_URL}: {e}. Falling back to SQLite.")
            _engine = _create_engine_instance(DEFAULT_SQLITE_URL)
        _async_session_factory = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _engine


def get_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        get_engine()
    return _async_session_factory


async def init_db() -> bool:
    """
    Initialize database connection and create tables if they do not exist.
    If PostgreSQL is unreachable, falls back to SQLite seamlessly.
    """
    global _engine, _async_session_factory, _using_fallback
    engine = get_engine()

    try:
        async with engine.begin() as conn:
            # Import models to ensure they are registered with Base.metadata
            from db.models import User, QuizAttempt, TopicStat, VideoRecord, ShareLink  # noqa: F401
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info(f" Database connected and schema verified ({'SQLite Fallback' if _using_fallback else 'PostgreSQL'})")
        return True
    except Exception as e:
        logger.error(f"⚠️ Could not connect to primary database ({DATABASE_URL}): {e}")
        
        # If we weren't already using SQLite, switch to SQLite fallback
        if not DATABASE_URL.startswith("sqlite") and not _using_fallback:
            logger.info(f"🔄 Switching to local SQLite fallback: {DEFAULT_SQLITE_URL}")
            _using_fallback = True
            _engine = _create_engine_instance(DEFAULT_SQLITE_URL)
            _async_session_factory = async_sessionmaker(
                bind=_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            async with _engine.begin() as conn:
                from db.models import User, QuizAttempt, TopicStat, VideoRecord, ShareLink  # noqa: F401
                await conn.run_sync(Base.metadata.create_all)
            logger.info(" Database initialized using local SQLite fallback.")
            return True
        return False


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI route handlers."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
