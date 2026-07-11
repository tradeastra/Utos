"""
Async database configuration for UTOS Trading Engine.

SQLAlchemy 2.0 async engine + session factory using asyncpg.
"""

from collections.abc import AsyncGenerator
from typing import Any

import sqlalchemy as sa
from sqlalchemy import String, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from core.config import get_database_url
from core.logging import get_logger

logger = get_logger(__name__)


class GUID(TypeDecorator):
    """Platform-independent UUID type.

    Uses PostgreSQL's UUID column type when connecting to PostgreSQL,
    otherwise uses CHAR(36) for SQLite and other databases.
    """

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PgUUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        import uuid
        return uuid.UUID(value)


class JSONBCompat(TypeDecorator):
    """Platform-independent JSONB type.

    Uses PostgreSQL's JSONB when available, otherwise falls back to JSON.
    """

    impl = sa.Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(sa.Text())

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        import json
        return json.dumps(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        if isinstance(value, str):
            import json
            return json.loads(value)
        return value


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


# Module-level engine — initialized in lifespan, replaced during tests.
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine(database_url: str | None = None) -> AsyncEngine:
    """Create (or recreate) the async engine."""
    global _engine, _session_factory
    url = database_url or get_database_url()
    _engine = create_async_engine(
        url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False,
    )
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    logger.info("Async database engine initialised", extra={"url": url.split("@")[-1]})
    return _engine


def get_engine() -> AsyncEngine:
    if _engine is None:
        return init_engine()
    return _engine


async def close_engine() -> None:
    """Dispose of the engine on shutdown."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine disposed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async database session."""
    factory = _session_factory
    if factory is None:
        init_engine()
        factory = _session_factory
    assert factory is not None
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
