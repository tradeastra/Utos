"""Unit tests for TemplateEngine."""

import pytest

from core.exceptions import NotificationError
from engine.notification.template import NotificationTemplate, TemplateEngine


class TestDefaultTemplates:

    def test_default_templates_registered(self) -> None:
        engine = TemplateEngine()
        templates = engine.list_templates()
        assert "order_filled" in templates
        assert "order_failed" in templates
        assert "grid_completed" in templates
        assert "profit_lock_triggered" in templates
        assert "recovery_failed" in templates
        assert "risk_rejected" in templates

    def test_render_order_filled(self) -> None:
        engine = TemplateEngine()
        msg = engine.render("order_filled", {
            "symbol": "BTCUSDT",
            "side": "buy",
            "quantity": "1.5",
            "price": "50000",
        })
        assert "BTCUSDT" in msg.title
        assert "1.5" in msg.message
        assert "50000" in msg.message

    def test_render_telegram_format(self) -> None:
        engine = TemplateEngine()
        msg = engine.render("order_filled", {
            "symbol": "BTCUSDT",
            "side": "buy",
            "quantity": "1.5",
            "price": "50000",
        }, channel="telegram")
        assert "✅" in msg.message
        assert "BTCUSDT" in msg.message


class TestCustomTemplates:

    def test_register_and_render(self) -> None:
        engine = TemplateEngine()
        engine.register_template(NotificationTemplate(
            name="custom",
            title_template="Alert: {type}",
            message_template="Value: {value}",
        ))
        msg = engine.render("custom", {"type": "warning", "value": "42"})
        assert msg.title == "Alert: warning"
        assert msg.message == "Value: 42"

    def test_render_not_found(self) -> None:
        engine = TemplateEngine()
        with pytest.raises(NotificationError):
            engine.render("nonexistent", {})

    def test_render_missing_variable(self) -> None:
        engine = TemplateEngine()
        with pytest.raises(NotificationError):
            engine.render("order_filled", {"symbol": "BTCUSDT"})


class TestQueries:

    def test_get_template(self) -> None:
        engine = TemplateEngine()
        template = engine.get_template("order_filled")
        assert template is not None
        assert template.name == "order_filled"

    def test_get_template_not_found(self) -> None:
        engine = TemplateEngine()
        assert engine.get_template("nonexistent") is None
