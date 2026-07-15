"""
Integration tests for Sprint 12: Worker Scheduler & Event Bus.

Tests event flow across engines, worker lifecycle with scheduler,
retry → DLQ pipeline, and heartbeat monitoring.
"""

import pytest

from engine.scheduler.bus import EventBus
from engine.scheduler.dlq import DeadLetterQueue
from engine.scheduler.heartbeat import HeartbeatMonitor
from engine.scheduler.manager import WorkerManager
from engine.scheduler.retry import RetryWorker
from engine.scheduler.scheduler import JobScheduler


class TestEventFlowAcrossEngines:
    """Verify EventBus routes events to multiple engine subscribers."""

    @pytest.mark.asyncio
    async def test_order_filled_reaches_all_engines(self) -> None:
        bus = EventBus()
        grid_received: list[dict] = []
        profit_lock_received: list[dict] = []
        portfolio_received: list[dict] = []
        risk_received: list[dict] = []

        bus.subscribe("ORDER_FILLED", lambda e: grid_received.append(e))
        bus.subscribe("ORDER_FILLED", lambda e: profit_lock_received.append(e))
        bus.subscribe("ORDER_FILLED", lambda e: portfolio_received.append(e))
        bus.subscribe("ORDER_FILLED", lambda e: risk_received.append(e))

        await bus.publish("ORDER_FILLED", {
            "order_id": "ord-1",
            "symbol": "BTCUSDT",
            "side": "buy",
            "quantity": "1.5",
            "price": "50000",
        })

        assert len(grid_received) == 1
        assert len(profit_lock_received) == 1
        assert len(portfolio_received) == 1
        assert len(risk_received) == 1
        assert grid_received[0]["data"]["order_id"] == "ord-1"

    @pytest.mark.asyncio
    async def test_different_event_types_isolated(self) -> None:
        bus = EventBus()
        order_events: list[dict] = []
        price_events: list[dict] = []

        bus.subscribe("ORDER_FILLED", lambda e: order_events.append(e))
        bus.subscribe("PRICE_UPDATE", lambda e: price_events.append(e))

        await bus.publish("ORDER_FILLED", {"v": 1})
        await bus.publish("PRICE_UPDATE", {"v": 2})

        assert len(order_events) == 1
        assert len(price_events) == 1
        assert order_events[0]["data"]["v"] == 1
        assert price_events[0]["data"]["v"] == 2


class TestWorkerSchedulerIntegration:
    """WorkerManager + JobScheduler working together."""

    @pytest.mark.asyncio
    async def test_worker_runs_scheduled_task(self) -> None:
        wm = WorkerManager()
        js = JobScheduler()

        executed: list[str] = []

        async def cleanup_task() -> str:
            executed.append("cleanup")
            return "done"

        wm.register_worker("cleanup-worker", cleanup_task)
        wm.start_worker("cleanup-worker")

        js.add_task("cleanup", "cleanup", 60, coroutine=cleanup_task)
        results = await js.run_all()

        assert len(results) == 1
        assert results[0]["status"] == "success"
        assert wm.get_worker_status("cleanup-worker").state == "running"
        wm.stop_worker("cleanup-worker")


class TestRetryDLQPipeline:
    """RetryWorker → DeadLetterQueue pipeline."""

    @pytest.mark.asyncio
    async def test_failed_task_moves_to_dlq(self) -> None:
        dlq_entries: list[tuple] = []

        def dlq_cb(job, reason: str) -> None:
            dlq_entries.append((job.task_id, reason))

        dlq = DeadLetterQueue()
        rw = RetryWorker(max_retries=2, backoff_base=0, dlq_callback=dlq_cb)

        def always_fails() -> None:
            raise RuntimeError("permanent failure")

        rw.submit("task-1", always_fails)
        await rw.process_queue()
        if rw.get_queue_size() > 0:
            await rw.process_queue()

        assert rw.get_metrics()["jobs_failed"] == 1
        assert rw.get_metrics()["moved_to_dlq"] == 1
        assert len(dlq_entries) == 1
        assert dlq_entries[0][0] == "task-1"

    @pytest.mark.asyncio
    async def test_retry_succeeds_before_dlq(self) -> None:
        dlq = DeadLetterQueue()
        dlq_count: list[int] = []

        def dlq_cb(job, reason: str) -> None:
            dlq_count.append(1)

        rw = RetryWorker(max_retries=3, backoff_base=0, dlq_callback=dlq_cb)

        attempts: list[int] = []

        def flaky() -> str:
            attempts.append(1)
            if len(attempts) < 3:
                raise RuntimeError("not yet")
            return "success"

        rw.submit("task-1", flaky)
        await rw.process_queue()
        while rw.get_queue_size() > 0:
            await rw.process_queue()

        assert rw.get_metrics()["jobs_succeeded"] == 1
        assert rw.get_metrics()["moved_to_dlq"] == 0
        assert len(dlq_count) == 0


class TestHeartbeatWithMultipleComponents:
    """HeartbeatMonitor monitoring multiple system components."""

    @pytest.mark.asyncio
    async def test_monitor_all_components(self) -> None:
        hm = HeartbeatMonitor()

        hm.register("trading_process", lambda: True)
        hm.register("worker", lambda: True)
        hm.register("exchange_connector", lambda: False)
        hm.register("market_hub", lambda: True)

        results = await hm.check_all()
        assert len(results) == 4

        unhealthy = hm.get_unhealthy()
        assert len(unhealthy) == 1
        assert unhealthy[0].component == "exchange_connector"

        healthy = hm.get_healthy()
        assert len(healthy) == 3

    @pytest.mark.asyncio
    async def test_unhealthy_component_detected(self) -> None:
        hm = HeartbeatMonitor()

        def check_redis() -> bool:
            raise ConnectionError("Redis unreachable")

        hm.register("redis", check_redis)
        result = await hm.check("redis")
        assert result.healthy is False
        assert "Redis unreachable" in result.error


class TestFullSchedulerFlow:
    """Full flow: EventBus → JobScheduler → RetryWorker → DLQ."""

    @pytest.mark.asyncio
    async def test_event_triggered_task_with_retry(self) -> None:
        bus = EventBus()
        js = JobScheduler()
        dlq = DeadLetterQueue()

        dlq_entries: list[tuple] = []
        def dlq_cb(job, reason: str) -> None:
            dlq_entries.append((job.task_id, reason))

        rw = RetryWorker(max_retries=2, backoff_base=0, dlq_callback=dlq_cb)

        task_triggered: list[dict] = []
        bus.subscribe("TRIGGER_TASK", lambda e: task_triggered.append(e))

        async def failing_task() -> None:
            raise RuntimeError("task error")

        js.add_task("failing", "retry", 10, coroutine=failing_task)

        await bus.publish("TRIGGER_TASK", {"task": "failing"})
        assert len(task_triggered) == 1

        result = await js.run_all()
        assert result[0]["status"] == "failed"

        rw.submit("failing", failing_task)
        await rw.process_queue()
        while rw.get_queue_size() > 0:
            await rw.process_queue()

        assert rw.get_metrics()["moved_to_dlq"] == 1
        assert len(dlq_entries) == 1
