"""Unit tests for RetryWorker."""

import pytest

from engine.scheduler.retry import RetryWorker


class TestSubmitAndProcess:

    @pytest.mark.asyncio
    async def test_success_on_first_try(self) -> None:
        rw = RetryWorker()
        called: list[int] = []

        def task() -> str:
            called.append(1)
            return "ok"

        rw.submit("task-1", task)
        results = await rw.process_queue()
        assert len(results) == 1
        assert results[0]["status"] == "success"
        assert len(called) == 1
        assert rw.get_metrics()["jobs_succeeded"] == 1

    @pytest.mark.asyncio
    async def test_retry_then_success(self) -> None:
        attempts: list[int] = []

        def task() -> str:
            attempts.append(1)
            if len(attempts) < 2:
                raise RuntimeError("fail")
            return "ok"

        rw = RetryWorker(max_retries=3, backoff_base=0)
        rw.submit("task-1", task)
        await rw.process_queue()
        if rw.get_queue_size() > 0:
            await rw.process_queue()
        assert len(attempts) == 2
        assert rw.get_metrics()["jobs_succeeded"] == 1

    @pytest.mark.asyncio
    async def test_fail_after_max_retries(self) -> None:
        dlq_entries: list[tuple] = []

        def dlq_cb(job, reason: str) -> None:
            dlq_entries.append((job.task_id, reason))

        def task() -> None:
            raise RuntimeError("always fails")

        rw = RetryWorker(max_retries=2, backoff_base=0, dlq_callback=dlq_cb)
        rw.submit("task-1", task)
        await rw.process_queue()
        if rw.get_queue_size() > 0:
            await rw.process_queue()
        assert rw.get_metrics()["jobs_failed"] == 1
        assert rw.get_metrics()["moved_to_dlq"] == 1
        assert len(dlq_entries) == 1

    @pytest.mark.asyncio
    async def test_async_task(self) -> None:
        rw = RetryWorker()

        async def task() -> int:
            return 42

        rw.submit("task-1", task)
        results = await rw.process_queue()
        assert results[0]["status"] == "success"


class TestBackoff:

    def test_backoff_zero_on_first(self) -> None:
        rw = RetryWorker(backoff_base=1)
        assert rw.get_backoff_seconds(0) == 0

    def test_backoff_exponential(self) -> None:
        rw = RetryWorker(backoff_base=1)
        assert rw.get_backoff_seconds(1) == 1
        assert rw.get_backoff_seconds(2) == 2
        assert rw.get_backoff_seconds(3) == 4

    def test_backoff_custom_base(self) -> None:
        rw = RetryWorker(backoff_base=2)
        assert rw.get_backoff_seconds(1) == 2
        assert rw.get_backoff_seconds(2) == 4
        assert rw.get_backoff_seconds(3) == 8


class TestQueueAndMetrics:

    def test_queue_size(self) -> None:
        rw = RetryWorker()
        rw.submit("t1", lambda: None)
        rw.submit("t2", lambda: None)
        assert rw.get_queue_size() == 2

    def test_max_retries(self) -> None:
        rw = RetryWorker(max_retries=5)
        assert rw.get_max_retries() == 5

    @pytest.mark.asyncio
    async def test_metrics_tracked(self) -> None:
        rw = RetryWorker()
        rw.submit("t1", lambda: "ok")
        await rw.process_queue()
        metrics = rw.get_metrics()
        assert metrics["jobs_submitted"] == 1
        assert metrics["jobs_succeeded"] == 1
