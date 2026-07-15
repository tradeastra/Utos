"""Unit tests for WorkerManager."""

import pytest

from engine.scheduler.manager import WorkerManager, WorkerStatus


class TestWorkerLifecycle:

    def test_register_and_start(self) -> None:
        wm = WorkerManager()
        wm.register_worker("grid-worker", lambda: None)
        assert wm.start_worker("grid-worker") is True
        status = wm.get_worker_status("grid-worker")
        assert status is not None
        assert status.state == "running"
        assert status.started_at is not None

    def test_start_unregistered(self) -> None:
        wm = WorkerManager()
        assert wm.start_worker("unknown") is False

    def test_start_already_running(self) -> None:
        wm = WorkerManager()
        wm.register_worker("w1", lambda: None)
        wm.start_worker("w1")
        assert wm.start_worker("w1") is True

    def test_stop_worker(self) -> None:
        wm = WorkerManager()
        wm.register_worker("w1", lambda: None)
        wm.start_worker("w1")
        assert wm.stop_worker("w1") is True
        status = wm.get_worker_status("w1")
        assert status.state == "stopped"
        assert status.stopped_at is not None

    def test_stop_unregistered(self) -> None:
        wm = WorkerManager()
        assert wm.stop_worker("unknown") is False

    def test_pause_and_resume(self) -> None:
        wm = WorkerManager()
        wm.register_worker("w1", lambda: None)
        wm.start_worker("w1")
        assert wm.pause_worker("w1") is True
        assert wm.get_worker_status("w1").state == "paused"
        assert wm.resume_worker("w1") is True
        assert wm.get_worker_status("w1").state == "running"

    def test_pause_not_running(self) -> None:
        wm = WorkerManager()
        wm.register_worker("w1", lambda: None)
        assert wm.pause_worker("w1") is False

    def test_resume_not_paused(self) -> None:
        wm = WorkerManager()
        wm.register_worker("w1", lambda: None)
        wm.start_worker("w1")
        assert wm.resume_worker("w1") is False


class TestErrorTracking:

    def test_mark_error(self) -> None:
        wm = WorkerManager()
        wm.register_worker("w1", lambda: None)
        wm.start_worker("w1")
        wm.mark_error("w1", "Connection lost")
        status = wm.get_worker_status("w1")
        assert status.state == "error"
        assert status.error_count == 1
        assert status.last_error == "Connection lost"


class TestQueries:

    def test_get_all_workers(self) -> None:
        wm = WorkerManager()
        wm.register_worker("w1", lambda: None)
        wm.register_worker("w2", lambda: None)
        all_workers = wm.get_all_workers()
        assert len(all_workers) == 2

    def test_get_running_workers(self) -> None:
        wm = WorkerManager()
        wm.register_worker("w1", lambda: None)
        wm.register_worker("w2", lambda: None)
        wm.start_worker("w1")
        running = wm.get_running_workers()
        assert len(running) == 1
        assert running[0].name == "w1"

    def test_metrics(self) -> None:
        wm = WorkerManager()
        wm.register_worker("w1", lambda: None)
        wm.start_worker("w1")
        wm.stop_worker("w1")
        metrics = wm.get_metrics()
        assert metrics["workers_started"] == 1
        assert metrics["workers_stopped"] == 1
