"""
Integration tests for MarketHub — multi-consumer fan-out, cache persistence,
reconnect survival, and multi-exchange scenarios.
"""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from core.domain_types import TickerData
from market.hub.market_hub import MarketHub
from market.symbol_registry import SymbolRegistry


class StreamingFakeAdapter:
    """Fake adapter that can emit data to subscribers."""

    def __init__(self, name: str = "binance") -> None:
        self._name = name
        self._connected = False
        self._sub_counter = 0
        self._callbacks: dict[str, Callable] = {}

    @property
    def exchange_name(self) -> str:
        return self._name

    @property
    def is_testnet(self) -> bool:
        return False

    async def initialize(self, config: Any) -> bool:
        return True

    async def authenticate(self, credentials: Any) -> bool:
        return True

    async def connect_market(self) -> bool:
        self._connected = True
        return True

    async def connect_account(self) -> bool:
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def is_market_connected(self) -> bool:
        return self._connected

    async def is_account_connected(self) -> bool:
        return True

    async def subscribe_market(
        self, symbol: str, channel: str, callback: Callable
    ) -> str:
        self._sub_counter += 1
        sub_id = f"{self._name}_sub_{self._sub_counter}"
        self._callbacks[sub_id] = callback
        return sub_id

    async def unsubscribe_market(self, sub_id: str) -> None:
        self._callbacks.pop(sub_id, None)

    async def get_ticker(self, symbol: str) -> TickerData:
        return TickerData(
            symbol=symbol,
            bid=Decimal("50000"),
            ask=Decimal("50001"),
            last=Decimal("50000.50"),
            volume=Decimal("1000"),
            timestamp=datetime.now(UTC),
        )

    async def get_order_book(self, symbol: str, depth: int = 20) -> Any:
        from core.domain_types import OrderBook

        return OrderBook(
            symbol=symbol,
            bids=[(Decimal("50000"), Decimal("1"))],
            asks=[(Decimal("50001"), Decimal("1"))],
            timestamp=datetime.now(UTC),
        )

    async def get_candles(self, symbol: str, interval: str, limit: int = 100) -> list:
        from core.domain_types import Candle

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
            name=self._name,
            supported_symbols=["BTCUSDT", "ETHUSDT"],
            rate_limits={},
            fee_structure={},
            server_time=datetime.now(UTC),
        )

    async def health_check(self) -> bool:
        return True

    async def emit(self, data: Any) -> None:
        """Emit data to all active callbacks."""
        for callback in list(self._callbacks.values()):
            await callback(data)


@pytest.fixture
def registry() -> SymbolRegistry:
    r = SymbolRegistry()
    r.register("binance", ["BTCUSDT", "ETHUSDT"])
    r.register("bybit", ["BTCUSDT", "SOLUSDT"])
    return r


@pytest.fixture
def binance_adapter() -> StreamingFakeAdapter:
    return StreamingFakeAdapter("binance")


@pytest.fixture
def bybit_adapter() -> StreamingFakeAdapter:
    return StreamingFakeAdapter("bybit")


@pytest.fixture
async def hub(
    registry: SymbolRegistry,
    binance_adapter: StreamingFakeAdapter,
    bybit_adapter: StreamingFakeAdapter,
) -> MarketHub:
    h = MarketHub(symbol_registry=registry)
    h.register_adapter("binance", binance_adapter)
    h.register_adapter("bybit", bybit_adapter)
    await h.start()
    yield h
    await h.stop()


