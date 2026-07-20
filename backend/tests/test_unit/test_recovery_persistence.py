"""
Unit tests for RecoveryPersistence.
"""

from datetime import UTC, datetime

import pytest
from core.exceptions import CheckpointError
from engine.recovery.persistence import RecoveryCheckpoint, RecoveryPersistence


class TestSaveLoadCheckpoint:

    def test_save_and_load(self) -> None:
        persistence = RecoveryPersistence()
        checkpoint = RecoveryCheckpoint(
            instance_id="inst-1",
            created_at=datetime.now(UTC),
            phase="connection",
            data={"redis_ok": True},
        )
        persistence.save_checkpoint("inst-1", checkpoint)
        loaded = persistence.load_checkpoint("inst-1")
        assert loaded is not None
        assert loaded.instance_id == "inst-1"
        assert loaded.phase == "connection"
        assert loaded.data == {"redis_ok": True}

    def test_load_nonexistent(self) -> None:
        persistence = RecoveryPersistence()
        result = persistence.load_checkpoint("nonexistent")
        assert result is None

    def test_save_mismatched_instance_id(self) -> None:
        persistence = RecoveryPersistence()
        checkpoint = RecoveryCheckpoint(
            instance_id="inst-1",
            created_at=datetime.now(UTC),
            phase="connection",
            data={},
        )
        with pytest.raises(CheckpointError, match="does not match"):
            persistence.save_checkpoint("inst-2", checkpoint)


class TestClearCheckpoint:

    def test_clear_existing(self) -> None:
        persistence = RecoveryPersistence()
        checkpoint = RecoveryCheckpoint(
            instance_id="inst-1",
            created_at=datetime.now(UTC),
            phase="state",
            data={},
        )
        persistence.save_checkpoint("inst-1", checkpoint)
        assert persistence.has_checkpoint("inst-1") is True
        persistence.clear_checkpoint("inst-1")
        assert persistence.has_checkpoint("inst-1") is False

    def test_clear_nonexistent(self) -> None:
        persistence = RecoveryPersistence()
        persistence.clear_checkpoint("nonexistent")


class TestListCheckpoints:

    def test_list_empty(self) -> None:
        persistence = RecoveryPersistence()
        assert persistence.list_checkpoints() == []

    def test_list_multiple(self) -> None:
        persistence = RecoveryPersistence()
        for iid in ["inst-1", "inst-2", "inst-3"]:
            persistence.save_checkpoint(
                iid,
                RecoveryCheckpoint(
                    instance_id=iid,
                    created_at=datetime.now(UTC),
                    phase="connection",
                    data={},
                ),
            )
        result = persistence.list_checkpoints()
        assert set(result) == {"inst-1", "inst-2", "inst-3"}


class TestSerializeDeserialize:

    def test_roundtrip(self) -> None:
        checkpoint = RecoveryCheckpoint(
            instance_id="inst-1",
            created_at=datetime.now(UTC),
            phase="reconciliation",
            data={"results": [{"component": "grid", "action": "restored"}]},
        )
        json_str = RecoveryPersistence.serialize_checkpoint(checkpoint)
        restored = RecoveryPersistence.deserialize_checkpoint(json_str)
        assert restored.instance_id == checkpoint.instance_id
        assert restored.phase == checkpoint.phase
        assert restored.data == checkpoint.data


class TestMetrics:

    def test_metrics_tracked(self) -> None:
        persistence = RecoveryPersistence()
        checkpoint = RecoveryCheckpoint(
            instance_id="inst-1",
            created_at=datetime.now(UTC),
            phase="connection",
            data={},
        )
        persistence.save_checkpoint("inst-1", checkpoint)
        persistence.load_checkpoint("inst-1")
        persistence.clear_checkpoint("inst-1")
        metrics = persistence.get_metrics()
        assert metrics["checkpoints_saved"] == 1
        assert metrics["checkpoints_loaded"] == 1
        assert metrics["checkpoints_cleared"] == 1
