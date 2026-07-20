"""
WorkerManager — manages worker lifecycle: start, stop, pause, resume, error tracking.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WorkerStatus:
    name: str
    state: str = "idle"  # idle | running | paused | stopped | error
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    error_count: int = 0
    last_error: str | None = None


class WorkerManager:
    """Manages worker lifecycle without executing coroutines directly."""

    def __init__(self) -> None:
        self._workers: dict[str, WorkerStatus] = {}
        self._coroutines: dict[str, Callable[..., Any]] = {}
        self._metrics: dict[str, int] = {
            "workers_started": 0,
            "workers_stopped": 0,
            "workers_paused": 0,
            "workers_resumed": 0,
            "workers_errored": 0,
        }

    def register_worker(self, name: str, coroutine: Callable[..., Any]) -> None:
        self._coroutines[name] = coroutine
        self._workers[name] = WorkerStatus(name=name)

    def start_worker(self, name: str) -> bool:
        if name not in self._workers:
            logger.error(f"Worker not registered: {name}")
            return False
        worker = self._workers[name]
        if worker.state == "running":
            return True
        worker.state = "running"
        worker.started_at = datetime.now(UTC)
        worker.stopped_at = None
        worker.error_count = 0
        worker.last_error = None
        self._metrics["workers_started"] += 1
        logger.info(f"Worker started: {name}")
        return True

    def stop_worker(self, name: str) -> bool:
        if name not in self._workers:
            return False
        worker = self._workers[name]
        if worker.state == "stopped":
            return True
        worker.state = "stopped"
        worker.stopped_at = datetime.now(UTC)
        self._metrics["workers_stopped"] += 1
        logger.info(f"Worker stopped: {name}")
        return True

    def pause_worker(self, name: str) -> bool:
        if name not in self._workers:
            return False
        worker = self._workers[name]
        if worker.state not in ("running",):
            return False
        worker.state = "paused"
        self._metrics["workers_paused"] += 1
        logger.info(f"Worker paused: {name}")
        return True

    def resume_worker(self, name: str) -> bool:
        if name not in self._workers:
            return False
        worker = self._workers[name]
        if worker.state != "paused":
            return False
        worker.state = "running"
        self._metrics["workers_resumed"] += 1
        logger.info(f"Worker resumed: {name}")
        return True

    def mark_error(self, name: str, error: str) -> None:
        if name not in self._workers:
            return
        worker = self._workers[name]
        worker.state = "error"
        worker.error_count += 1
        worker.last_error = error
        self._metrics["workers_errored"] += 1
        logger.error(f"Worker error: {name} — {error}")

    def get_worker_status(self, name: str) -> WorkerStatus | None:
        return self._workers.get(name)

    def get_all_workers(self) -> list[WorkerStatus]:
        return list(self._workers.values())

    def get_running_workers(self) -> list[WorkerStatus]:
        return [w for w in self._workers.values() if w.state == "running"]

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)
