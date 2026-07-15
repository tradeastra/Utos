"""
Unit tests for ConnectionRecovery (Layer 1).
"""

from decimal import Decimal

import pytest

from engine.recovery.connection import ConnectionRecovery, QueuedOrder


class TestRedisRecovery:

    @pytest.mark.asyncio
    async def test_redis_recover_with_health_check_ok(self) -> None:
        cr = ConnectionRecovery(redis_health_check=lambda: True)
        result = await cr.recover_redis()
        assert result is True
        assert cr.is_redis_connected() is True

    @pytest.mark.asyncio
    async def test_redis_recover_with_health_check_fail(self) -> None:
        cr = ConnectionRecovery(redis_health_check=lambda: False)
        result = await cr.recover_redis()
        assert result is False
        assert cr.is_redis_connected() is False

    @pytest.mark.asyncio
    async def test_redis_recover_no_health_check(self) -> None:
        cr = ConnectionRecovery()
        result = await cr.recover_redis()
        assert result is True

    @pytest.mark.asyncio
    async def test_redis_recover_health_check_exception(self) -> None:
        def boom() -> bool:
            raise ConnectionError("Redis down")
        cr = ConnectionRecovery(redis_health_check=boom)
        result = await cr.recover_redis()
        assert result is False
        assert cr.is_redis_connected() is False


class TestPostgresRecovery:

    @pytest.mark.asyncio
    async def test_postgres_recover_ok(self) -> None:
        cr = ConnectionRecovery(postgres_health_check=lambda: True)
        result = await cr.recover_postgres()
        assert result is True
        assert cr.is_postgres_connected() is True

    @pytest.mark.asyncio
    async def test_postgres_recover_fail(self) -> None:
        cr = ConnectionRecovery(postgres_health_check=lambda: False)
        result = await cr.recover_postgres()
        assert result is False

    @pytest.mark.asyncio
    async def test_postgres_recover_exception(self) -> None:
        def boom() -> bool:
            raise ConnectionError("PG down")
        cr = ConnectionRecovery(postgres_health_check=boom)
        result = await cr.recover_postgres()
        assert result is False


class TestExchangeDisconnect:

    @pytest.mark.asyncio
    async def test_disconnect_marks_exchange_offline(self) -> None:
        cr = ConnectionRecovery()
        await cr.on_exchange_disconnect("binance", "acc-1")
        assert cr.is_exchange_connected("binance") is False

    @pytest.mark.asyncio
    async def test_reconnect_restores_connection(self) -> None:
        cr = ConnectionRecovery()
        await cr.on_exchange_disconnect("binance", "acc-1")
        assert cr.is_exchange_connected("binance") is False
        await cr.on_exchange_reconnect("binance", "acc-1")
        assert cr.is_exchange_connected("binance") is True


class TestResubscribeAndResync:

    @pytest.mark.asyncio
    async def test_resubscribe_all(self) -> None:
        called: list[tuple[str, list[str]]] = []
        def fake_resub(acc: str, syms: list[str]) -> bool:
            called.append((acc, syms))
            return True
        cr = ConnectionRecovery(resubscribe_fn=fake_resub)
        result = await cr.resubscribe_all("acc-1", ["BTCUSDT", "ETHUSDT"])
        assert result is True
        assert called == [("acc-1", ["BTCUSDT", "ETHUSDT"])]

    @pytest.mark.asyncio
    async def test_resubscribe_no_fn(self) -> None:
        cr = ConnectionRecovery()
        result = await cr.resubscribe_all("acc-1", ["BTCUSDT"])
        assert result is True

    @pytest.mark.asyncio
    async def test_resubscribe_exception(self) -> None:
        def boom(acc: str, syms: list[str]) -> bool:
            raise RuntimeError("fail")
        cr = ConnectionRecovery(resubscribe_fn=boom)
        result = await cr.resubscribe_all("acc-1", ["BTCUSDT"])
        assert result is False

    @pytest.mark.asyncio
    async def test_resync_prices(self) -> None:
        def fake_prices(syms: list[str]) -> dict[str, Decimal]:
            return {s: Decimal("100") for s in syms}
        cr = ConnectionRecovery(resync_prices_fn=fake_prices)
        result = await cr.resync_prices(["BTCUSDT", "ETHUSDT"])
        assert result == {"BTCUSDT": Decimal("100"), "ETHUSDT": Decimal("100")}

    @pytest.mark.asyncio
    async def test_resync_prices_no_fn(self) -> None:
        cr = ConnectionRecovery()
        result = await cr.resync_prices(["BTCUSDT"])
        assert result == {}


class TestOrderQueue:

    def test_queue_order(self) -> None:
        cr = ConnectionRecovery()
        order = QueuedOrder(
            instance_id="inst-1",
            account_id="acc-1",
            exchange="binance",
            symbol="BTCUSDT",
            side="buy",
            quantity=Decimal("1"),
            price=Decimal("100"),
        )
        cr.queue_order(order)
        assert cr.get_queue_size() == 1
        metrics = cr.get_metrics()
        assert metrics["orders_queued"] == 1

    @pytest.mark.asyncio
    async def test_replay_queued_orders(self) -> None:
        placed: list[QueuedOrder] = []
        def fake_place(order: QueuedOrder) -> str:
            placed.append(order)
            return "order-id"
        cr = ConnectionRecovery(place_order_fn=fake_place)
        order = QueuedOrder(
            instance_id="inst-1",
            account_id="acc-1",
            exchange="binance",
            symbol="BTCUSDT",
            side="buy",
            quantity=Decimal("1"),
            price=Decimal("100"),
        )
        cr.queue_order(order)
        results = await cr.replay_queued_orders()
        assert len(results) == 1
        assert cr.get_queue_size() == 0
        assert len(placed) == 1
        metrics = cr.get_metrics()
        assert metrics["orders_replayed"] == 1

    @pytest.mark.asyncio
    async def test_replay_empty_queue(self) -> None:
        cr = ConnectionRecovery()
        results = await cr.replay_queued_orders()
        assert results == []

    @pytest.mark.asyncio
    async def test_replay_order_exception(self) -> None:
        def boom(order: QueuedOrder) -> str:
            raise RuntimeError("Exchange rejected")
        cr = ConnectionRecovery(place_order_fn=boom)
        order = QueuedOrder(
            instance_id="inst-1",
            account_id="acc-1",
            exchange="binance",
            symbol="BTCUSDT",
            side="buy",
            quantity=Decimal("1"),
            price=Decimal("100"),
        )
        cr.queue_order(order)
        results = await cr.replay_queued_orders()
        assert len(results) == 0
        metrics = cr.get_metrics()
        assert metrics["orders_replayed_failed"] == 1


class TestMetrics:

    @pytest.mark.asyncio
    async def test_metrics_tracked(self) -> None:
        cr = ConnectionRecovery(
            redis_health_check=lambda: True,
            postgres_health_check=lambda: True,
        )
        await cr.recover_redis()
        await cr.recover_postgres()
        await cr.on_exchange_disconnect("binance", "acc-1")
        await cr.on_exchange_reconnect("binance", "acc-1")
        metrics = cr.get_metrics()
        assert metrics["redis_recoveries"] == 1
        assert metrics["postgres_recoveries"] == 1
        assert metrics["exchange_reconnects"] == 1
