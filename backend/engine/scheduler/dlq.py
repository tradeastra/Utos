"""
DeadLetterQueue — stores failed events/tasks for analysis and replay.

Events that fail after max retries are moved here for manual review
or automated replay.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DeadLetterEntry:
    id: str
    event_type: str
    data: dict[str, Any]
    metadata: dict[str, Any]
    reason: str
    created_at: datetime
    replay_count: int = 0


class DeadLetterQueue:
    """In-memory dead letter queue for failed events."""

    def __init__(self, replay_handler: Callable[[DeadLetterEntry], bool] | None = None) -> None:
        self._entries: dict[str, DeadLetterEntry] = {}
        self._replay_handler = replay_handler
        self._metrics: dict[str, int] = {
            "entries_added": 0,
            "entries_replayed": 0,
            "entries_replay_succeeded": 0,
            "entries_replay_failed": 0,
            "entries_cleared": 0,
        }

    def add(
        self,
        event_type: str,
        data: dict[str, Any],
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        entry_id = str(uuid.uuid4())
        entry = DeadLetterEntry(
            id=entry_id,
            event_type=event_type,
            data=data,
            metadata=metadata or {},
            reason=reason,
            created_at=datetime.now(timezone.utc),
        )
        self._entries[entry_id] = entry
        self._metrics["entries_added"] += 1
        logger.warning(
            "Event moved to DLQ",
            extra={"entry_id": entry_id, "event_type": event_type, "reason": reason},
        )
        return entry_id

    def get_all(self) -> list[DeadLetterEntry]:
        return list(self._entries.values())

    def get_by_event_type(self, event_type: str) -> list[DeadLetterEntry]:
        return [e for e in self._entries.values() if e.event_type == event_type]

    def get_by_id(self, entry_id: str) -> DeadLetterEntry | None:
        return self._entries.get(entry_id)

    def replay(self, entry_id: str) -> bool:
        entry = self._entries.get(entry_id)
        if entry is None:
            return False

        entry.replay_count += 1
        self._metrics["entries_replayed"] += 1

        if self._replay_handler is not None:
            try:
                success = self._replay_handler(entry)
                if success:
                    del self._entries[entry_id]
                    self._metrics["entries_replay_succeeded"] += 1
                    logger.info(
                        "DLQ entry replay succeeded",
                        extra={"entry_id": entry_id, "event_type": entry.event_type},
                    )
                    return True
                else:
                    self._metrics["entries_replay_failed"] += 1
                    logger.warning(
                        "DLQ entry replay failed",
                        extra={"entry_id": entry_id, "event_type": entry.event_type},
                    )
                    return False
            except Exception as exc:
                self._metrics["entries_replay_failed"] += 1
                logger.error(
                    f"DLQ replay error: {exc}",
                    extra={"entry_id": entry_id},
                )
                return False

        logger.warning("No replay handler configured", extra={"entry_id": entry_id})
        return False

    def clear(self) -> None:
        count = len(self._entries)
        self._entries.clear()
        self._metrics["entries_cleared"] += count
        logger.info(f"DLQ cleared ({count} entries)")

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)
