"""
16G-1: Infrastructure Failure Chaos Tests

Simulates:
- Redis mati (connection lost, recovery)
- PostgreSQL mati (connection lost, recovery)
- Exchange API timeout
- Exchange API 500
- DNS failure (connection error)
- TLS handshake failure (connection error)

Target: System recovery otomatis tanpa duplicate order.
"""

import asyncio
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.exceptions import (
    ExchangeConnectionError,
    ExchangeError,
    CacheError,
    DatabaseError,
    RetryableError,
)
from core.types import OrderSide, OrderType, OrderResult, OrderStatus
from engine.execution.models import OrderRequest
from engine.execution.executor import OrderExecutor
from engine.execution.tracker import OrderTracker
from engine.execution.execution_engine import ExecutionEngine
from engine.execution.validator import OrderValidator
from engine.recovery.connection import ConnectionRecovery, QueuedOrder
from tests.test_chaos.chaos_adapter import ChaosExchangeAdapter


# ── Redis Failure ─────────────────────────────

class TestRedisFailure:
    """Simulate Redis going down and recovering."""

    @pytest.mark.asyncio
    async def test_redis_down_continues_without_cache(self):
        """System should continue operating when Redis is unavailable."""
        redis_health = MagicMock(return_value=False)
        recovery = ConnectionRecovery(redis_health_check=redis_health)

        result = await recovery.recover_redis()

        assert result is False
        assert recovery.is_redis_connected() is False
        metrics = recovery.get_metrics()
        assert metrics["redis_recoveries"] == 1

    @pytest.mark.asyncio
    async def test_redis_down_then_up_recovery(self):
        """Redis recovery should succeed after coming back up."""
        call_count = 0

        def health_check():
            nonlocal call_count
            call_count += 1
            return call_count > 1  # Fail first, succeed second

        recovery = ConnectionRecovery(redis_health_check=health_check)

        first = await recovery.recover_redis()
        assert first is False

        second = await recovery.recover_redis()
        assert second is True
        assert recovery.is_redis_connected() is True

    @pytest.mark.asyncio
    async def test_redis_health_check_exception(self):
        """Redis health check raising exception should not crash recovery."""
        def bad_health_check():
            raise ConnectionError("Redis connection refused")

        recovery = ConnectionRecovery(redis_health_check=bad_health_check)

        result = await recovery.recover_redis()
        assert result is False
        assert recovery.is_redis_connected() is False

    @pytest.mark.asyncio
    async def test_orders_queued_during_redis_down(self):
        """Orders should be queued during disconnect and replayed after recovery."""
        place_order_fn = MagicMock(return_value={"status": "ok"})
        recovery = ConnectionRecovery(place_order_fn=place_order_fn)

        order = QueuedOrder(
            instance_id="inst-1",
            account_id="acc-1",
            exchange="binance",
            symbol="BTCUSDT",
            side="buy",
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
        )

        recovery.queue_order(order)
        assert recovery.get_queue_size() == 1

        results = await recovery.replay_queued_orders()
        assert len(results) == 1
        assert recovery.get_queue_size() == 0
        metrics = recovery.get_metrics()
        assert metrics["orders_replayed"] == 1


# ── PostgreSQL Failure ────────────────────────

class TestPostgresFailure:
    """Simulate PostgreSQL going down and recovering."""

    @pytest.mark.asyncio
    async def test_postgres_down_detected(self):
        """System should detect PostgreSQL being down."""
        pg_health = MagicMock(return_value=False)
        recovery = ConnectionRecovery(postgres_health_check=pg_health)

        result = await recovery.recover_postgres()

        assert result is False
        assert recovery.is_postgres_connected() is False

    @pytest.mark.asyncio
    async def test_postgres_down_then_up_recovery(self):
        """PostgreSQL recovery should succeed after coming back up."""
        call_count = 0

        def health_check():
            nonlocal call_count
            call_count += 1
            return call_count > 1

        recovery = ConnectionRecovery(postgres_health_check=health_check)

        first = await recovery.recover_postgres()
        assert first is False

        second = await recovery.recover_postgres()
        assert second is True

    @pytest.mark.asyncio
    async def test_postgres_health_check_exception(self):
        """PostgreSQL health check exception should not crash."""
        def bad_health_check():
            raise ConnectionError("PG connection refused")

        recovery = ConnectionRecovery(postgres_health_check=bad_health_check)

        result = await recovery.recover_postgres()
        assert result is False


# ── Exchange API Timeout ──────────────────────

