"""
Unit tests for ExecutionEngine.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from core.exceptions import ExchangeConnectionError, InsufficientBalanceError
from core.types import OrderResult, OrderSide, OrderStatus, OrderType
from engine.execution import ExecutionEngine
from engine.execution.exceptions import OrderExecutionError, OrderNotFound, OrderValidationError
from engine.execution.models import ExecutionOrderStatus, OrderRequest


class FakeAdapter:
    """Fake adapter for execution engine tests."""

    def __init__(self, name: str = "binance") -> None:
        self.exchange_name = name
        self.place_calls: list[dict[str, Any]] = []
        self.cancel_calls: list[dict[str, Any]] = []
        self.get_calls: list[dict[str, Any]] = []
        self.open_orders_calls: list[str | None] = []
        self._orders: dict[str, OrderResult] = {}
        self._fail_count = 0
        self._transient_error: Exception | None = None
        self._non_transient_error: Exception | None = None

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Decimal | None = None,
        stop_price: Decimal | None = None,
        client_order_id: str | None = None,
    ) -> OrderResult:
        self.place_calls.append({
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "quantity": quantity,
            "price": price,
        })

        if self._fail_count > 0:
            self._fail_count -= 1
            if self._transient_error:
                raise self._transient_error

        if self._non_transient_error:
            raise self._non_transient_error

        order_id = f"ex_{len(self._orders) + 1}"
        result = OrderResult(
            order_id=f"local_{order_id}",
            exchange_order_id=order_id,
            symbol=symbol.upper(),
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            filled_quantity=Decimal("0"),
            average_fill_price=None,
            status=OrderStatus.OPEN.value,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self._orders[order_id] = result
        return result

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        self.cancel_calls.append({"symbol": symbol, "order_id": order_id})
        if self._non_transient_error:
            raise self._non_transient_error
        return True

    async def get_order(self, symbol: str, order_id: str) -> OrderResult:
        self.get_calls.append({"symbol": symbol, "order_id": order_id})
        result = self._orders.get(order_id)
        if result is None:
            from core.exceptions import OrderNotFound as CoreOrderNotFound
            raise CoreOrderNotFound(order_id=order_id)
        # Return filled copy
        filled = OrderResult(
            order_id=result.order_id,
            exchange_order_id=result.exchange_order_id,
            symbol=result.symbol,
            side=result.side,
            order_type=result.order_type,
            quantity=result.quantity,
            price=result.price,
            filled_quantity=result.quantity,
            average_fill_price=result.price,
            status=OrderStatus.FILLED.value,
            created_at=result.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        return filled

    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        self.open_orders_calls.append(symbol)
        return [
            OrderResult(
                order_id="local_1",
                exchange_order_id="ex_1",
                symbol=symbol.upper() if symbol else "BTCUSDT",
                side="buy",
                order_type="limit",
                quantity=Decimal("0.1"),
                price=Decimal("50000"),
                filled_quantity=Decimal("0"),
                average_fill_price=None,
                status=OrderStatus.OPEN.value,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        ]

    def set_transient_failures(self, count: int, error: Exception) -> None:
        self._fail_count = count
        self._transient_error = error

    def set_non_transient_error(self, error: Exception) -> None:
        self._non_transient_error = error


@pytest.fixture
def account_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def engine(account_id: uuid.UUID) -> ExecutionEngine:
    e = ExecutionEngine()
    adapter = FakeAdapter()
    e.register_adapter(account_id, adapter)
    return e


@pytest.fixture
def request_obj(account_id: uuid.UUID) -> OrderRequest:
    return OrderRequest(
        request_id=uuid.uuid4(),
        exchange_account_id=account_id,
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
    )


class TestExecutionEngine:
    @pytest.mark.asyncio
    async def test_place_order(self, engine: ExecutionEngine, request_obj: OrderRequest) -> None:
        result = await engine.place_order(request_obj)
        assert result.exchange_order_id is not None
        assert result.status == OrderStatus.OPEN.value

    @pytest.mark.asyncio
    async def test_idempotency_returns_cached_result(self, engine: ExecutionEngine, request_obj: OrderRequest) -> None:
        result1 = await engine.place_order(request_obj)
        result2 = await engine.place_order(request_obj)
        assert result1.exchange_order_id == result2.exchange_order_id
        adapter = engine._adapters[request_obj.exchange_account_id]
        assert len(adapter.place_calls) == 1

    @pytest.mark.asyncio
    async def test_idempotency_with_different_request_id_calls_exchange(self, engine: ExecutionEngine, request_obj: OrderRequest) -> None:
        await engine.place_order(request_obj)
        request2 = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=request_obj.exchange_account_id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )
        await engine.place_order(request2)
        adapter = engine._adapters[request_obj.exchange_account_id]
        assert len(adapter.place_calls) == 2

    @pytest.mark.asyncio
    async def test_validation_error(self, engine: ExecutionEngine, account_id: uuid.UUID) -> None:
        bad_request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0"),
            price=Decimal("50000"),
        )
        with pytest.raises(OrderValidationError):
            await engine.place_order(bad_request)

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self, engine: ExecutionEngine, request_obj: OrderRequest) -> None:
        adapter = engine._adapters[request_obj.exchange_account_id]
        adapter.set_transient_failures(
            2, ExchangeConnectionError(message="connection lost", exchange_name="binance")
        )
        result = await engine.place_order(request_obj)
        assert result is not None
        assert len(adapter.place_calls) == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_insufficient_balance(self, engine: ExecutionEngine, request_obj: OrderRequest) -> None:
        adapter = engine._adapters[request_obj.exchange_account_id]
        adapter.set_non_transient_error(InsufficientBalanceError(message="no balance"))
        with pytest.raises(OrderExecutionError):
            await engine.place_order(request_obj)
        assert len(adapter.place_calls) == 1

    @pytest.mark.asyncio
    async def test_cancel_order(self, engine: ExecutionEngine, request_obj: OrderRequest) -> None:
        result = await engine.place_order(request_obj)
        cancel_result = await engine.cancel_order(request_obj.exchange_account_id, result.order_id)
        assert cancel_result is not None
        adapter = engine._adapters[request_obj.exchange_account_id]
        assert len(adapter.cancel_calls) == 1

    @pytest.mark.asyncio
    async def test_cancel_order_not_found(self, engine: ExecutionEngine, account_id: uuid.UUID) -> None:
        with pytest.raises(OrderNotFound):
            await engine.cancel_order(account_id, "missing")

    @pytest.mark.asyncio
    async def test_cancel_all_orders(self, engine: ExecutionEngine, account_id: uuid.UUID) -> None:
        results = await engine.cancel_all_orders(account_id, "BTCUSDT")
        assert len(results) == 1
        adapter = engine._adapters[account_id]
        assert len(adapter.cancel_calls) == 1

    @pytest.mark.asyncio
    async def test_get_order(self, engine: ExecutionEngine, request_obj: OrderRequest) -> None:
        placed = await engine.place_order(request_obj)
        result = await engine.get_order(request_obj.exchange_account_id, placed.order_id)
        assert result is not None
        assert result.order_id == placed.order_id

    @pytest.mark.asyncio
    async def test_sync_order(self, engine: ExecutionEngine, request_obj: OrderRequest) -> None:
        placed = await engine.place_order(request_obj)
        synced = await engine.sync_order(request_obj.exchange_account_id, placed.order_id)
        assert synced.status == OrderStatus.FILLED.value
        tracked = engine.tracker.get(request_obj.exchange_account_id, placed.order_id)
        assert tracked is not None
        assert tracked.status == ExecutionOrderStatus.FILLED

    @pytest.mark.asyncio
    async def test_list_active_orders(self, engine: ExecutionEngine, request_obj: OrderRequest) -> None:
        await engine.place_order(request_obj)
        active = engine.list_active_orders(request_obj.exchange_account_id)
        assert len(active) == 1

    @pytest.mark.asyncio
    async def test_list_active_orders_empty_after_fill(self, engine: ExecutionEngine, request_obj: OrderRequest) -> None:
        placed = await engine.place_order(request_obj)
        await engine.sync_order(request_obj.exchange_account_id, placed.order_id)
        active = engine.list_active_orders(request_obj.exchange_account_id)
        assert len(active) == 0

    @pytest.mark.asyncio
    async def test_no_adapter_registered(self, account_id: uuid.UUID) -> None:
        e = ExecutionEngine()
        request_obj = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=account_id,
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )
        with pytest.raises(OrderExecutionError):
            await e.place_order(request_obj)