class TestMarketHubIntegration:
    @pytest.mark.asyncio
    async def test_fan_out_to_multiple_consumers(
        self, hub: MarketHub, binance_adapter: StreamingFakeAdapter
    ) -> None:
        """One WebSocket subscription fans out to N consumers."""
        received: list[TickerData] = []

        async def consumer_a(data: TickerData) -> None:
            received.append(data)

        async def consumer_b(data: TickerData) -> None:
            received.append(data)

        async def consumer_c(data: TickerData) -> None:
            received.append(data)

        sub_a = await hub.subscribe("binance", "BTCUSDT", "ticker", consumer_a)
        sub_b = await hub.subscribe("binance", "BTCUSDT", "ticker", consumer_b)
        sub_c = await hub.subscribe("binance", "BTCUSDT", "ticker", consumer_c)

        assert hub.active_websocket_subscriptions() == 1
        assert hub.consumer_count() == 3

        ticker = TickerData(
            symbol="BTCUSDT",
            bid=Decimal("50000"),
            ask=Decimal("50001"),
            last=Decimal("50000.50"),
            volume=Decimal("1000"),
            timestamp=datetime.now(UTC),
        )
        await binance_adapter.emit(ticker)

        await asyncio.sleep(0.1)

        assert len(received) == 3
        assert all(r.last == Decimal("50000.50") for r in received)

        for sid in [sub_a, sub_b, sub_c]:
            await hub.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_cache_persists_during_reconnect(
        self, hub: MarketHub, binance_adapter: StreamingFakeAdapter
    ) -> None:
        """Cache data should survive a connector reconnect cycle."""
        ticker = TickerData(
            symbol="BTCUSDT",
            bid=Decimal("50000"),
            ask=Decimal("50001"),
            last=Decimal("50000.50"),
            volume=Decimal("1000"),
            timestamp=datetime.now(UTC),
        )
        hub.cache.update_ticker("binance", "BTCUSDT", ticker)

        connector = hub._connectors["binance"]
        await connector.reconnect()

        cached = await hub.get_ticker("binance", "BTCUSDT")
        assert cached.last == Decimal("50000.50")

    @pytest.mark.asyncio
    async def test_multi_exchange_isolation(
        self,
        hub: MarketHub,
        binance_adapter: StreamingFakeAdapter,
        bybit_adapter: StreamingFakeAdapter,
    ) -> None:
        """Subscriptions on different exchanges are fully isolated."""
        binance_received: list[Any] = []
        bybit_received: list[Any] = []

        async def binance_cb(data: Any) -> None:
            binance_received.append(data)

        async def bybit_cb(data: Any) -> None:
            bybit_received.append(data)

        await hub.subscribe("binance", "BTCUSDT", "ticker", binance_cb)
        await hub.subscribe("bybit", "BTCUSDT", "ticker", bybit_cb)

        assert hub.active_websocket_subscriptions() == 2

        ticker = TickerData(
            symbol="BTCUSDT",
            bid=Decimal("50000"),
            ask=Decimal("50001"),
            last=Decimal("50000.50"),
            volume=Decimal("1000"),
            timestamp=datetime.now(UTC),
        )
        await binance_adapter.emit(ticker)
        await asyncio.sleep(0.1)

        assert len(binance_received) == 1
        assert len(bybit_received) == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_last_consumer_closes_websocket(
        self, hub: MarketHub
    ) -> None:
        """When last consumer unsubscribes, the WebSocket is closed."""
        sub1 = await hub.subscribe("binance", "BTCUSDT", "ticker", lambda d: None)
        sub2 = await hub.subscribe("binance", "BTCUSDT", "ticker", lambda d: None)
        assert hub.active_websocket_subscriptions() == 1

        await hub.unsubscribe(sub1)
        assert hub.active_websocket_subscriptions() == 1

        await hub.unsubscribe(sub2)
        assert hub.active_websocket_subscriptions() == 0

    @pytest.mark.asyncio
    async def test_status_transitions(
        self, hub: MarketHub, binance_adapter: StreamingFakeAdapter
    ) -> None:
        """Verify status transitions: DISCONNECTED -> CONNECTING -> CONNECTED."""
        from market.base import MarketStatus

        sub_id = await hub.subscribe("binance", "BTCUSDT", "ticker", lambda d: None)
        status = await hub.get_status("binance", "BTCUSDT")
        assert status == MarketStatus.CONNECTED

        connector = hub._connectors["binance"]
        connector.mark_reconnecting("BTCUSDT")
        status = await hub.get_status("binance", "BTCUSDT")
        assert status == MarketStatus.RECONNECTING

        await connector.reconnect()
        status = await hub.get_status("binance", "BTCUSDT")
        assert status == MarketStatus.CONNECTED

        await hub.unsubscribe(sub_id)

    @pytest.mark.asyncio
    async def test_snapshot_reports_all_metrics(self, hub: MarketHub) -> None:
        await hub.subscribe("binance", "BTCUSDT", "ticker", lambda d: None)
        await hub.subscribe("bybit", "SOLUSDT", "ticker", lambda d: None)

        snap = hub.snapshot()
        assert snap["running"] is True
        assert snap["active_logical_subscriptions"] == 2
        assert snap["active_websocket_subscriptions"] == 2
        assert snap["consumer_subscriptions"] == 2
        assert "binance" in snap["exchanges"]
        assert "bybit" in snap["exchanges"]
