"""
NotificationQueue — async queue with worker pattern.

Processes notifications sequentially. Failed notifications are retried
(max 3) then moved to a dead letter callback.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class QueuedNotification:
    id: str
    user_id: str
    channel: str
    recipient: str
    title: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class NotificationResult:
    notification_id: str
    channel: str
    status: str  # success | failed | retry
    error: str | None = None
    sent_at: datetime | None = None


class NotificationQueue:
    """In-memory notification queue with retry support."""

    def __init__(
        self,
        send_fn: Callable[..., Any] | None = None,
        max_retries: int = 3,
        dlq_callback: Callable[[QueuedNotification, str], Any] | None = None,
    ) -> None:
        self._send_fn = send_fn
        self._max_retries = max_retries
        self._dlq_callback = dlq_callback
        self._queue: list[QueuedNotification] = []
        self._metrics: dict[str, int] = {
            "enqueued": 0,
            "sent": 0,
            "retried": 0,
            "failed": 0,
            "moved_to_dlq": 0,
        }

    def enqueue(self, notification: QueuedNotification) -> str:
        self._queue.append(notification)
        self._metrics["enqueued"] += 1
        logger.info(
            "Notification enqueued",
            extra={"notification_id": notification.id, "channel": notification.channel},
        )
        return notification.id

    def create_and_enqueue(
        self,
        user_id: str,
        channel: str,
        recipient: str,
        title: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> str:
        notification = QueuedNotification(
            id=str(uuid.uuid4()),
            user_id=user_id,
            channel=channel,
            recipient=recipient,
            title=title,
            message=message,
            data=data or {},
            max_retries=self._max_retries,
        )
        return self.enqueue(notification)

    async def process(self) -> list[NotificationResult]:
        results: list[NotificationResult] = []
        queue = list(self._queue)
        self._queue.clear()

        for notification in queue:
            result = await self._process_one(notification)
            results.append(result)

        return results

    async def _process_one(self, notification: QueuedNotification) -> NotificationResult:
        if self._send_fn is None:
            logger.warning("No send function configured", extra={"notification_id": notification.id})
            return NotificationResult(
                notification_id=notification.id,
                channel=notification.channel,
                status="failed",
                error="No send function configured",
            )

        try:
            if self._is_async(self._send_fn):
                success = await self._send_fn(notification)
            else:
                success = self._send_fn(notification)

            if success:
                self._metrics["sent"] += 1
                return NotificationResult(
                    notification_id=notification.id,
                    channel=notification.channel,
                    status="success",
                    sent_at=datetime.now(timezone.utc),
                )

            raise RuntimeError("Send returned False")

        except Exception as exc:
            notification.retry_count += 1
            error_msg = str(exc)

            if notification.retry_count < notification.max_retries:
                self._queue.append(notification)
                self._metrics["retried"] += 1
                logger.warning(
                    f"Notification failed, will retry: {error_msg}",
                    extra={"notification_id": notification.id, "attempt": notification.retry_count},
                )
                return NotificationResult(
                    notification_id=notification.id,
                    channel=notification.channel,
                    status="retry",
                    error=error_msg,
                )

            self._metrics["failed"] += 1
            self._metrics["moved_to_dlq"] += 1
            logger.error(
                f"Notification failed after {notification.max_retries} retries: {error_msg}",
                extra={"notification_id": notification.id},
            )
            if self._dlq_callback is not None:
                try:
                    self._dlq_callback(notification, error_msg)
                except Exception as dlq_exc:
                    logger.error(f"DLQ callback error: {dlq_exc}")

            return NotificationResult(
                notification_id=notification.id,
                channel=notification.channel,
                status="failed",
                error=error_msg,
            )

    def get_pending_count(self) -> int:
        return len(self._queue)

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)

    @staticmethod
    def _is_async(func: Callable[..., Any]) -> bool:
        import asyncio
        return asyncio.iscoroutinefunction(func)
