"""
RetryWorker — retries failed jobs with exponential backoff.

After max_retries, moves to DeadLetterQueue.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class _RetryJob:
    task_id: str
    coroutine: Callable[..., Any]
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_error: str | None = None


class RetryWorker:
    """Retries failed tasks with exponential backoff."""

    def __init__(
        self,
        max_retries: int = 3,
        backoff_base: int = 1,
        dlq_callback: Callable[[_RetryJob, str], Any] | None = None,
    ) -> None:
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._dlq_callback = dlq_callback
        self._queue: list[_RetryJob] = []
        self._metrics: dict[str, int] = {
            "jobs_submitted": 0,
            "jobs_succeeded": 0,
            "jobs_retried": 0,
            "jobs_failed": 0,
            "moved_to_dlq": 0,
        }

    def submit(self, task_id: str, coroutine: Callable[..., Any]) -> str:
        job = _RetryJob(
            task_id=task_id,
            coroutine=coroutine,
            max_retries=self._max_retries,
        )
        self._queue.append(job)
        self._metrics["jobs_submitted"] += 1
        logger.info("Job submitted for retry", extra={"task_id": task_id})
        return task_id

    async def process_queue(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        queue = list(self._queue)
        self._queue.clear()

        for job in queue:
            result = await self._process_job(job)
            results.append(result)

        return results

    async def _process_job(self, job: _RetryJob) -> dict[str, Any]:
        backoff = self.get_backoff_seconds(job.retry_count)
        if backoff > 0 and job.retry_count > 0:
            await asyncio.sleep(backoff)

        try:
            if self._is_async(job.coroutine):
                await job.coroutine()
            else:
                job.coroutine()

            self._metrics["jobs_succeeded"] += 1
            logger.info(
                "Job succeeded",
                extra={"task_id": job.task_id, "attempt": job.retry_count + 1},
            )
            return {
                "task_id": job.task_id,
                "status": "success",
                "attempts": job.retry_count + 1,
            }

        except Exception as exc:
            job.last_error = str(exc)
            job.retry_count += 1

            if job.retry_count < job.max_retries:
                self._queue.append(job)
                self._metrics["jobs_retried"] += 1
                logger.warning(
                    f"Job failed, will retry: {exc}",
                    extra={"task_id": job.task_id, "attempt": job.retry_count},
                )
                return {
                    "task_id": job.task_id,
                    "status": "retry",
                    "attempts": job.retry_count,
                    "error": str(exc),
                }
            else:
                self._metrics["jobs_failed"] += 1
                self._metrics["moved_to_dlq"] += 1
                logger.error(
                    f"Job failed after {job.max_retries} retries: {exc}",
                    extra={"task_id": job.task_id},
                )
                if self._dlq_callback is not None:
                    try:
                        self._dlq_callback(job, str(exc))
                    except Exception as dlq_exc:
                        logger.error(f"DLQ callback error: {dlq_exc}")
                return {
                    "task_id": job.task_id,
                    "status": "failed",
                    "attempts": job.retry_count,
                    "error": str(exc),
                }

    def get_queue_size(self) -> int:
        return len(self._queue)

    def get_max_retries(self) -> int:
        return self._max_retries

    def get_backoff_seconds(self, retry_count: int) -> int:
        if retry_count <= 0:
            return 0
        return self._backoff_base * (2 ** (retry_count - 1))

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)

    @staticmethod
    def _is_async(func: Callable[..., Any]) -> bool:
        import asyncio

        return asyncio.iscoroutinefunction(func)
