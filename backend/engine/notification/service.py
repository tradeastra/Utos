"""
NotificationService — orchestrates channels, templates, and queue.

Flow: notify() → template render → enqueue → queue process → channel send
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from core.exceptions import NotificationError
from core.logging import get_logger
from engine.notification.channels import NotificationChannel
from engine.notification.queue import NotificationQueue, QueuedNotification
from engine.notification.template import NotificationMessage, TemplateEngine

logger = get_logger(__name__)


class NotificationService:
    """Orchestrates notification channels, templates, and queue."""

    def __init__(
        self,
        template_engine: TemplateEngine | None = None,
        queue: NotificationQueue | None = None,
    ) -> None:
        self._templates = template_engine or TemplateEngine()
        self._channels: dict[str, NotificationChannel] = {}
        self._queue = queue or NotificationQueue(send_fn=self._dispatch)
        self._recipient_resolver: dict[str, str] = {}
        self._metrics: dict[str, int] = {
            "notifications_requested": 0,
            "notifications_sent": 0,
            "notifications_failed": 0,
        }

    def register_channel(self, channel: NotificationChannel) -> None:
        self._channels[channel.channel_name] = channel
        logger.info(f"Channel registered: {channel.channel_name}")

    def register_template(self, template_name: str, title: str, message: str) -> None:
        from engine.notification.template import NotificationTemplate
        self._templates.register_template(NotificationTemplate(
            name=template_name,
            title_template=title,
            message_template=message,
        ))

    def set_recipient(self, user_id: str, channel: str, recipient: str) -> None:
        self._recipient_resolver[f"{user_id}:{channel}"] = recipient

    def get_recipient(self, user_id: str, channel: str) -> str:
        return self._recipient_resolver.get(f"{user_id}:{channel}", user_id)

    async def notify(
        self,
        user_id: str,
        template_name: str,
        channel: str,
        context: dict[str, Any],
    ) -> str:
        self._metrics["notifications_requested"] += 1

        if channel not in self._channels:
            raise NotificationError(f"Channel not registered: {channel}")

        rendered = self._templates.render(template_name, context, channel=channel)
        recipient = self.get_recipient(user_id, channel)

        notification_id = self._queue.create_and_enqueue(
            user_id=user_id,
            channel=channel,
            recipient=recipient,
            title=rendered.title,
            message=rendered.message,
            data=context,
        )
        return notification_id

    async def notify_multi(
        self,
        user_id: str,
        template_name: str,
        channels: list[str],
        context: dict[str, Any],
    ) -> list[str]:
        ids: list[str] = []
        for channel in channels:
            try:
                notification_id = await self.notify(user_id, template_name, channel, context)
                ids.append(notification_id)
            except NotificationError as exc:
                logger.error(f"Failed to notify via {channel}: {exc}")
        return ids

    async def process_queue(self) -> list[dict[str, Any]]:
        results = await self._queue.process()
        for result in results:
            if result.status == "success":
                self._metrics["notifications_sent"] += 1
            elif result.status == "failed":
                self._metrics["notifications_failed"] += 1
        return [
            {
                "notification_id": r.notification_id,
                "channel": r.channel,
                "status": r.status,
                "error": r.error,
            }
            for r in results
        ]

    async def _dispatch(self, notification: QueuedNotification) -> bool:
        channel = self._channels.get(notification.channel)
        if channel is None:
            logger.error(f"Channel not found: {notification.channel}")
            return False

        return await channel.send(
            recipient=notification.recipient,
            title=notification.title,
            message=notification.message,
            data=notification.data,
        )

    def get_pending_count(self) -> int:
        return self._queue.get_pending_count()

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)

    def get_queue_metrics(self) -> dict[str, int]:
        return self._queue.get_metrics()
