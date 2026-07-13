"""
Unit tests for SubscriptionManager.
"""

from typing import Any

import pytest

from market.subscription_manager import SubscriptionManager


class FakeSubscribeBackend:
    """Simulates the underlying adapter subscribe/unsubscribe."""

    def __init__(self) -> None:
        self.subscriptions: dict[str, tuple[str, str, str]] = {}
        self._counter = 0
        self.subscribe_calls = 0
        self.unsubscribe_calls = 0

    async def subscribe_fn(
        self, exchange: str, symbol: str, channel: str, callback: Any
    ) -> str:
        self.subscribe_calls += 1
        self._counter += 1
        sub_id = f"ws_{self._counter}"
        self.subscriptions[sub_id] = (exchange, symbol, channel)
        return sub_id

    async def unsubscribe_fn(self, sub_id: str) -> None:
        self.unsubscribe_calls += 1
        self.subscriptions.pop(sub_id, None)


@pytest.fixture
def backend() -> FakeSubscribeBackend:
    return FakeSubscribeBackend()


@pytest.fixture
def manager(backend: FakeSubscribeBackend) -> SubscriptionManager:
    return SubscriptionManager(
        subscribe_fn=backend.subscribe_fn,
        unsubscribe_fn=backend.unsubscribe_fn,
    )


async def _noop_callback(data: Any) -> None:
    pass


class TestSubscriptionManager:
    @pytest.mark.asyncio
    async def test_single_subscription(self, manager: SubscriptionManager, backend: FakeSubscribeBackend) -> None:
        sub_id = await manager.subscribe("binance", "BTCUSDT", "ticker", _noop_callback)
        assert sub_id is not None
        assert backend.subscribe_calls == 1
        assert manager.active_count() == 1
        assert manager.consumer_count() == 1

    @pytest.mark.asyncio
    async def test_deduplicated_subscription(self, manager: SubscriptionManager, backend: FakeSubscribeBackend) -> None:
        """Two consumers on same (exchange, symbol, channel) = 1 WebSocket."""
        sub1 = await manager.subscribe("binance", "BTCUSDT", "ticker", _noop_callback)
        sub2 = await manager.subscribe("binance", "BTCUSDT", "ticker", _noop_callback)
        assert sub1 != sub2
        assert backend.subscribe_calls == 1
        assert manager.active_count() == 1
        assert manager.consumer_count() == 2

    @pytest.mark.asyncio
    async def test_different_channels_separate(self, manager: SubscriptionManager, backend: FakeSubscribeBackend) -> None:
        await manager.subscribe("binance", "BTCUSDT", "ticker", _noop_callback)
        await manager.subscribe("binance", "BTCUSDT", "orderbook", _noop_callback)
        assert backend.subscribe_calls == 2
        assert manager.active_count() == 2

    @pytest.mark.asyncio
    async def test_different_exchanges_separate(self, manager: SubscriptionManager, backend: FakeSubscribeBackend) -> None:
        await manager.subscribe("binance", "BTCUSDT", "ticker", _noop_callback)
        await manager.subscribe("bybit", "BTCUSDT", "ticker", _noop_callback)
        assert backend.subscribe_calls == 2
        assert manager.active_count() == 2

    @pytest.mark.asyncio
    async def test_unsubscribe_keeps_stream(self, manager: SubscriptionManager, backend: FakeSubscribeBackend) -> None:
        """Unsub one consumer when two are active should NOT close the stream."""
        sub1 = await manager.subscribe("binance", "BTCUSDT", "ticker", _noop_callback)
        sub2 = await manager.subscribe("binance", "BTCUSDT", "ticker", _noop_callback)
        await manager.unsubscribe(sub1)
        assert backend.unsubscribe_calls == 0
        assert manager.active_count() == 1
        assert manager.consumer_count() == 1

    @pytest.mark.asyncio
    async def test_unsubscribe_last_closes_stream(self, manager: SubscriptionManager, backend: FakeSubscribeBackend) -> None:
        sub1 = await manager.subscribe("binance", "BTCUSDT", "ticker", _noop_callback)
        sub2 = await manager.subscribe("binance", "BTCUSDT", "ticker", _noop_callback)
        await manager.unsubscribe(sub1)
        await manager.unsubscribe(sub2)
        assert backend.unsubscribe_calls == 1
        assert manager.active_count() == 0
        assert manager.consumer_count() == 0

    @pytest.mark.asyncio
    async def test_unsubscribe_unknown_id(self, manager: SubscriptionManager) -> None:
        await manager.unsubscribe("nonexistent")
        assert manager.active_count() == 0

    @pytest.mark.asyncio
    async def test_is_active(self, manager: SubscriptionManager) -> None:
        await manager.subscribe("binance", "BTCUSDT", "ticker", _noop_callback)
        assert manager.is_active("binance", "BTCUSDT", "ticker") is True
        assert manager.is_active("binance", "ETHUSDT", "ticker") is False

    @pytest.mark.asyncio
    async def test_active_count_filtered(self, manager: SubscriptionManager) -> None:
        await manager.subscribe("binance", "BTCUSDT", "ticker", _noop_callback)
        await manager.subscribe("bybit", "BTCUSDT", "ticker", _noop_callback)
        assert manager.active_count(exchange="binance") == 1
        assert manager.active_count(exchange="bybit") == 1
        assert manager.active_count(symbol="BTCUSDT") == 2

    @pytest.mark.asyncio
    async def test_logical_keys(self, manager: SubscriptionManager) -> None:
        await manager.subscribe("binance", "BTCUSDT", "ticker", _noop_callback)
        await manager.subscribe("bybit", "ETHUSDT", "orderbook", _noop_callback)
        keys = manager.logical_keys()
        assert ("binance", "BTCUSDT", "ticker") in keys
        assert ("bybit", "ETHUSDT", "orderbook") in keys

    @pytest.mark.asyncio
    async def test_many_consumers_one_stream(self, manager: SubscriptionManager, backend: FakeSubscribeBackend) -> None:
        """10 consumers = 1 WebSocket subscription."""
        sub_ids = []
        for _ in range(10):
            sub_ids.append(await manager.subscribe("binance", "BTCUSDT", "ticker", _noop_callback))
        assert backend.subscribe_calls == 1
        assert manager.active_count() == 1
        assert manager.consumer_count() == 10
        for sid in sub_ids:
            await manager.unsubscribe(sid)
        assert backend.unsubscribe_calls == 1
        assert manager.active_count() == 0
