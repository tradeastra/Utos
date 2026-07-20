"""
Unit tests for OrderValidator.
"""

import uuid
from datetime import UTC
from decimal import Decimal

import pytest
from adapters.base import IExchangeAdapter
from core.domain_types import OrderSide, OrderType
from engine.execution.exceptions import OrderValidationError
from engine.execution.models import OrderRequest
from engine.execution.validator import OrderValidator


class FakeAdapter(IExchangeAdapter):
    """Minimal adapter for validator tests."""

    @property
    def exchange_name(self) -> str:
        return "binance"

    @property
    def is_testnet(self) -> bool:
        return False

    async def initialize(self, config):
        return True

    async def authenticate(self, credentials):
        return True

    async def connect_market(self):
        return True

    async def connect_account(self):
        return True

    async def disconnect(self):
        pass

    async def is_market_connected(self):
        return True

    async def is_account_connected(self):
        return True

    async def place_order(self, *args, **kwargs):
        raise NotImplementedError

    async def cancel_order(self, *args, **kwargs):
        raise NotImplementedError

    async def modify_order(self, *args, **kwargs):
        raise NotImplementedError

    async def get_balance(self):
        return []

    async def get_positions(self):
        return []

    async def get_order(self, *args, **kwargs):
        raise NotImplementedError

    async def get_open_orders(self, *args, **kwargs):
        return []

    async def get_order_history(self, *args, **kwargs):
        return []

    async def get_trade_history(self, *args, **kwargs):
        return []

    async def get_ticker(self, *args, **kwargs):
        raise NotImplementedError

    async def get_order_book(self, *args, **kwargs):
        raise NotImplementedError

    async def get_candles(self, *args, **kwargs):
        return []

    async def subscribe_market(self, *args, **kwargs):
        raise NotImplementedError

    async def unsubscribe_market(self, *args, **kwargs):
        pass

    async def get_exchange_info(self):
        from datetime import datetime

        from core.domain_types import ExchangeInfo

        return ExchangeInfo(
            name="binance",
            supported_symbols=["BTCUSDT"],
            rate_limits={},
            fee_structure={},
            server_time=datetime.now(UTC),
        )

    async def health_check(self):
        return True


@pytest.fixture
def validator() -> OrderValidator:
    return OrderValidator()


@pytest.fixture
def adapter() -> FakeAdapter:
    return FakeAdapter()


@pytest.fixture
def valid_request() -> OrderRequest:
    return OrderRequest(
        request_id=uuid.uuid4(),
        exchange_account_id=uuid.uuid4(),
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
    )


class TestOrderValidator:
    def test_valid_limit_order(
        self,
        validator: OrderValidator,
        valid_request: OrderRequest,
        adapter: FakeAdapter,
    ) -> None:
        validator.validate(valid_request, adapter)

    def test_valid_market_order(
        self, validator: OrderValidator, adapter: FakeAdapter
    ) -> None:
        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
        )
        validator.validate(request, adapter)

    def test_missing_request_id(
        self,
        validator: OrderValidator,
        valid_request: OrderRequest,
        adapter: FakeAdapter,
    ) -> None:
        valid_request.request_id = None  # type: ignore[assignment]
        with pytest.raises(OrderValidationError):
            validator.validate(valid_request, adapter)

    def test_missing_symbol(
        self,
        validator: OrderValidator,
        valid_request: OrderRequest,
        adapter: FakeAdapter,
    ) -> None:
        valid_request.symbol = ""
        with pytest.raises(OrderValidationError):
            validator.validate(valid_request, adapter)

    def test_invalid_side(
        self,
        validator: OrderValidator,
        valid_request: OrderRequest,
        adapter: FakeAdapter,
    ) -> None:
        valid_request.side = "long"  # type: ignore[assignment]
        with pytest.raises(OrderValidationError):
            validator.validate(valid_request, adapter)

    def test_invalid_order_type(
        self,
        validator: OrderValidator,
        valid_request: OrderRequest,
        adapter: FakeAdapter,
    ) -> None:
        valid_request.order_type = "unsupported"  # type: ignore[assignment]
        with pytest.raises(OrderValidationError):
            validator.validate(valid_request, adapter)

    def test_zero_quantity(
        self,
        validator: OrderValidator,
        valid_request: OrderRequest,
        adapter: FakeAdapter,
    ) -> None:
        valid_request.quantity = Decimal("0")
        with pytest.raises(OrderValidationError):
            validator.validate(valid_request, adapter)

    def test_negative_quantity(
        self,
        validator: OrderValidator,
        valid_request: OrderRequest,
        adapter: FakeAdapter,
    ) -> None:
        valid_request.quantity = Decimal("-1")
        with pytest.raises(OrderValidationError):
            validator.validate(valid_request, adapter)

    def test_limit_without_price(
        self,
        validator: OrderValidator,
        valid_request: OrderRequest,
        adapter: FakeAdapter,
    ) -> None:
        valid_request.price = None
        with pytest.raises(OrderValidationError):
            validator.validate(valid_request, adapter)

    def test_stop_limit_without_stop_price(
        self, validator: OrderValidator, adapter: FakeAdapter
    ) -> None:
        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.STOP_LIMIT,
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )
        with pytest.raises(OrderValidationError):
            validator.validate(request, adapter)

    def test_market_with_price(
        self, validator: OrderValidator, adapter: FakeAdapter
    ) -> None:
        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=uuid.uuid4(),
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
        )
        with pytest.raises(OrderValidationError):
            validator.validate(request, adapter)

    def test_validation_without_adapter(
        self, validator: OrderValidator, valid_request: OrderRequest
    ) -> None:
        validator.validate(valid_request, None)
