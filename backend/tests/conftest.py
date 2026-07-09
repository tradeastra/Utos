"""
Pytest configuration and fixtures for UTOS Trading Engine tests.

This module provides common fixtures and test configuration.
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import redis

from main import app
from database.base import Base, get_db
from core.config import settings


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def db_session() -> Generator:
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session) -> Generator:
    """Create a test client with database dependency override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def redis_client() -> Generator:
    """Create a test Redis client."""
    test_redis = redis.Redis.from_url(
        "redis://localhost:6379/1",
        decode_responses=True
    )
    
    # Clear test database
    test_redis.flushdb()
    
    yield test_redis
    
    # Cleanup
    test_redis.flushdb()
    test_redis.close()


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User"
    }


@pytest.fixture
def sample_exchange_account_data():
    """Sample exchange account data for testing."""
    return {
        "exchange_name": "binance",
        "api_key": "test_api_key",
        "api_secret": "test_api_secret",
        "is_testnet": True
    }


@pytest.fixture
def sample_trading_instance_data():
    """Sample trading instance data for testing."""
    return {
        "exchange_account_id": "test-account-id",
        "symbol": "BTCUSDT",
        "strategy_type": "smart_grid",
        "strategy_params": {
            "grid_count": 10,
            "grid_spacing": 0.01
        },
        "total_investment": 1000.0,
        "grid_upper_price": 50000.0,
        "grid_lower_price": 40000.0,
        "grid_count": 10
    }


@pytest.fixture
def authenticated_client(client, sample_user_data):
    """Create an authenticated test client."""
    # Register user
    client.post("/api/v1/auth/register", json=sample_user_data)
    
    # Login user
    login_response = client.post("/api/v1/auth/login", json={
        "email": sample_user_data["email"],
        "password": sample_user_data["password"]
    })
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Set authorization header
    client.headers.update({
        "Authorization": f"Bearer {access_token}"
    })
    
    return client


@pytest.fixture
def admin_token():
    """Create an admin token for testing."""
    from core.security import token_manager
    
    return token_manager.create_access_token({
        "sub": "admin-user-id",
        "email": "admin@example.com",
        "role": "admin",
        "subscription_tier": "enterprise"
    })


@pytest.fixture
def admin_client(client, admin_token):
    """Create an admin test client."""
    client.headers.update({
        "Authorization": f"Bearer {admin_token}"
    })
    return client


# Mock fixtures
@pytest.fixture
def mock_exchange_adapter():
    """Mock exchange adapter for testing."""
    from unittest.mock import Mock
    from adapters.base import IExchangeAdapter
    
    mock_adapter = Mock(spec=IExchangeAdapter)
    mock_adapter.exchange_name = "binance"
    mock_adapter.is_testnet = True
    
    # Configure mock methods
    mock_adapter.initialize.return_value = True
    mock_adapter.authenticate.return_value = True
    mock_adapter.connect_market.return_value = True
    mock_adapter.connect_account.return_value = True
    mock_adapter.is_market_connected.return_value = True
    mock_adapter.is_account_connected.return_value = True
    
    return mock_adapter


@pytest.fixture
def mock_trading_engine():
    """Mock trading engine for testing."""
    from unittest.mock import Mock
    from engine.base import ITradingEngine
    
    mock_engine = Mock(spec=ITradingEngine)
    
    # Configure mock methods
    mock_engine.create_instance.return_value = {
        "id": "test-instance-id",
        "status": "created"
    }
    mock_engine.prepare_instance.return_value = True
    mock_engine.start_instance.return_value = True
    mock_engine.stop_instance.return_value = True
    
    return mock_engine


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing."""
    from unittest.mock import Mock
    from events.base import IEventBus
    
    mock_bus = Mock(spec=IEventBus)
    
    # Configure mock methods
    mock_bus.publish.return_value = "test-event-id"
    mock_bus.subscribe.return_value = "test-subscription-id"
    mock_bus.health_check.return_value = True
    
    return mock_bus


# Async fixtures
@pytest.fixture
async def async_client():
    """Create an async test client."""
    from httpx import AsyncClient
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def async_redis_client():
    """Create an async Redis client for testing."""
    import redis.asyncio as aioredis
    
    redis_client = aioredis.from_url(
        "redis://localhost:6379/1",
        decode_responses=True
    )
    
    # Clear test database
    await redis_client.flushdb()
    
    yield redis_client
    
    # Cleanup
    await redis_client.flushdb()
    await redis_client.close()


# Test markers
pytest_plugins = []

# Custom markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    )


# Test collection hooks
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Add unit marker to tests in test_unit directory
        if "test_unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Add integration marker to tests in test_integration directory
        elif "test_integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add external marker to tests that require external services
        if "redis" in str(item.fspath) or "exchange" in str(item.fspath):
            item.add_marker(pytest.mark.external)
