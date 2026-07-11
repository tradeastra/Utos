"""
Async database session utilities for UTOS Trading Engine.

Provides:
- `get_session()` — context manager for a standalone async session
- `create_test_engine()` — builds an in-memory or test DB engine + session factory
- `get_test_session()` — context manager for a test session with rollback
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from database.base import Base, get_engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session from the global engine."""
    engine = get_engine()
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def create_test_engine(url: str) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Create a test engine + session factory for the given URL."""
    engine = create_async_engine(url, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


async def create_all_tables(engine: AsyncEngine) -> None:
    """Create all tables registered on Base.metadata."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables(engine: AsyncEngine) -> None:
    """Drop all tables registered on Base.metadata."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)