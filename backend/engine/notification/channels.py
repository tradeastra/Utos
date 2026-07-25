"""
Notification channels — Email, Telegram, Discord, Webhook.

Each channel is independent. Channels use callback-based sending
(no direct SMTP/HTTP) for testability.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from core.logging import get_logger

logger = get_logger(__name__)


class NotificationChannel(ABC):
    """Abstract base for notification channels."""

    def __init__(self, send_fn: Callable[..., Any] | None = None) -> None:
        self._send_fn = send_fn
        self._metrics: dict[str, int] = {
            "sent": 0,
            "failed": 0,
        }

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Return the channel name (e.g., 'email', 'telegram')."""
        ...

    @abstractmethod
    async def send(
        self,
        recipient: str,
        title: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Send a notification via this channel."""
        ...

    def get_metrics(self) -> dict[str, int]:
        return dict(self._metrics)


class EmailChannel(NotificationChannel):
    """Email notification channel."""

    @property
    def channel_name(self) -> str:
        return "email"

    async def send(
        self,
        recipient: str,
        title: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        if self._send_fn is None:
            logger.info(
                "Email sent (stub)",
                extra={"recipient": recipient, "title": title},
            )
            self._metrics["sent"] += 1
            return True

        try:
            result = self._send_fn(recipient, title, message, data or {})
            self._metrics["sent"] += 1
            return bool(result)
        except Exception as exc:
            self._metrics["failed"] += 1
            logger.error(f"Email send failed: {exc}", extra={"recipient": recipient})
            return False


class TelegramChannel(NotificationChannel):
    """Telegram notification channel — sends messages via Telegram Bot API."""

    @property
    def channel_name(self) -> str:
        return "telegram"

    async def send(
        self,
        recipient: str,
        title: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        if self._send_fn is not None:
            try:
                result = self._send_fn(recipient, title, message, data or {})
                self._metrics["sent"] += 1
                return bool(result)
            except Exception as exc:
                self._metrics["failed"] += 1
                logger.error(f"Telegram send failed: {exc}", extra={"recipient": recipient})
                return False

        # Real Telegram Bot API implementation
        try:
            import httpx
            from core.config import settings

            bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
            if not bot_token:
                logger.warning("Telegram bot token not configured — skipping send")
                self._metrics["failed"] += 1
                return False

            # recipient is the chat_id
            chat_id = recipient
            text = f"*{title}*\n\n{message}"

            payload: dict[str, Any] = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }
            if data and "reply_markup" in data:
                payload["reply_markup"] = data["reply_markup"]

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json=payload,
                )
                resp.raise_for_status()
                result = resp.json()
                if result.get("ok"):
                    self._metrics["sent"] += 1
                    return True
                else:
                    self._metrics["failed"] += 1
                    logger.error(f"Telegram API error: {result.get('description')}")
                    return False

        except Exception as exc:
            self._metrics["failed"] += 1
            logger.error(f"Telegram send failed: {exc}", extra={"recipient": recipient})
            return False


class DiscordChannel(NotificationChannel):
    """Discord notification channel."""

    @property
    def channel_name(self) -> str:
        return "discord"

    async def send(
        self,
        recipient: str,
        title: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        if self._send_fn is None:
            logger.info(
                "Discord sent (stub)",
                extra={"recipient": recipient, "title": title},
            )
            self._metrics["sent"] += 1
            return True

        try:
            result = self._send_fn(recipient, title, message, data or {})
            self._metrics["sent"] += 1
            return bool(result)
        except Exception as exc:
            self._metrics["failed"] += 1
            logger.error(f"Discord send failed: {exc}", extra={"recipient": recipient})
            return False


class WebhookChannel(NotificationChannel):
    """Webhook notification channel."""

    @property
    def channel_name(self) -> str:
        return "webhook"

    async def send(
        self,
        recipient: str,
        title: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        if self._send_fn is None:
            logger.info(
                "Webhook sent (stub)",
                extra={"recipient": recipient, "title": title},
            )
            self._metrics["sent"] += 1
            return True

        try:
            result = self._send_fn(recipient, title, message, data or {})
            self._metrics["sent"] += 1
            return bool(result)
        except Exception as exc:
            self._metrics["failed"] += 1
            logger.error(f"Webhook send failed: {exc}", extra={"recipient": recipient})
            return False
