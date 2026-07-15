"""Unit tests for NotificationService."""

import pytest

from core.exceptions import NotificationError
from engine.notification.channels import EmailChannel, TelegramChannel
from engine.notification.service import NotificationService


class TestRegistration:

    def test_register_channel(self) -> None:
        svc = NotificationService()
        svc.register_channel(EmailChannel())
        svc.register_channel(TelegramChannel())
        assert svc.get_pending_count() == 0

    def test_register_template(self) -> None:
        svc = NotificationService()
        svc.register_template("custom", "Alert: {type}", "Value: {value}")
        assert svc.get_pending_count() == 0

    def test_set_recipient(self) -> None:
        svc = NotificationService()
        svc.set_recipient("user-1", "telegram", "@user1")
        assert svc.get_recipient("user-1", "telegram") == "@user1"
        assert svc.get_recipient("user-1", "email") == "user-1"


class TestNotify:

    @pytest.mark.asyncio
    async def test_notify_enqueues(self) -> None:
        svc = NotificationService()
        svc.register_channel(TelegramChannel())
        svc.set_recipient("user-1", "telegram", "@user1")
        nid = await svc.notify(
            "user-1", "order_filled", "telegram",
            {"symbol": "BTCUSDT", "side": "buy", "quantity": "1", "price": "50000"},
        )
        assert isinstance(nid, str)
        assert svc.get_pending_count() == 1
        assert svc.get_metrics()["notifications_requested"] == 1

    @pytest.mark.asyncio
    async def test_notify_unregistered_channel(self) -> None:
        svc = NotificationService()
        with pytest.raises(NotificationError):
            await svc.notify("user-1", "order_filled", "telegram", {})

    @pytest.mark.asyncio
    async def test_notify_multi(self) -> None:
        svc = NotificationService()
        svc.register_channel(EmailChannel())
        svc.register_channel(TelegramChannel())
        svc.set_recipient("user-1", "email", "user@example.com")
        svc.set_recipient("user-1", "telegram", "@user1")
        ids = await svc.notify_multi(
            "user-1", "order_filled", ["email", "telegram"],
            {"symbol": "BTCUSDT", "side": "buy", "quantity": "1", "price": "50000"},
        )
        assert len(ids) == 2
        assert svc.get_pending_count() == 2

    @pytest.mark.asyncio
    async def test_notify_multi_skips_failed(self) -> None:
        svc = NotificationService()
        svc.register_channel(TelegramChannel())
        ids = await svc.notify_multi(
            "user-1", "order_filled", ["telegram", "email"],
            {"symbol": "BTCUSDT", "side": "buy", "quantity": "1", "price": "50000"},
        )
        assert len(ids) == 1


class TestProcessQueue:

    @pytest.mark.asyncio
    async def test_process_queue_success(self) -> None:
        svc = NotificationService()
        svc.register_channel(TelegramChannel())
        svc.set_recipient("user-1", "telegram", "@user1")
        await svc.notify(
            "user-1", "order_filled", "telegram",
            {"symbol": "BTCUSDT", "side": "buy", "quantity": "1", "price": "50000"},
        )
        results = await svc.process_queue()
        assert len(results) == 1
        assert results[0]["status"] == "success"
        assert svc.get_metrics()["notifications_sent"] == 1

    @pytest.mark.asyncio
    async def test_process_empty_queue(self) -> None:
        svc = NotificationService()
        results = await svc.process_queue()
        assert len(results) == 0
