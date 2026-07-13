"""
Performance tests for MarketHub — fan-out throughput, cache read latency,
and subscription deduplication at scale.
"""

import asyncio
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable

import pytest

from core.types import TickerData
from market.hub.market_hub import MarketHub
from market.symbol_registry import SymbolRegistry


class PerfFakeAdapter:
    """Minimal adapter for performance tests."""

    def __init__(self, name: str = "binance") -> None:
        self._name = name
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
        return True

    async def connect_account(self) -> bool:
        return True

    async def disconnect(self) -> None:
        pass

    async def is_market_connected(self) -> bool:
        return True

    async def is_account_connected(self) -> bool:
        return True

    async def subscribe_market(self, symbol: str, channel: str, callback: Callable) -> str:
        self._sub_counter += 1
        sub_id = f"perf_sub_{self._sub_counter}"
        self._callbacks[sub_id] = callback
        return sub_id

    async def unsubscribe_market(self, sub_id: str) -> None:
        self._callbacks.pop(sub_id, None)

    async def get_ticker(self, symbol: str) -> TickerData:
        return TickerData(
            symbol=symbol, bid=Decimal("50000"), ask=Decimal("50001"),
            last=Decimal("50000.50"), volume=Decimal("1000"),
            timestamp=datetime.now(timezone.utc),
        )

    async def get_order_book(self, symbol: str, depth: int = 20) -> Any:
        from core.types import OrderBook
        return OrderBook(
            symbol=symbol,
            bids=[(Decimal("50000"), Decimal("1"))],
            asks=[(Decimal("50001"), Decimal("1"))],
            timestamp=datetime.now(timezone.utc),
        )

    async def get_candles(self, symbol: str, interval: str, limit: int = 100) -> list:
        from core.types import Candle
        return [Candle(
            symbol=symbol, interval=interval,
            open=Decimal("50000"), high=Decimal("50100"),
            low=Decimal("49900"), close=Decimal("50050"),
            volume=Decimal("100"),
            timestamp=datetime.now(timezone.utc),
        )]

    async def get_exchange_info(self) -> Any:
        from core.types import ExchangeInfo
        return ExchangeInfo(
            name=self._name,
            supported_symbols=["BTCUSDT", "ETHUSDT"],
            rate_limits={}, fee_structure={},
            server_time=datetime.now(timezone.utc),
        )

    async def health_check(self) -> bool:
        return True

    async def emit(self, data: Any) -> None:
        for cb in list(self._callbacks.values()):
            await cb(data)


@pytest.fixture
def registry() -> SymbolRegistry:
    r = SymbolRegistry()
    r.register("binance", ["BTCUSDT", "ETHUSDT"])
    return r


@pytest.fixture
def adapter() -> PerfFakeAdapter:
    return PerfFakeAdapter("binance")


@pytest.fixture
async def hub(registry: SymbolRegistry, adapter: PerfFakeAdapter) -> MarketHub:
    h = MarketHub(symbol_registry=registry)
    h.register_adapter("binance", adapter)
    await h.start()
    yield h
    await h.stop()


class TestMarketHubPerformance:
    @pytest.mark.asyncio
    async def test_cache_read_latency(self, hub: MarketHub) -> None:
        """Cache reads should complete in under 1ms per call."""
        ticker = TickerData(
            symbol="BTCUSDT", bid=Decimal("50000"), ask=Decimal("50001"),
            last=Decimal("50000.50"), volume=Decimal("1000"),
            timestamp=datetime.now(timezone.utc),
        )
        hub.cache.update_ticker("binance", "BTCUSDT", ticker)

        iterations = 10000
        start = time.perf_counter()
        for _ in range(iterations):
            hub.cache.get_ticker("binance", "BTCUSDT")
        elapsed = time.perf_counter() - start
        per_call_us = (elapsed / iterations) * 1_000_000

        assert per_call_us < 100, f"Cache read took {per_call_us:.1f}µs per call (expected <100µs)"

    @pytest.mark.asyncio
    async def test_fan_out_50_consumers(self, hub: MarketHub, adapter: PerfFakeAdapter) -> None:
        """50 consumers should all receive data from a single WebSocket."""
        received: list[TickerData] = []
        lock = asyncio.Lock()

        async def make_cb(idx: int) -> Callable:
            async def cb(data: TickerData) -> None:
                async with lock:
                    received.append(data)
            return cb

        sub_ids = []
        for i in range(50):
            cb = await make_cb(i)
            sub_ids.append(await hub.subscribe("binance", "BTCUSDT", "ticker", cb))

        assert hub.active_websocket_subscriptions() == 1
        assert hub.consumer_count() == 50

        ticker = TickerData(
            symbol="BTCUSDT", bid=Decimal("50000"), ask=Decimal("50001"),
            last=Decimal("50000.50"), volume=Decimal("1000"),
            timestamp=datetime.now(timezone.utc),
        )

        start = time.perf_counter()
        await adapter.emit(ticker)
        await asyncio.sleep(0.5)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(received) == 50, f"Expected 50 fan-outs, got {len(received)}"
        assert elapsed_ms < 1000, f"Fan-out to 50 consumers took {elapsed_ms:.1f}ms"

        for sid in sub_ids:
            await hub.unsubscribe(sid)

    @pytest.mark.asyncio
    async def test_subscription_dedup_at_scale(self, hub: MarketHub) -> None:
        """100 consumers on same stream = 1 WebSocket subscription."""
        sub_ids = []
        for _ in range(100):
            sub_ids.append(await hub.subscribe("binance", "BTCUSDT", "ticker", lambda d: None))

        assert hub.active_websocket_subscriptions() == 1
        assert hub.consumer_count() == 100

        for sid in sub_ids:
            await hub.unsubscribe(sid)

        assert hub.active_websocket_subscriptions() == 0

    @pytest.mark.asyncio
    async def test_concurrent_cache_writes(self, hub: MarketHub) -> None:
        """1000 concurrent cache updates should not raise."""
        async def write_one(idx: int) -> None:
            hub.cache.update_ticker("binance", "BTCUSDT", TickerData(
                symbol="BTCUSDT",
                bid=Decimal(str(50000 + idx)),
                ask=Decimal(str(50001 + idx)),
                last=Decimal(str(50000 + idx)),
                volume=Decimal("1000"),
                timestamp=datetime.now(timezone.utc),
            ))

        await asyncio.gather(*[write_one(i) for i in range(1000)])
        assert hub.cache.get_ticker("binance", "BTCUSDT") is not None
        assert hub.cache.get_message_count("binance", "BTCUSDT") == 1000

    @pytest.mark.asyncio
    async def test_snapshot_under_load(self, hub: MarketHub, adapter: PerfFakeAdapter) -> None:
        """Snapshot should be fast even with active subscriptions."""
        for _ in range(20):
            await hub.subscribe("binance", "BTCUSDT", "ticker", lambda d: None)

        start = time.perf_counter()
        snap = hub.snapshot()
        elapsed_us = (time.perf_counter() - start) * 1_000_000

        assert elapsed_us < 1000, f"Snapshot took {elapsed_us:.0f}µs"
        assert snap["consumer_subscriptions"] == 20
        assert snap["active_websocket_subscriptions"] == 1
