"""
TemplateEngine — render notification messages from templates.

Templates use {variable} placeholders. Channel-specific formatting supported.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.exceptions import NotificationError
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class NotificationTemplate:
    name: str
    title_template: str
    message_template: str
    channel_format: dict[str, str] = field(default_factory=dict)


@dataclass
class NotificationMessage:
    title: str
    message: str
    channel: str


class TemplateEngine:
    """Renders notification messages from registered templates."""

    def __init__(self) -> None:
        self._templates: dict[str, NotificationTemplate] = {}
        self._register_defaults()

    def register_template(self, template: NotificationTemplate) -> None:
        self._templates[template.name] = template
        logger.info(f"Template registered: {template.name}")

    def render(
        self,
        template_name: str,
        context: dict[str, Any],
        channel: str = "default",
    ) -> NotificationMessage:
        template = self._templates.get(template_name)
        if template is None:
            raise NotificationError(f"Template not found: {template_name}")

        title = self._safe_format(template.title_template, context)
        message = self._safe_format(template.message_template, context)

        if channel in template.channel_format:
            message = self._safe_format(template.channel_format[channel], context)

        return NotificationMessage(title=title, message=message, channel=channel)

    def list_templates(self) -> list[str]:
        return list(self._templates.keys())

    def get_template(self, name: str) -> NotificationTemplate | None:
        return self._templates.get(name)

    def _safe_format(self, template_str: str, context: dict[str, Any]) -> str:
        try:
            return template_str.format(**context)
        except KeyError as exc:
            raise NotificationError(
                f"Missing template variable: {exc}",
                details={"template": template_str, "missing": str(exc)},
            )

    def _register_defaults(self) -> None:
        defaults = [
            NotificationTemplate(
                name="order_filled",
                title_template="Order Filled: {symbol}",
                message_template=(
                    "Your {side} order for {quantity} {symbol} "
                    "has been filled at {price}."
                ),
                channel_format={
                    "telegram": (
                        "✅ *Order Filled*\n"
                        "Symbol: {symbol}\n"
                        "Side: {side}\n"
                        "Quantity: {quantity}\n"
                        "Price: {price}"
                    ),
                },
            ),
            NotificationTemplate(
                name="order_failed",
                title_template="Order Failed: {symbol}",
                message_template=(
                    "Your {side} order for {quantity} {symbol} "
                    "failed. Reason: {reason}."
                ),
                channel_format={
                    "telegram": (
                        "❌ *Order Failed*\n"
                        "Symbol: {symbol}\n"
                        "Side: {side}\n"
                        "Reason: {reason}"
                    ),
                },
            ),
            NotificationTemplate(
                name="grid_completed",
                title_template="Grid Completed: {instance_id}",
                message_template=(
                    "Grid trading for instance {instance_id} "
                    "has completed. Total profit: {profit}."
                ),
                channel_format={
                    "telegram": (
                        "🎯 *Grid Completed*\n"
                        "Instance: {instance_id}\n"
                        "Total Profit: {profit}"
                    ),
                },
            ),
            NotificationTemplate(
                name="profit_lock_triggered",
                title_template="Profit Lock Triggered: {instance_id}",
                message_template=(
                    "Profit lock triggered for instance {instance_id} "
                    "at price {price}. Lock price: {lock_price}."
                ),
                channel_format={
                    "telegram": (
                        "🔒 *Profit Lock Triggered*\n"
                        "Instance: {instance_id}\n"
                        "Price: {price}\n"
                        "Lock Price: {lock_price}"
                    ),
                },
            ),
            NotificationTemplate(
                name="recovery_failed",
                title_template="Recovery Failed: {instance_id}",
                message_template=(
                    "Recovery failed for instance {instance_id}. "
                    "Error: {error}. Manual intervention required."
                ),
                channel_format={
                    "telegram": (
                        "⚠️ *Recovery Failed*\n"
                        "Instance: {instance_id}\n"
                        "Error: {error}"
                    ),
                },
            ),
            NotificationTemplate(
                name="risk_rejected",
                title_template="Risk Rejected: {symbol}",
                message_template=(
                    "Order for {symbol} rejected by risk manager. "
                    "Reason: {reason}. Current exposure: {exposure}."
                ),
                channel_format={
                    "telegram": (
                        "🚫 *Risk Rejected*\n"
                        "Symbol: {symbol}\n"
                        "Reason: {reason}\n"
                        "Exposure: {exposure}"
                    ),
                },
            ),
        ]

        for template in defaults:
            self._templates[template.name] = template
