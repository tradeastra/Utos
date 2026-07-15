"""
Integration tests for Sprint 13: Notification & Automation.

Tests full flow: event → automation rules → service → queue → template → channel.
"""

import pytest

from engine.notification.automation import AutomationRules
from engine.notification.channels import EmailChannel, TelegramChannel, WebhookChannel
from engine.notification.service import NotificationService


class TestFullNotificationFlow:

    @pytest.mark.asyncio
    async def test_event_to_channel_delivery(self) -> None:
        sent: list[tuple] = []

        def telegram_send(recipient: str, title: str, msg: str, data: dict) -> bool:
            sent.append((recipient, title, msg))
            return True

        svc = NotificationService()
        svc.register_channel(TelegramChannel(send_fn=telegram_send))
        svc.set_recipient("user-1", "telegram", "@trader1")

        nid = await svc.notify(
            "user-1", "order_filled", "telegram",
            {"symbol": "BTCUSDT", "side": "buy", "quantity": "1.5", "price": "50000"},
        )
        assert svc.get_pending_count() == 1

        results = await svc.process_queue()
        assert len(results) == 1
        assert results[0]["status"] == "success"
        assert len(sent) == 1
        assert "@trader1" in sent[0]
        assert "BTCUSDT" in sent[0][1]

    @pytest.mark.asyncio
    async def test_multi_channel_delivery(self) -> None:
        sent: list[tuple] = []

        def email_send(r: str, t: str, m: str, d: dict) -> bool:
            sent.append(("email", r, t))
            return True

        def telegram_send(r: str, t: str, m: str, d: dict) -> bool:
            sent.append(("telegram", r, t))
            return True

        svc = NotificationService()
        svc.register_channel(EmailChannel(send_fn=email_send))
        svc.register_channel(TelegramChannel(send_fn=telegram_send))
        svc.set_recipient("user-1", "email", "user@example.com")
        svc.set_recipient("user-1", "telegram", "@user1")

        await svc.notify_multi(
            "user-1", "order_filled", ["email", "telegram"],
            {"symbol": "BTCUSDT", "side": "buy", "quantity": "1", "price": "50000"},
        )
        await svc.process_queue()

        assert len(sent) == 2
        channels = [s[0] for s in sent]
        assert "email" in channels
        assert "telegram" in channels


class TestAutomationToNotification:

    @pytest.mark.asyncio
    async def test_automation_triggers_notification(self) -> None:
        sent: list[tuple] = []

        def telegram_send(r: str, t: str, m: str, d: dict) -> bool:
            sent.append((r, t, m))
            return True

        svc = NotificationService()
        svc.register_channel(TelegramChannel(send_fn=telegram_send))
        svc.set_recipient("user-1", "telegram", "@trader1")

        rules = AutomationRules()
        rules.add_rule(
            "profit_alert", "ORDER_FILLED",
            lambda d: float(d.get("profit_pct", 0)) > 10,
            "telegram", "order_filled",
            action_user_id="user-1",
        )

        actions = await rules.evaluate("ORDER_FILLED", {
            "symbol": "BTCUSDT",
            "side": "buy",
            "quantity": "1.5",
            "price": "50000",
            "profit_pct": 15,
        })
        assert len(actions) == 1

        for action in actions:
            await svc.notify(
                action.user_id, action.template, action.channel, action.context,
            )

        await svc.process_queue()
        assert len(sent) == 1
        assert "BTCUSDT" in sent[0][1]

    @pytest.mark.asyncio
    async def test_automation_no_trigger_when_condition_false(self) -> None:
        svc = NotificationService()
        svc.register_channel(TelegramChannel())
        svc.set_recipient("user-1", "telegram", "@trader1")

        rules = AutomationRules()
        rules.add_rule(
            "profit_alert", "ORDER_FILLED",
            lambda d: float(d.get("profit_pct", 0)) > 10,
            "telegram", "order_filled",
            action_user_id="user-1",
        )

        actions = await rules.evaluate("ORDER_FILLED", {
            "symbol": "BTCUSDT",
            "side": "buy",
            "quantity": "1",
            "price": "50000",
            "profit_pct": 5,
        })
        assert len(actions) == 0
        assert svc.get_pending_count() == 0


class TestChannelFailureIsolation:

    @pytest.mark.asyncio
    async def test_telegram_failure_does_not_block_email(self) -> None:
        sent: list[str] = []

        def email_send(r: str, t: str, m: str, d: dict) -> bool:
            sent.append("email")
            return True

        def telegram_broken(r: str, t: str, m: str, d: dict) -> bool:
            raise RuntimeError("Telegram API down")

        svc = NotificationService()
        svc.register_channel(EmailChannel(send_fn=email_send))
        svc.register_channel(TelegramChannel(send_fn=telegram_broken))
        svc.set_recipient("user-1", "email", "user@example.com")
        svc.set_recipient("user-1", "telegram", "@user1")

        await svc.notify_multi(
            "user-1", "order_filled", ["email", "telegram"],
            {"symbol": "BTCUSDT", "side": "buy", "quantity": "1", "price": "50000"},
        )
        results = await svc.process_queue()

        statuses = [r["status"] for r in results]
        assert "success" in statuses
        assert "failed" in statuses or "retry" in statuses
        assert "email" in sent


class TestRecoveryFailedNotification:

    @pytest.mark.asyncio
    async def test_recovery_failed_sends_alert(self) -> None:
        sent: list[tuple] = []

        def webhook_send(r: str, t: str, m: str, d: dict) -> bool:
            sent.append((r, t, m))
            return True

        svc = NotificationService()
        svc.register_channel(WebhookChannel(send_fn=webhook_send))
        svc.set_recipient("admin", "webhook", "https://hook.example.com/alert")

        rules = AutomationRules()
        rules.add_rule(
            "recovery_alert", "RECOVERY_FAILED",
            lambda d: True,
            "webhook", "recovery_failed",
            action_user_id="admin",
        )

        actions = await rules.evaluate("RECOVERY_FAILED", {
            "instance_id": "inst-1",
            "error": "Connection timeout",
        })
        assert len(actions) == 1

        for action in actions:
            await svc.notify(action.user_id, action.template, action.channel, action.context)

        await svc.process_queue()
        assert len(sent) == 1
        assert "inst-1" in sent[0][1]
        assert "Connection timeout" in sent[0][2]
