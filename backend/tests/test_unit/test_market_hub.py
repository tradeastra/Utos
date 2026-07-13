"""
Unit tests for MarketHub.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

import pytest

from core.types import Candle, OrderBook, TickerData
from market.base import MarketStatus
from market.cache.market_cache import MarketCache
from market.hub.market_hub import MarketHub
from market.symbol_registry import SymbolRegistry


class FakeAdapter:
    """Fake adapter for hub tests."""

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

    async def subscribe_market(self, symbol: str, channel: str, callback: Callable) -> str:
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
            timestamp=datetime.now(timezone.utc),
        )

    async def get_order_book(self, symbol: str, depth: int = 20) -> OrderBook:
        return OrderBook(
            symbol=symbol,
            bids=[(Decimal("50000"), Decimal("1.5"))],
            asks=[(Decimal("50001"), Decimal("1.0"))],
            timestamp=datetime.now(timezone.utc),
        )

    async def get_candles(self, symbol: str, interval: str, limit: int = 100) -> list[Candle]:
        return [
            Candle(
                symbol=symbol, interval=interval,
                open=Decimal("50000"), high=Decimal("50100"),
                low=Decimal("49900"), close=Decimal("50050"),
                volume=Decimal("100"),
                timestamp=datetime.now(timezone.utc),
            )
        ]

    async def get_exchange_info(self) -> Any:
        from core.types import ExchangeInfo
        return ExchangeInfo(
            name=self._name,
            supported_symbols=["BTCUSDT", "ETHUSDT"],
            rate_limits={},
            fee_structure={},
            server_time=datetime.now(timezone.utc),
        )

    async def health_check(self) -> bool:
        return True

    async def emit_ticker(self, symbol: str, ticker: TickerData) -> None:
        """Simulate a WebSocket ticker update."""
        for callback in self._callbacks.values():
            import asyncio
            asyncio.get_event_loop().create_task(callback(ticker))


@pytest.fixture
def binance_adapter() -> FakeAdapter:
    return FakeAdapter("binance")


@pytest.fixture
def bybit_adapter() -> FakeAdapter:
    return FakeAdapter("bybit")


@pytest.fixture
def registry() -> SymbolRegistry:
    r = SymbolRegistry()
    r.register("binance", ["BTCUSDT", "ETHUSDT"])
    r.register("bybit", ["BTCUSDT", "SOLUSDT"])
    return r


@pytest.fixture
async def hub(registry: SymbolRegistry, binance_adapter: FakeAdapter, bybit_adapter: FakeAdapter) -> MarketHub:
    h = MarketHub(symbol_registry=registry)
    h.register_adapter("binance", binance_adapter)
    h.register_adapter("bybit", bybit_adapter)
    await h.start()
    yield h
    await h.stop()


async def _noop(data: Any) -> None:
    pass


class TestMarketHub:
    @pytest.mark.asyncio
    async def test_register_adapter(self, registry: SymbolRegistry, binance_adapter: FakeAdapter) -> None:
        h = MarketHub(symbol_registry=registry)
        h.register_adapter("binance", binance_adapter)
        assert "binance" in h.exchanges()
        await h.stop()

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self, hub: MarketHub) -> None:
        sub_id = await hub.subscribe("binance", "BTCUSDT", "ticker", _noop)
        assert sub_id is not None
        assert hub.active_subscriptions() == 1
        await hub.unsubscribe(sub_id)
        assert hub.active_subscriptions() == 0

    @pytest.mark.asyncio
    async def test_deduplicated_subscription(self, hub: MarketHub) -> None:
        """10 consumers = 1 WebSocket."""
        sub_ids = []
        for _ in range(10):
            sub_ids.append(await hub.subscribe("binance", "BTCUSDT", "ticker", _noop))
        assert hub.active_subscriptions() == 1
        assert hub.active_websocket_subscriptions() == 1
        assert hub.consumer_count() == 10
        for sid in sub_ids:
            await hub.unsubscribe(sid)
        assert hub.active_subscriptions() == 0

    @pytest.mark.asyncio
    async def test_get_ticker_from_cache(self, hub: MarketHub) -> None:
        ticker = TickerData(
            symbol="BTCUSDT",
            bid=Decimal("50000"),
            ask=Decimal("50001"),
            last=Decimal("50000.50"),
            volume=Decimal("1000"),
            timestamp=datetime.now(timezone.utc),
        )
        hub.cache.update_ticker("binance", "BTCUSDT", ticker)
        result = await hub.get_ticker("binance", "BTCUSDT")
        assert result.symbol == "BTCUSDT"
        assert result.last == Decimal("50000.50")

    @pytest.mark.asyncio
    async def test_get_ticker_fallback_to_adapter(self, hub: MarketHub) -> None:
        """If not in cache, hub should fetch from adapter."""
        result = await hub.get_ticker("binance", "BTCUSDT")
        assert result.symbol == "BTCUSDT"
        assert result.last == Decimal("50000.50")
        assert hub.cache.get_ticker("binance", "BTCUSDT") is not None

    @pytest.mark.asyncio
    async def test_get_price_from_cache(self, hub: MarketHub) -> None:
        ticker = TickerData(
            symbol="BTCUSDT",
            bid=Decimal("50000"),
            ask=Decimal("50001"),
            last=Decimal("50000.50"),
            volume=Decimal("1000"),
            timestamp=datetime.now(timezone.utc),
        )
        hub.cache.update_ticker("binance", "BTCUSDT", ticker)
        price = await hub.get_price("binance", "BTCUSDT")
        assert price == Decimal("50000.50")

    @pytest.mark.asyncio
    async def test_get_orderbook_fallback(self, hub: MarketHub) -> None:
        ob = await hub.get_orderbook("binance", "BTCUSDT")
        assert ob.symbol == "BTCUSDT"
        assert len(ob.bids) == 1

    @pytest.mark.asyncio
    async def test_get_candles_fallback(self, hub: MarketHub) -> None:
        candles = await hub.get_candles("binance", "BTCUSDT", "1m")
        assert len(candles) == 1
        assert candles[0].interval == "1m"

    @pytest.mark.asyncio
    async def test_is_alive_false_no_data(self, hub: MarketHub) -> None:
        assert await hub.is_alive("binance", "BTCUSDT") is False

    @pytest.mark.asyncio
    async def test_get_status_disconnected_no_sub(self, hub: MarketHub) -> None:
        status = await hub.get_status("binance", "BTCUSDT")
        assert status == MarketStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_get_metrics(self, hub: MarketHub) -> None:
        m = await hub.get_metrics("binance", "BTCUSDT")
        assert m.exchange == "binance"
        assert m.symbol == "BTCUSDT"

    @pytest.mark.asyncio
    async def test_snapshot(self, hub: MarketHub) -> None:
        await hub.subscribe("binance", "BTCUSDT", "ticker", _noop)
        snap = hub.snapshot()
        assert snap["running"] is True
        assert snap["active_logical_subscriptions"] == 1
        assert snap["active_websocket_subscriptions"] == 1
        assert snap["consumer_subscriptions"] == 1
        assert "binance" in snap["exchanges"]

    @pytest.mark.asyncio
    async def test_multi_exchange(self, hub: MarketHub) -> None:
        await hub.subscribe("binance", "BTCUSDT", "ticker", _noop)
        await hub.subscribe("bybit", "BTCUSDT", "ticker", _noop)
        assert hub.active_subscriptions() == 2
        assert hub.active_websocket_subscriptions() == 2

    @pytest.mark.asyncio
    async def test_subscribe_unsupported_symbol(self, hub: MarketHub) -> None:
        from core.exceptions import SymbolNotSupported
        with pytest.raises(SymbolNotSupported):
            await hub.subscribe("binance", "DOGEUSDT", "ticker", _noop)

    @pytest.mark.asyncio
    async def test_subscribe_before_start_raises(self, registry: SymbolRegistry, binance_adapter: FakeAdapter) -> None:
        h = MarketHub(symbol_registry=registry)
        h.register_adapter("binance", binance_adapter)
        with pytest.raises(RuntimeError):
            await h.subscribe("binance", "BTCUSDT", "ticker", _noop)

    @pytest.mark.asyncio
    async def test_cache_survives_reconnect(self, hub: MarketHub) -> None:
        """Cache data should persist across connector reconnect."""
        ticker = TickerData(
            symbol="BTCUSDT",
            bid=Decimal("50000"),
            ask=Decimal("50001"),
            last=Decimal("50000.50"),
            volume=Decimal("1000"),
            timestamp=datetime.now(timezone.utc),
        )
        hub.cache.update_ticker("binance", "BTCUSDT", ticker)
        connector = hub._connectors["binance"]
        await connector.reconnect()
        result = await hub.get_ticker("binance", "BTCUSDT")
        assert result.last == Decimal("50000.50")

    @pytest.mark.asyncio
    async def test_stop_clears_cache(self, registry: SymbolRegistry, binance_adapter: FakeAdapter) -> None:
        h = MarketHub(symbol_registry=registry)
        h.register_adapter("binance", binance_adapter)
        await h.start()
        h.cache.update_ticker("binance", "BTCUSDT", TickerData(
            symbol="BTCUSDT", bid=Decimal("1"), ask=Decimal("1"),
            last=Decimal("1"), volume=Decimal("1"),
            timestamp=datetime.now(timezone.utc),
        ))
        assert h.cache.entry_count() == 1
        await h.stop()
        assert h.cache.entry_count() == 0
