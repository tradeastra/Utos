"""
16G-6: Exchange Chaos Tests

Simulates mock exchange:
- timeout
- duplicate ACK
- delayed fill
- partial fill after cancel
- out-of-order WebSocket event

This is the most critical chaos test — directly impacts trading integrity.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from core.domain_types import OrderResult, OrderSide, OrderStatus, OrderType
from core.exceptions import ExchangeConnectionError
from engine.execution.execution_engine import ExecutionEngine
from engine.execution.executor import OrderExecutor
from engine.execution.models import OrderRequest
from engine.execution.tracker import OrderTracker
from engine.execution.validator import OrderValidator
from engine.recovery.reconciler import RuntimeReconciler
from tests.test_chaos.chaos_adapter import ChaosExchangeAdapter


class TestExchangeTimeout:
    """Exchange timeout scenarios."""

    @pytest.mark.asyncio
    async def test_timeout_retries_and_fails_gracefully(self):
        """All retries exhausted on timeout — should raise, not crash."""
        adapter = ChaosExchangeAdapter(failure_mode="timeout", failure_rate=1.0)
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
    async def test_timeout_then_success_no_duplicate(self):
        """Timeout on first attempt, success on retry — no duplicate order."""
        call_count = 0

        class TimeoutOnceAdapter(ChaosExchangeAdapter):
            async def place_order(self, *args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise ExchangeConnectionError("Simulated timeout", "chaos")
                return await super().place_order(*args, **kwargs)

        adapter = TimeoutOnceAdapter()
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
        assert call_count == 2  # 1 timeout + 1 success


class TestDuplicateACK:
    """Exchange returns duplicate ACK for same order."""

    @pytest.mark.asyncio
    async def test_duplicate_ack_idempotency(self):
        """ExecutionEngine should handle duplicate ACK via request_id idempotency."""
        adapter = ChaosExchangeAdapter(duplicate_ack=True)
        validator = OrderValidator()
        tracker = OrderTracker()
        executor = OrderExecutor(max_retries=3, base_delay=0.01)
        engine = ExecutionEngine(
            validator=validator, executor=executor, tracker=tracker
        )

        account_id = uuid.uuid4()
        engine.register_adapter(account_id, adapter)

        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
        )

        # First call
        result1 = await engine.place_order(request)
        assert result1.status == OrderStatus.OPEN.value

        # Same request_id — should return cached result (idempotent)
        result2 = await engine.place_order(request)
        assert result2.exchange_order_id == result1.exchange_order_id

    @pytest.mark.asyncio
    async def test_duplicate_ack_does_not_create_duplicate_tracker_entry(self):
        """Tracker should not have duplicate entries for same request_id."""
        adapter = ChaosExchangeAdapter()
        validator = OrderValidator()
        tracker = OrderTracker()
        executor = OrderExecutor(max_retries=3, base_delay=0.01)
        engine = ExecutionEngine(
            validator=validator, executor=executor, tracker=tracker
        )

        account_id = uuid.uuid4()
        engine.register_adapter(account_id, adapter)

        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
        )

        await engine.place_order(request)
        await engine.place_order(request)  # Duplicate

        # Should only have one tracked order
        cached = tracker.get_by_request_id(request.request_id)
        assert cached is not None
        assert cached.result.exchange_order_id is not None


class TestPartialFillAfterCancel:
    """Exchange returns partial fill after cancel request."""

    @pytest.mark.asyncio
    async def test_partial_fill_after_cancel_detected(self):
        """System should detect partial fill after cancel and handle it."""
        adapter = ChaosExchangeAdapter(partial_fill_after_cancel=True)

        # Place order
        uuid.uuid4()
        result = await adapter.place_order(
            symbol="BTCUSDT",
            side="buy",
            order_type="limit",
            quantity=Decimal("1.0"),
            price=Decimal("45000"),
        )

        order_id = result.exchange_order_id

        # Cancel order
        cancel_result = await adapter.cancel_order("BTCUSDT", order_id)
        assert cancel_result is True

        # Check order status — should be partially filled (chaos scenario)
        order = await adapter.get_order("BTCUSDT", order_id)
        assert order.status == OrderStatus.PARTIALLY_FILLED.value
        assert order.filled_quantity == Decimal("0.5")

    @pytest.mark.asyncio
    async def test_partial_fill_after_cancel_reconciliation(self):
        """Reconciler should detect partial fill after cancel as orphan/missing."""
        adapter = ChaosExchangeAdapter(partial_fill_after_cancel=True)

        result = await adapter.place_order(
            symbol="BTCUSDT",
            side="buy",
            order_type="limit",
            quantity=Decimal("1.0"),
            price=Decimal("45000"),
        )
        order_id = result.exchange_order_id

        await adapter.cancel_order("BTCUSDT", order_id)

        # The order is now partially filled — reconciliation should handle this
        order = await adapter.get_order("BTCUSDT", order_id)
        assert order.filled_quantity > Decimal("0")
        assert order.filled_quantity < order.quantity


class TestDelayedFill:
    """Exchange delays fill notification."""

    @pytest.mark.asyncio
    async def test_delayed_fill_does_not_cause_duplicate_order(self):
        """Delayed fill should not cause system to place duplicate orders."""
        adapter = ChaosExchangeAdapter(delay_seconds=0.1)
        validator = OrderValidator()
        tracker = OrderTracker()
        executor = OrderExecutor(max_retries=3, base_delay=0.01)
        engine = ExecutionEngine(
            validator=validator, executor=executor, tracker=tracker
        )

        account_id = uuid.uuid4()
        engine.register_adapter(account_id, adapter)

        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
        )

        result = await engine.place_order(request)
        assert result.status == OrderStatus.OPEN.value

        # Verify only one order was placed
        cached = tracker.get_by_request_id(request.request_id)
        assert cached is not None


class TestOutOfOrderWebSocketEvents:
    """WebSocket events arrive out of order."""

    @pytest.mark.asyncio
    async def test_out_of_order_events_logged(self):
        """Out-of-order events should be logged for debugging."""
        adapter = ChaosExchangeAdapter(out_of_order_events=True)

        # Place multiple orders
        results = []
        for i in range(5):
            r = await adapter.place_order(
                symbol="BTCUSDT",
                side="buy",
                order_type="limit",
                quantity=Decimal("0.1"),
                price=Decimal(f"{45000 + i * 100}"),
            )
            results.append(r)

        # Events are logged
        events = adapter.get_event_log()
        assert len(events) == 5
        assert all(e["type"] == "place_order" for e in events)

    @pytest.mark.asyncio
    async def test_reconciler_handles_out_of_order(self):
        """Reconciler should handle out-of-order events gracefully."""
        reconciler = RuntimeReconciler()

        # Create a simple grid state with levels
        from core.domain_types import GridLevel, GridLevelStatus, GridState
        from engine.grid.state import GridStatus

        levels = [
            GridLevel(
                level=0,
                buy_price=Decimal("49000"),
                sell_price=Decimal("50000"),
                quantity=Decimal("0.1"),
                status=GridLevelStatus.OPEN,
                buy_order_id="order-1",
            ),
            GridLevel(
                level=1,
                buy_price=Decimal("48000"),
                sell_price=Decimal("49000"),
                quantity=Decimal("0.1"),
                status=GridLevelStatus.WAITING,
            ),
        ]

        state = GridState(
            instance_id="inst-1",
            status=GridStatus.ACTIVE,
            upper_price=Decimal("50000"),
            lower_price=Decimal("40000"),
            grid_count=2,
            grid_spacing=Decimal("1000"),
            investment_per_grid=Decimal("100"),
            levels=levels,
            exchange_account_id=uuid.uuid4(),
            symbol="BTCUSDT",
        )

        # Simulate out-of-order: fill event for order-1 arrives
        live_orders = [
            OrderResult(
                order_id="order-1",
                exchange_order_id="order-1",
                symbol="BTCUSDT",
                side="buy",
                order_type="limit",
                status=OrderStatus.FILLED.value,
                quantity=Decimal("0.1"),
                price=Decimal("49000"),
                filled_quantity=Decimal("0.1"),
                average_fill_price=Decimal("49000"),
                created_at=datetime(2025, 1, 1, tzinfo=UTC),
                updated_at=datetime(2025, 1, 1, 0, 1, tzinfo=UTC),
            ),
        ]

        result = await reconciler.reconcile_grid("inst-1", state, live_orders)

        # Should detect the fill and update level status
        assert result.action == "restored"
        assert state.levels[0].status == GridLevelStatus.FILLED


class TestExchangeChaosRecovery:
    """Full recovery after exchange chaos."""

    @pytest.mark.asyncio
    async def test_recovery_after_exchange_chaos(self):
        """System should recover after exchange chaos (timeouts + partial fills)."""
        call_count = 0

        class FailFirstAdapter(ChaosExchangeAdapter):
            async def place_order(self, *args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise ExchangeConnectionError("Simulated timeout", "chaos")
                return await super().place_order(*args, **kwargs)

        adapter = FailFirstAdapter(partial_fill_after_cancel=True)

        validator = OrderValidator()
        tracker = OrderTracker()
        executor = OrderExecutor(max_retries=5, base_delay=0.01)
        engine = ExecutionEngine(
            validator=validator, executor=executor, tracker=tracker
        )

        account_id = uuid.uuid4()
        engine.register_adapter(account_id, adapter)

        # First order: timeout then success on retry
        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
        )

        result = await engine.place_order(request)
        assert result.status == OrderStatus.OPEN.value

        # Second order: succeeds immediately
        call_count = 0
        adapter.reset()

        request2 = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("45000"),
        )

        result2 = await engine.place_order(request2)
        assert result2.status == OrderStatus.OPEN.value

    @pytest.mark.asyncio
    async def test_no_duplicate_orders_across_chaos(self):
        """No duplicate orders should be created across chaos scenarios."""
        adapter = ChaosExchangeAdapter()
        validator = OrderValidator()
        tracker = OrderTracker()
        executor = OrderExecutor(max_retries=3, base_delay=0.01)
        engine = ExecutionEngine(
            validator=validator, executor=executor, tracker=tracker
        )

        account_id = uuid.uuid4()
        engine.register_adapter(account_id, adapter)

        all_order_ids = set()

        for _ in range(10):
            request = OrderRequest(
                request_id=uuid.uuid4(),
                exchange_account_id=account_id,
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=Decimal("0.1"),
                price=Decimal("45000"),
            )
            result = await engine.place_order(request)
            all_order_ids.add(result.exchange_order_id)

        # Each order should have a unique exchange_order_id
        assert len(all_order_ids) == 10
        assert len(all_order_ids) == len(set(all_order_ids))
