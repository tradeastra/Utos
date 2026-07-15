"""Unit tests for JobScheduler."""

from datetime import datetime, timezone, timedelta

import pytest

from engine.scheduler.scheduler import JobScheduler, ScheduledTask


class TestAddRemoveTask:

    def test_add_task(self) -> None:
        js = JobScheduler()
        task_id = js.add_task("cleanup", "cleanup", 60)
        assert js.get_task_count() == 1
        assert js.get_metrics()["tasks_added"] == 1

    def test_remove_task(self) -> None:
        js = JobScheduler()
        task_id = js.add_task("cleanup", "cleanup", 60)
        assert js.remove_task(task_id) is True
        assert js.get_task_count() == 0
        assert js.get_metrics()["tasks_removed"] == 1

    def test_remove_nonexistent(self) -> None:
        js = JobScheduler()
        assert js.remove_task("fake") is False

    def test_enable_disable(self) -> None:
        js = JobScheduler()
        task_id = js.add_task("cleanup", "cleanup", 60)
        assert js.disable_task(task_id) is True
        assert js.enable_task(task_id) is True


class TestRunTask:

    @pytest.mark.asyncio
    async def test_run_sync_task(self) -> None:
        js = JobScheduler()
        called: list[bool] = []

        def task_fn() -> str:
            called.append(True)
            return "done"

        task_id = js.add_task("sync-task", "cleanup", 60, coroutine=task_fn)
        result = await js.run_task(task_id)
        assert result["status"] == "success"
        assert result["result"] == "done"
        assert len(called) == 1

    @pytest.mark.asyncio
    async def test_run_async_task(self) -> None:
        js = JobScheduler()

        async def task_fn() -> int:
            return 42

        task_id = js.add_task("async-task", "checkpoint", 30, coroutine=task_fn)
        result = await js.run_task(task_id)
        assert result["status"] == "success"
        assert result["result"] == 42

    @pytest.mark.asyncio
    async def test_run_task_failure(self) -> None:
        js = JobScheduler()

        def boom() -> None:
            raise RuntimeError("task failed")

        task_id = js.add_task("bad-task", "sync", 60, coroutine=boom)
        result = await js.run_task(task_id)
        assert result["status"] == "failed"
        assert "task failed" in result["error"]

    @pytest.mark.asyncio
    async def test_run_disabled_task(self) -> None:
        js = JobScheduler()
        task_id = js.add_task("disabled", "cleanup", 60, coroutine=lambda: None)
        js.disable_task(task_id)
        result = await js.run_task(task_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_run_all(self) -> None:
        js = JobScheduler()
        async def t1() -> int:
            return 1
        async def t2() -> int:
            return 2
        js.add_task("t1", "cleanup", 60, coroutine=t1)
        js.add_task("t2", "sync", 30, coroutine=t2)
        results = await js.run_all()
        assert len(results) == 2
        assert all(r["status"] == "success" for r in results)


class TestPendingTasks:

    def test_get_pending_tasks(self) -> None:
        js = JobScheduler()
        js.add_task("t1", "cleanup", 60)
        now = datetime.now(timezone.utc)
        pending = js.get_pending_tasks(now=now + timedelta(seconds=120))
        assert len(pending) == 1

    def test_no_pending_future(self) -> None:
        js = JobScheduler()
        js.add_task("t1", "cleanup", 60)
        now = datetime.now(timezone.utc)
        pending = js.get_pending_tasks(now=now)
        assert len(pending) == 0


class TestQueries:

    def test_get_tasks_by_type(self) -> None:
        js = JobScheduler()
        js.add_task("c1", "cleanup", 60)
        js.add_task("c2", "cleanup", 60)
        js.add_task("h1", "heartbeat", 10)
        cleanups = js.get_tasks_by_type("cleanup")
        assert len(cleanups) == 2
        heartbeats = js.get_tasks_by_type("heartbeat")
        assert len(heartbeats) == 1
