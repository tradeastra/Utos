"""
EventBus — lightweight in-memory pub/sub event bus.

For testing and worker orchestration. Production uses RedisEventBus.
All engines communicate via events, not direct calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class _Subscriber:
    id: str
    handler: Callable[[dict[str, Any]], Any]


class EventBus:
    """Lightweight in-memory event bus."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[_Subscriber]] = {}
        self._metrics: dict[str, int] = {
            "events_published": 0,
            "events_delivered": 0,
            "subscribers_added": 0,
            "subscribers_removed": 0,
        }

    async def publish(
        self,
        event_type: str,
        data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Publish an event to all subscribers."""
        event_id = str(uuid.uuid4())
        self._metrics["events_published"] += 1

        event_data = {
            "event_type": event_type,
            "event_id": event_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
            "metadata": metadata or {},
        }

        subscribers = list(self._subscribers.get(event_type, []))
        if not subscribers:
            logger.debug(f"No subscribers for {event_type}")
            return event_id

        for sub in subscribers:
            try:
                result = sub.handler(event_data)
                if isinstance(result, Coroutine):
                    await result
                self._metrics["events_delivered"] += 1
            except Exception as exc:
                logger.error(
                    f"Handler error for {event_type}: {exc}",
                    extra={"event_id": event_id, "subscriber_id": sub.id},
                )

        return event_id

    def subscribe(
        self, event_type: str, handler: Callable[[dict[str, Any]], Any]
    ) -> str:
        """Subscribe to an event type."""
        sub_id = str(uuid.uuid4())
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(_Subscriber(id=sub_id, handler=handler))
        self._metrics["subscribers_added"] += 1
        logger.debug(f"Subscribed to {event_type}", extra={"subscriber_id": sub_id})
        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe by subscription ID."""
        for event_type, subs in self._subscribers.items():
            for i, sub in enumerate(subs):
                if sub.id == subscription_id:
                    subs.pop(i)
                    self._metrics["subscribers_removed"] += 1
                    logger.debug(
                        f"Unsubscribed from {event_type}",
                        extra={"subscriber_id": subscription_id},
                    )
                    return True
        return False

    def get_subscribers(self, event_type: str) -> list[str]:
        """Return list of subscriber IDs for an event type."""
        return [sub.id for sub in self._subscribers.get(event_type, [])]

    def get_subscriber_count(self, event_type: str) -> int:
        return len(self._subscribers.get(event_type, []))

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)
