"""
RecoveryPersistence — checkpoints recovery state for auditability.

Saves and loads recovery checkpoints so that recovery can resume
from the last successful phase if interrupted.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.exceptions import CheckpointError
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RecoveryCheckpoint:
    """A recovery checkpoint for resuming interrupted recovery."""

    instance_id: str
    created_at: datetime
    phase: str  # "connection" | "state" | "reconciliation"
    data: dict[str, Any] = field(default_factory=dict)


class RecoveryPersistence:
    """In-memory checkpoint store for recovery state.

    In production, this would persist to Redis or PostgreSQL.
    For now, in-memory is sufficient for testing and validation.
    """

    def __init__(self) -> None:
        self._checkpoints: dict[str, RecoveryCheckpoint] = {}
        self._metrics: dict[str, int] = {
            "checkpoints_saved": 0,
            "checkpoints_loaded": 0,
            "checkpoints_cleared": 0,
        }

    def save_checkpoint(self, instance_id: str, checkpoint: RecoveryCheckpoint) -> None:
        """Save a recovery checkpoint."""
        if checkpoint.instance_id != instance_id:
            raise CheckpointError(
                f"Checkpoint instance_id {checkpoint.instance_id} does not match {instance_id}"
            )
        self._checkpoints[instance_id] = checkpoint
        self._metrics["checkpoints_saved"] += 1
        logger.info(
            "Checkpoint saved",
            extra={"instance_id": instance_id, "phase": checkpoint.phase},
        )

    def load_checkpoint(self, instance_id: str) -> RecoveryCheckpoint | None:
        """Load a recovery checkpoint."""
        checkpoint = self._checkpoints.get(instance_id)
        if checkpoint is None:
            return None
        self._metrics["checkpoints_loaded"] += 1
        logger.info(
            "Checkpoint loaded",
            extra={"instance_id": instance_id, "phase": checkpoint.phase},
        )
        return checkpoint

    def clear_checkpoint(self, instance_id: str) -> None:
        """Clear a recovery checkpoint after successful recovery."""
        if instance_id in self._checkpoints:
            del self._checkpoints[instance_id]
            self._metrics["checkpoints_cleared"] += 1
            logger.info("Checkpoint cleared", extra={"instance_id": instance_id})

    def list_checkpoints(self) -> list[str]:
        """List all instance IDs with active checkpoints."""
        return list(self._checkpoints.keys())

    def has_checkpoint(self, instance_id: str) -> bool:
        return instance_id in self._checkpoints

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)

    @staticmethod
    def serialize_checkpoint(checkpoint: RecoveryCheckpoint) -> str:
        """Serialize checkpoint to JSON string."""
        data = asdict(checkpoint)
        data["created_at"] = checkpoint.created_at.isoformat()
        return json.dumps(data)

    @staticmethod
    def deserialize_checkpoint(json_str: str) -> RecoveryCheckpoint:
        """Deserialize checkpoint from JSON string."""
        data = json.loads(json_str)
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return RecoveryCheckpoint(**data)
