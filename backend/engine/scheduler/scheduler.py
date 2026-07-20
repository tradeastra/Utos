"""
JobScheduler — schedules periodic background tasks.

Tasks: cleanup, checkpoint, heartbeat, sync, retry.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ScheduledTask:
    id: str
    name: str
    task_type: str  # cleanup | checkpoint | heartbeat | sync | retry
    interval_seconds: int
    coroutine: Callable[..., Any] | None = None
    last_run: datetime | None = None
    next_run: datetime | None = None
    enabled: bool = True
    run_count: int = 0
    failure_count: int = 0


class JobScheduler:
    """Schedules and tracks periodic background tasks."""

    def __init__(self) -> None:
        self._tasks: dict[str, ScheduledTask] = {}
        self._metrics: dict[str, int] = {
            "tasks_added": 0,
            "tasks_removed": 0,
            "tasks_executed": 0,
            "tasks_failed": 0,
        }

    def add_task(
        self,
        name: str,
        task_type: str,
        interval_seconds: int,
        coroutine: Callable[..., Any] | None = None,
        enabled: bool = True,
    ) -> str:
        task_id = str(uuid.uuid4())
        now = datetime.now(UTC)
        task = ScheduledTask(
            id=task_id,
            name=name,
            task_type=task_type,
            interval_seconds=interval_seconds,
            coroutine=coroutine,
            last_run=None,
            next_run=now + timedelta(seconds=interval_seconds),
            enabled=enabled,
        )
        self._tasks[task_id] = task
        self._metrics["tasks_added"] += 1
        logger.info(
            "Task scheduled",
            extra={"task_id": task_id, "task_name": name, "interval": interval_seconds},
        )
        return task_id

    def remove_task(self, task_id: str) -> bool:
        if task_id not in self._tasks:
            return False
        del self._tasks[task_id]
        self._metrics["tasks_removed"] += 1
        logger.info("Task removed", extra={"task_id": task_id})
        return True

    def enable_task(self, task_id: str) -> bool:
        if task_id not in self._tasks:
            return False
        self._tasks[task_id].enabled = True
        return True

    def disable_task(self, task_id: str) -> bool:
        if task_id not in self._tasks:
            return False
        self._tasks[task_id].enabled = False
        return True

    async def run_task(self, task_id: str) -> dict[str, Any] | None:
        task = self._tasks.get(task_id)
        if not task or not task.enabled or task.coroutine is None:
            return None

        now = datetime.now(UTC)
        task.last_run = now
        task.next_run = now + timedelta(seconds=task.interval_seconds)

        try:
            result = (
                await task.coroutine()
                if self._is_async(task.coroutine)
                else task.coroutine()
            )
            task.run_count += 1
            self._metrics["tasks_executed"] += 1
            logger.info(
                "Task executed",
                extra={
                    "task_id": task_id,
                    "task_name": task.name,
                    "type": task.task_type,
                },
            )
            return {"task_id": task_id, "status": "success", "result": result}
        except Exception as exc:
            task.failure_count += 1
            self._metrics["tasks_failed"] += 1
            logger.error(
                f"Task failed: {exc}",
                extra={"task_id": task_id, "task_name": task.name},
            )
            return {"task_id": task_id, "status": "failed", "error": str(exc)}

    async def run_all(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for task_id in list(self._tasks.keys()):
            result = await self.run_task(task_id)
            if result is not None:
                results.append(result)
        return results

    def get_pending_tasks(self, now: datetime | None = None) -> list[ScheduledTask]:
        if now is None:
            now = datetime.now(UTC)
        return [
            t
            for t in self._tasks.values()
            if t.enabled and (t.next_run is None or t.next_run <= now)
        ]

    def get_task_count(self) -> int:
        return len(self._tasks)

    def get_tasks_by_type(self, task_type: str) -> list[ScheduledTask]:
        return [t for t in self._tasks.values() if t.task_type == task_type]

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)

    @staticmethod
    def _is_async(func: Callable[..., Any]) -> bool:
        import asyncio

        return asyncio.iscoroutinefunction(func)