class TestExchangeTimeout:
    """Simulate exchange API timeout — should retry, not duplicate orders."""

    @pytest.mark.asyncio
    async def test_exchange_timeout_retries(self):
        """OrderExecutor should retry on timeout."""
        adapter = ChaosExchangeAdapter(failure_mode="timeout", failure_rate=1.0)
        adapter._delay = 0  # No delay, just fail

        executor = OrderExecutor(max_retries=3, base_delay=0.01)

        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
        )

        from engine.execution.exceptions import OrderExecutionError
        with pytest.raises(OrderExecutionError):
            await executor.execute(request, adapter)

    @pytest.mark.asyncio
    async def test_exchange_timeout_then_success(self):
        """After timeout, retry should succeed when exchange recovers."""
        # Deterministic: fail first 2 calls, then succeed
        call_count = 0

        class TimeoutThenSuccessAdapter(ChaosExchangeAdapter):
            async def place_order(self, *args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise ExchangeConnectionError("Simulated timeout", "chaos")
                return await super().place_order(*args, **kwargs)

        adapter = TimeoutThenSuccessAdapter(failure_mode="none")
        executor = OrderExecutor(max_retries=5, base_delay=0.01)

        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
        )

        result = await executor.execute(request, adapter)
        assert result.status == OrderStatus.OPEN.value
        assert call_count == 3  # 2 failures + 1 success

    @pytest.mark.asyncio
    async def test_no_duplicate_order_on_timeout(self):
        """ExecutionEngine should not place duplicate orders on timeout."""
        adapter = ChaosExchangeAdapter(failure_mode="timeout", failure_rate=1.0)
        validator = OrderValidator()
        tracker = OrderTracker()
        executor = OrderExecutor(max_retries=2, base_delay=0.01)
        engine = ExecutionEngine(validator=validator, executor=executor, tracker=tracker)
        engine.register_adapter(uuid.uuid4(), adapter)

        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=list(engine._adapters.keys())[0],
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
        )

        with pytest.raises(Exception):
            await engine.place_order(request)

        # Verify no orders were tracked (since all failed)
        assert len(tracker._orders) == 0 or all(
            o.status.value == "failed" for o in tracker._orders.values()
        )


# ── Exchange API 500 ──────────────────────────

class TestExchange500:
    """Simulate exchange returning 500 errors."""

    @pytest.mark.asyncio
    async def test_exchange_500_raises_execution_error(self):
        """Exchange 500 should raise OrderExecutionError, not crash."""
        adapter = ChaosExchangeAdapter(failure_mode="500", failure_rate=1.0)
        executor = OrderExecutor(max_retries=3, base_delay=0.01)

        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
        )

        from engine.execution.exceptions import OrderExecutionError
        with pytest.raises(OrderExecutionError):
            await executor.execute(request, adapter)


# ── DNS Failure ───────────────────────────────

class TestDNSFailure:
    """Simulate DNS resolution failure."""

    @pytest.mark.asyncio
    async def test_dns_failure_raises_connection_error(self):
        """DNS failure should raise ExchangeConnectionError."""
        adapter = ChaosExchangeAdapter(failure_mode="connection_drop", failure_rate=1.0)
        executor = OrderExecutor(max_retries=2, base_delay=0.01)

        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
        )

        from engine.execution.exceptions import OrderExecutionError
        with pytest.raises(OrderExecutionError):
            await executor.execute(request, adapter)

    @pytest.mark.asyncio
    async def test_dns_failure_exchange_disconnect_handler(self):
        """ConnectionRecovery should handle exchange disconnect from DNS failure."""
        recovery = ConnectionRecovery()

        await recovery.on_exchange_disconnect("binance", "acc-1")

        assert recovery.is_exchange_connected("binance") is False
        assert recovery.get_metrics()["exchange_reconnects"] == 0


# ── TLS Handshake Failure ─────────────────────

class TestTLSFailure:
    """Simulate TLS handshake failure — behaves like connection error."""

    @pytest.mark.asyncio
    async def test_tls_failure_treated_as_connection_error(self):
        """TLS failure should be handled as ExchangeConnectionError."""
        adapter = ChaosExchangeAdapter(failure_mode="connection_drop", failure_rate=1.0)
        executor = OrderExecutor(max_retries=2, base_delay=0.01)

        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
        )

        from engine.execution.exceptions import OrderExecutionError
        with pytest.raises(OrderExecutionError):
            await executor.execute(request, adapter)


# ── Combined Infrastructure Failure ───────────

class TestCombinedInfrastructureFailure:
    """All infrastructure down simultaneously."""

    @pytest.mark.asyncio
    async def test_redis_and_postgres_down(self):
        """Both Redis and PostgreSQL down — recovery should report both."""
        recovery = ConnectionRecovery(
            redis_health_check=lambda: False,
            postgres_health_check=lambda: False,
        )

        redis_ok = await recovery.recover_redis()
        pg_ok = await recovery.recover_postgres()

        assert redis_ok is False
        assert pg_ok is False
        assert recovery.is_redis_connected() is False
        assert recovery.is_postgres_connected() is False

    @pytest.mark.asyncio
    async def test_all_down_then_all_recovered(self):
        """All infrastructure down, then all recover — system should be healthy."""
        state = {"redis": False, "pg": False}

        def redis_health():
            return state["redis"]

        def pg_health():
            return state["pg"]

        recovery = ConnectionRecovery(
            redis_health_check=redis_health,
            postgres_health_check=pg_health,
        )

        # Both down
        assert await recovery.recover_redis() is False
        assert await recovery.recover_postgres() is False

        # Both recover
        state["redis"] = True
        state["pg"] = True

        assert await recovery.recover_redis() is True
        assert await recovery.recover_postgres() is True
        assert recovery.is_redis_connected() is True
        assert recovery.is_postgres_connected() is True
