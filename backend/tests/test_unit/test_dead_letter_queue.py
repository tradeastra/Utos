"""Unit tests for DeadLetterQueue."""

import pytest

from engine.scheduler.dlq import DeadLetterEntry, DeadLetterQueue


class TestAddAndGet:

    def test_add_entry(self) -> None:
        dlq = DeadLetterQueue()
        entry_id = dlq.add("ORDER_FILLED", {"order_id": "123"}, "Handler error")
        assert isinstance(entry_id, str)
        assert dlq.get_metrics()["entries_added"] == 1

    def test_get_all(self) -> None:
        dlq = DeadLetterQueue()
        dlq.add("ORDER_FILLED", {"v": 1}, "err1")
        dlq.add("PRICE_UPDATE", {"v": 2}, "err2")
        all_entries = dlq.get_all()
        assert len(all_entries) == 2

    def test_get_by_event_type(self) -> None:
        dlq = DeadLetterQueue()
        dlq.add("ORDER_FILLED", {"v": 1}, "err1")
        dlq.add("PRICE_UPDATE", {"v": 2}, "err2")
        dlq.add("ORDER_FILLED", {"v": 3}, "err3")
        results = dlq.get_by_event_type("ORDER_FILLED")
        assert len(results) == 2

    def test_get_by_id(self) -> None:
        dlq = DeadLetterQueue()
        entry_id = dlq.add("TEST", {"v": 1}, "err")
        entry = dlq.get_by_id(entry_id)
        assert entry is not None
        assert entry.event_type == "TEST"
        assert entry.reason == "err"


class TestReplay:

    def test_replay_success(self) -> None:
        replayed: list[DeadLetterEntry] = []

        def handler(entry: DeadLetterEntry) -> bool:
            replayed.append(entry)
            return True

        dlq = DeadLetterQueue(replay_handler=handler)
        entry_id = dlq.add("ORDER_FILLED", {"v": 1}, "err")
        result = dlq.replay(entry_id)
        assert result is True
        assert len(replayed) == 1
        assert dlq.get_by_id(entry_id) is None
        assert dlq.get_metrics()["entries_replay_succeeded"] == 1

    def test_replay_failure(self) -> None:
        def handler(entry: DeadLetterEntry) -> bool:
            return False

        dlq = DeadLetterQueue(replay_handler=handler)
        entry_id = dlq.add("TEST", {"v": 1}, "err")
        result = dlq.replay(entry_id)
        assert result is False
        assert dlq.get_by_id(entry_id) is not None
        assert dlq.get_metrics()["entries_replay_failed"] == 1

    def test_replay_no_handler(self) -> None:
        dlq = DeadLetterQueue()
        entry_id = dlq.add("TEST", {"v": 1}, "err")
        result = dlq.replay(entry_id)
        assert result is False

    def test_replay_nonexistent(self) -> None:
        dlq = DeadLetterQueue(replay_handler=lambda e: True)
        assert dlq.replay("fake-id") is False

    def test_replay_handler_exception(self) -> None:
        def boom(entry: DeadLetterEntry) -> bool:
            raise RuntimeError("replay error")

        dlq = DeadLetterQueue(replay_handler=boom)
        entry_id = dlq.add("TEST", {"v": 1}, "err")
        result = dlq.replay(entry_id)
        assert result is False
        assert dlq.get_metrics()["entries_replay_failed"] == 1


class TestClear:

    def test_clear(self) -> None:
        dlq = DeadLetterQueue()
        dlq.add("A", {"v": 1}, "err")
        dlq.add("B", {"v": 2}, "err")
        dlq.clear()
        assert len(dlq.get_all()) == 0
        assert dlq.get_metrics()["entries_cleared"] == 2
