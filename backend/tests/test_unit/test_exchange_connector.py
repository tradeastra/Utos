"""
Unit tests for ExchangeConnector.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from core.domain_types import Candle, OrderBook, TickerData
from market.base import MarketStatus
from market.connector.exchange_connector import ExchangeConnector


class FakeAdapter:
    """Minimal fake adapter for connector tests."""

    def __init__(self, connected: bool = True) -> None:
        self._connected = connected
        self._sub_counter = 0
        self._subs: dict[str, tuple[str, str, Callable]] = {}
        self.connect_calls = 0
        self.disconnect_calls = 0

    @property
    def exchange_name(self) -> str:
        return "binance"

    @property
    def is_testnet(self) -> bool:
        return False

    async def initialize(self, config: Any) -> bool:
        return True

    async def authenticate(self, credentials: Any) -> bool:
        return True

    async def connect_market(self) -> bool:
        self.connect_calls += 1
        self._connected = True
        return True

    async def connect_account(self) -> bool:
        return True

    async def disconnect(self) -> None:
        self.disconnect_calls += 1
        self._connected = False

    async def is_market_connected(self) -> bool:
        return self._connected

    async def is_account_connected(self) -> bool:
        return True

    async def subscribe_market(
        self, symbol: str, channel: str, callback: Callable
    ) -> str:
        self._sub_counter += 1
        sub_id = f"sub_{self._sub_counter}"
        self._subs[sub_id] = (symbol, channel, callback)
        return sub_id

    async def unsubscribe_market(self, sub_id: str) -> None:
        self._subs.pop(sub_id, None)

    async def get_ticker(self, symbol: str) -> TickerData:
        return TickerData(
            symbol=symbol,
            bid=Decimal("50000"),
            ask=Decimal("50001"),
            last=Decimal("50000.50"),
            volume=Decimal("1000"),
            timestamp=datetime.now(UTC),
        )

    async def get_order_book(self, symbol: str, depth: int = 20) -> OrderBook:
        return OrderBook(
            symbol=symbol,
            bids=[(Decimal("50000"), Decimal("1"))],
            asks=[(Decimal("50001"), Decimal("1"))],
            timestamp=datetime.now(UTC),
        )

    async def get_candles(
        self, symbol: str, interval: str, limit: int = 100
    ) -> list[Candle]:
        return [
            Candle(
                symbol=symbol,
                interval=interval,
                open=Decimal("50000"),
                high=Decimal("50100"),
                low=Decimal("49900"),
                close=Decimal("50050"),
                volume=Decimal("100"),
                timestamp=datetime.now(UTC),
            )
        ]

    async def get_exchange_info(self) -> Any:
        from core.domain_types import ExchangeInfo

        return ExchangeInfo(
            name="binance",
            supported_symbols=["BTCUSDT", "ETHUSDT"],
            rate_limits={},
            fee_structure={},
            server_time=datetime.now(UTC),
        )

    async def health_check(self) -> bool:
        return True


@pytest.fixture
def adapter() -> FakeAdapter:
    return FakeAdapter()


@pytest.fixture
def connector(adapter: FakeAdapter) -> ExchangeConnector:
    return ExchangeConnector(
        exchange="binance",
        adapter=adapter,
        data_callback=lambda *args: None,
    )


class TestExchangeConnector:
    @pytest.mark.asyncio
    async def test_start(
        self, connector: ExchangeConnector, adapter: FakeAdapter
    ) -> None:
        await connector.start()
        assert connector.running is True
        assert adapter.connect_calls == 1

    @pytest.mark.asyncio
    async def test_stop(
        self, connector: ExchangeConnector, adapter: FakeAdapter
    ) -> None:
        await connector.start()
        await connector.stop()
        assert connector.running is False
        assert adapter.disconnect_calls == 1

    @pytest.mark.asyncio
    async def test_subscribe(self, connector: ExchangeConnector) -> None:
        await connector.start()
        sub_id = await connector.subscribe("BTCUSDT", "ticker")
        assert sub_id.startswith("sub_")

    @pytest.mark.asyncio
    async def test_unsubscribe(self, connector: ExchangeConnector) -> None:
        await connector.start()
        sub_id = await connector.subscribe("BTCUSDT", "ticker")
        await connector.unsubscribe(sub_id)

    @pytest.mark.asyncio
    async def test_is_alive_no_data(self, connector: ExchangeConnector) -> None:
        await connector.start()
        assert connector.is_alive("BTCUSDT") is False

    @pytest.mark.asyncio
    async def test_get_status_disconnected(self, connector: ExchangeConnector) -> None:
        assert connector.get_status("BTCUSDT") == MarketStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_get_metrics_default(self, connector: ExchangeConnector) -> None:
        m = connector.get_metrics("BTCUSDT")
        assert m.exchange == "binance"
        assert m.symbol == "BTCUSDT"
        assert m.status == MarketStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_mark_reconnecting(self, connector: ExchangeConnector) -> None:
        await connector.start()
        await connector.subscribe("BTCUSDT", "ticker")
        connector.mark_reconnecting("BTCUSDT")
        assert connector.get_status("BTCUSDT") == MarketStatus.RECONNECTING

    @pytest.mark.asyncio
    async def test_record_dropped(self, connector: ExchangeConnector) -> None:
        await connector.start()
        await connector.subscribe("BTCUSDT", "ticker")
        connector.record_dropped("BTCUSDT")
        m = connector.get_metrics("BTCUSDT")
        assert m.dropped_messages == 1

    @pytest.mark.asyncio
    async def test_reconnect(
        self, connector: ExchangeConnector, adapter: FakeAdapter
    ) -> None:
        await connector.start()
        await connector.subscribe("BTCUSDT", "ticker")
        await connector.reconnect()
        assert connector.get_status("BTCUSDT") == MarketStatus.CONNECTED
