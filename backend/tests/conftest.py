"""
Shared pytest fixtures for backend tests.

Uses async SQLite (aiosqlite) for unit tests by default.
Set TEST_DATABASE_URL to use PostgreSQL instead.
"""

import os
from collections.abc import AsyncGenerator, Callable
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("TESTING", "true")

from database.base import Base, get_db
from main import app

# Use SQLite for tests by default (no external DB required)
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite+aiosqlite://",
)

_is_sqlite = TEST_DB_URL.startswith("sqlite")

_test_engine = create_async_engine(TEST_DB_URL, echo=False)
_TestSession = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


# For SQLite: register JSON functions and enable foreign keys
if _is_sqlite:
    @event.listens_for(_test_engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_tables():
    """Create all tables once per session; drop after session."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await _test_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Transactional test session — rolls back after each test."""
    async with _test_engine.connect() as conn:
        transaction = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with DB dependency overridden to the test session."""

    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def sample_user_data() -> dict:
    return {"email": "test@example.com", "password": "TestPassword123!", "full_name": "Test User"}


@pytest_asyncio.fixture
async def create_trading_instance() -> Callable:
    """Factory fixture that creates a full trading instance setup (user, exchange account, strategy, grid profile, instance)."""
    from models import User, ExchangeAccount, Strategy, GridProfile, TradingInstance
    from models.exchange_account import ExchangeName
    from core.types import StrategyType, TradingInstanceStatus

    async def _create(db_session: AsyncSession) -> TradingInstance:
        user = User(email=f"ti_{os.urandom(4).hex()}@example.com", password_hash="x")
        db_session.add(user)
        await db_session.flush()

        ea = ExchangeAccount(
            user_id=user.id,
            exchange_name=ExchangeName.BINANCE,
            account_name="Binance",
            api_key_encrypted="k",
            api_secret_encrypted="s",
        )
        db_session.add(ea)
        await db_session.flush()

        strategy = Strategy(
            name=f"Strategy_{os.urandom(4).hex()}",
            type=StrategyType.SMART_GRID,
            min_investment=Decimal("100"),
        )
        db_session.add(strategy)
        await db_session.flush()

        gp = GridProfile(
            user_id=user.id,
            name="Grid",
            strategy_type=StrategyType.SMART_GRID,
            upper_price=Decimal("50000"),
            lower_price=Decimal("40000"),
            grid_count=10,
            investment_per_grid=Decimal("100"),
        )
        db_session.add(gp)
        await db_session.flush()

        instance = TradingInstance(
            user_id=user.id,
            exchange_account_id=ea.id,
            strategy_id=strategy.id,
            grid_profile_id=gp.id,
            symbol="BTCUSDT",
            status=TradingInstanceStatus.CREATED,
            start_price=Decimal("45000"),
            total_investment=Decimal("1000"),
            base_currency="BTC",
            quote_currency="USDT",
        )
        db_session.add(instance)
        await db_session.flush()
        await db_session.refresh(instance)
        return instance

    return _create


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "unit: unit test")
    config.addinivalue_line("markers", "integration: integration test")
    config.addinivalue_line("markers", "slow: slow test")
