"""Notification package: channels, templates, queue, service, automation."""

from engine.notification.automation import (
    AutomationAction,
    AutomationRule,
    AutomationRules,
)
from engine.notification.channels import (
    DiscordChannel,
    EmailChannel,
    NotificationChannel,
    TelegramChannel,
    WebhookChannel,
)
from engine.notification.queue import (
    NotificationQueue,
    NotificationResult,
    QueuedNotification,
)
from engine.notification.service import NotificationService
from engine.notification.template import (
    NotificationMessage,
    NotificationTemplate,
    TemplateEngine,
)

__all__ = [
    "NotificationChannel",
    "EmailChannel",
    "TelegramChannel",
    "DiscordChannel",
    "WebhookChannel",
    "NotificationTemplate",
    "NotificationMessage",
    "TemplateEngine",
    "NotificationQueue",
    "QueuedNotification",
    "NotificationResult",
    "NotificationService",
    "AutomationRule",
    "AutomationAction",
    "AutomationRules",
]
