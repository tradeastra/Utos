"""Unit tests for HeartbeatMonitor."""

import pytest
from engine.scheduler.heartbeat import HeartbeatMonitor


class TestRegister:

    def test_register(self) -> None:
        hm = HeartbeatMonitor()
        hm.register("trading_process", lambda: True)
        assert "trading_process" in hm.get_registered_components()
        assert hm.get_metrics()["checks_registered"] == 1

    def test_unregister(self) -> None:
        hm = HeartbeatMonitor()
        hm.register("worker", lambda: True)
        assert hm.unregister("worker") is True
        assert "worker" not in hm.get_registered_components()

    def test_unregister_nonexistent(self) -> None:
        hm = HeartbeatMonitor()
        assert hm.unregister("fake") is False


class TestCheck:

    @pytest.mark.asyncio
    async def test_check_healthy(self) -> None:
        hm = HeartbeatMonitor()
        hm.register("redis", lambda: True)
        result = await hm.check("redis")
        assert result.healthy is True
        assert result.error is None
        assert result.response_time_ms >= 0

    @pytest.mark.asyncio
    async def test_check_unhealthy(self) -> None:
        hm = HeartbeatMonitor()
        hm.register("postgres", lambda: False)
        result = await hm.check("postgres")
        assert result.healthy is False

    @pytest.mark.asyncio
    async def test_check_exception(self) -> None:
        hm = HeartbeatMonitor()

        def boom() -> bool:
            raise ConnectionError("PG down")

        hm.register("postgres", boom)
        result = await hm.check("postgres")
        assert result.healthy is False
        assert "PG down" in result.error

    @pytest.mark.asyncio
    async def test_check_unregistered(self) -> None:
        hm = HeartbeatMonitor()
        result = await hm.check("unknown")
        assert result.healthy is False
        assert "not registered" in result.error

    @pytest.mark.asyncio
    async def test_check_async_fn(self) -> None:
        hm = HeartbeatMonitor()

        async def async_check() -> bool:
            return True

        hm.register("market_hub", async_check)
        result = await hm.check("market_hub")
        assert result.healthy is True

    @pytest.mark.asyncio
    async def test_check_tuple_result(self) -> None:
        hm = HeartbeatMonitor()
        hm.register("exchange", lambda: (True, None))
        result = await hm.check("exchange")
        assert result.healthy is True
        assert result.error is None

    @pytest.mark.asyncio
    async def test_check_tuple_unhealthy(self) -> None:
        hm = HeartbeatMonitor()
        hm.register("exchange", lambda: (False, "timeout"))
        result = await hm.check("exchange")
        assert result.healthy is False
        assert "timeout" in result.error


class TestCheckAll:

    @pytest.mark.asyncio
    async def test_check_all(self) -> None:
        hm = HeartbeatMonitor()
        hm.register("a", lambda: True)
        hm.register("b", lambda: False)
        hm.register("c", lambda: True)
        results = await hm.check_all()
        assert len(results) == 3
        healthy = [r for r in results if r.healthy]
        unhealthy = [r for r in results if not r.healthy]
        assert len(healthy) == 2
        assert len(unhealthy) == 1


class TestQueries:

    @pytest.mark.asyncio
    async def test_get_unhealthy(self) -> None:
        hm = HeartbeatMonitor()
        hm.register("a", lambda: True)
        hm.register("b", lambda: False)
        await hm.check_all()
        unhealthy = hm.get_unhealthy()
        assert len(unhealthy) == 1
        assert unhealthy[0].component == "b"

    @pytest.mark.asyncio
    async def test_get_healthy(self) -> None:
        hm = HeartbeatMonitor()
        hm.register("a", lambda: True)
        hm.register("b", lambda: False)
        await hm.check_all()
        healthy = hm.get_healthy()
        assert len(healthy) == 1
        assert healthy[0].component == "a"

    @pytest.mark.asyncio
    async def test_metrics(self) -> None:
        hm = HeartbeatMonitor()
        hm.register("a", lambda: True)
        hm.register("b", lambda: False)
        await hm.check_all()
        metrics = hm.get_metrics()
        assert metrics["checks_run"] == 2
        assert metrics["checks_healthy"] == 1
        assert metrics["checks_unhealthy"] == 1
