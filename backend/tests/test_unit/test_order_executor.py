"""
Unit tests for OrderExecutor.
"""

import asyncio
from decimal import Decimal
from typing import Any

import pytest

from core.exceptions import (
    ExchangeConnectionError,
    ExchangeRateLimitError,
    InsufficientBalanceError,
    TimeoutError,
)
from core.types import OrderResult, OrderStatus
from engine.execution.exceptions import OrderExecutionError
from engine.execution.executor import OrderExecutor
from engine.execution.models import OrderRequest, OrderSide, OrderType


class FakeAdapter:
    """Fake adapter for executor tests."""

    def __init__(self, exchange_name: str = "binance") -> None:
        self.exchange_name = exchange_name
        self.place_calls: list[dict[str, Any]] = []
        self.cancel_calls: list[dict[str, Any]] = []
        self.get_calls: list[dict[str, Any]] = []
        self.open_orders_calls: list[str | None] = []
        self.fail_count = 0
        self.transient_error: Exception | None = None
        self.non_transient_error: Exception | None = None

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

        if self.fail_count > 0:
            self.fail_count -= 1
            if self.transient_error:
                raise self.transient_error

        if self.non_transient_error:
            raise self.non_transient_error

        return OrderResult(
            order_id="local_123",
            exchange_order_id="ex_123",
            symbol=symbol.upper(),
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            filled_quantity=Decimal("0"),
            average_fill_price=None,
            status=OrderStatus.OPEN.value,
            created_at=__import__("datetime").datetime.utcnow(),
            updated_at=__import__("datetime").datetime.utcnow(),
        )

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        self.cancel_calls.append({"symbol": symbol, "order_id": order_id})
        if self.non_transient_error:
            raise self.non_transient_error
        return True

    async def get_order(self, symbol: str, order_id: str) -> OrderResult:
        self.get_calls.append({"symbol": symbol, "order_id": order_id})
        return OrderResult(
            order_id=order_id,
            exchange_order_id=order_id,
            symbol=symbol.upper(),
            side="buy",
            order_type="limit",
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
            filled_quantity=Decimal("0.1"),
            average_fill_price=Decimal("50000"),
            status=OrderStatus.FILLED.value,
            created_at=__import__("datetime").datetime.utcnow(),
            updated_at=__import__("datetime").datetime.utcnow(),
        )

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
                created_at=__import__("datetime").datetime.utcnow(),
                updated_at=__import__("datetime").datetime.utcnow(),
            )
        ]


@pytest.fixture
def executor() -> OrderExecutor:
    # Use very short delays so tests run fast.
    return OrderExecutor(max_retries=3, base_delay=0.01, max_delay=0.05)


@pytest.fixture
def request_obj() -> OrderRequest:
    return OrderRequest(
        request_id=__import__("uuid").uuid4(),
        exchange_account_id=__import__("uuid").uuid4(),
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
    )


class TestOrderExecutor:
    @pytest.mark.asyncio
    async def test_execute_success(self, executor: OrderExecutor, request_obj: OrderRequest) -> None:
        adapter = FakeAdapter()
        result = await executor.execute(request_obj, adapter)
        assert result.exchange_order_id == "ex_123"
        assert len(adapter.place_calls) == 1

    @pytest.mark.asyncio
    async def test_execute_retries_on_connection_error(self, executor: OrderExecutor, request_obj: OrderRequest) -> None:
        adapter = FakeAdapter()
        adapter.fail_count = 2
        adapter.transient_error = ExchangeConnectionError(
            message="connection lost", exchange_name="binance"
        )
        result = await executor.execute(request_obj, adapter)
        assert result is not None
        assert len(adapter.place_calls) == 3

    @pytest.mark.asyncio
    async def test_execute_retries_on_rate_limit(self, executor: OrderExecutor, request_obj: OrderRequest) -> None:
        adapter = FakeAdapter()
        adapter.fail_count = 1
        adapter.transient_error = ExchangeRateLimitError(
            message="rate limited", exchange_name="binance"
        )
        result = await executor.execute(request_obj, adapter)
        assert result is not None
        assert len(adapter.place_calls) == 2

    @pytest.mark.asyncio
    async def test_execute_retries_on_timeout(self, executor: OrderExecutor, request_obj: OrderRequest) -> None:
        adapter = FakeAdapter()
        adapter.fail_count = 2
        adapter.transient_error = TimeoutError(message="timeout")
        result = await executor.execute(request_obj, adapter)
        assert result is not None
        assert len(adapter.place_calls) == 3

    @pytest.mark.asyncio
    async def test_execute_does_not_retry_insufficient_balance(self, executor: OrderExecutor, request_obj: OrderRequest) -> None:
        adapter = FakeAdapter()
        adapter.non_transient_error = InsufficientBalanceError(
            message="not enough balance"
        )
        with pytest.raises(OrderExecutionError):
            await executor.execute(request_obj, adapter)
        assert len(adapter.place_calls) == 1

    @pytest.mark.asyncio
    async def test_execute_gives_up_after_max_retries(self, executor: OrderExecutor, request_obj: OrderRequest) -> None:
        adapter = FakeAdapter()
        adapter.fail_count = 5
        adapter.transient_error = ExchangeConnectionError(
            message="connection lost", exchange_name="binance"
        )
        with pytest.raises(OrderExecutionError):
            await executor.execute(request_obj, adapter)
        assert len(adapter.place_calls) == 3

    @pytest.mark.asyncio
    async def test_cancel(self, executor: OrderExecutor) -> None:
        adapter = FakeAdapter()
        result = await executor.cancel("BTCUSDT", "ex_123", adapter)
        assert result is True
        assert len(adapter.cancel_calls) == 1

    @pytest.mark.asyncio
    async def test_get_order(self, executor: OrderExecutor) -> None:
        adapter = FakeAdapter()
        result = await executor.get_order("BTCUSDT", "ex_123", adapter)
        assert result.status == OrderStatus.FILLED.value

    @pytest.mark.asyncio
    async def test_get_open_orders(self, executor: OrderExecutor) -> None:
        adapter = FakeAdapter()
        results = await executor.get_open_orders("BTCUSDT", adapter)
        assert len(results) == 1
        assert len(adapter.open_orders_calls) == 1
