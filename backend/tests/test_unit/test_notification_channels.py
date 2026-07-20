"""Unit tests for notification channels."""

import pytest
from engine.notification.channels import (
    DiscordChannel,
    EmailChannel,
    TelegramChannel,
    WebhookChannel,
)


class TestEmailChannel:

    @pytest.mark.asyncio
    async def test_send_stub(self) -> None:
        ch = EmailChannel()
        result = await ch.send("user@example.com", "Title", "Message")
        assert result is True
        assert ch.get_metrics()["sent"] == 1

    @pytest.mark.asyncio
    async def test_send_with_callback(self) -> None:
        sent: list[tuple] = []

        def send_fn(recipient: str, title: str, msg: str, data: dict) -> bool:
            sent.append((recipient, title, msg))
            return True

        ch = EmailChannel(send_fn=send_fn)
        result = await ch.send("user@example.com", "Test", "Hello", {"key": "val"})
        assert result is True
        assert len(sent) == 1
        assert sent[0] == ("user@example.com", "Test", "Hello")

    @pytest.mark.asyncio
    async def test_send_callback_exception(self) -> None:
        def boom(recipient: str, title: str, msg: str, data: dict) -> bool:
            raise RuntimeError("SMTP down")

        ch = EmailChannel(send_fn=boom)
        result = await ch.send("user@example.com", "Test", "Hello")
        assert result is False
        assert ch.get_metrics()["failed"] == 1

    def test_channel_name(self) -> None:
        assert EmailChannel().channel_name == "email"


class TestTelegramChannel:

    @pytest.mark.asyncio
    async def test_send_stub(self) -> None:
        ch = TelegramChannel()
        result = await ch.send("@user", "Title", "Message")
        assert result is True

    @pytest.mark.asyncio
    async def test_send_with_callback(self) -> None:
        sent: list[tuple] = []

        def send_fn(recipient: str, title: str, msg: str, data: dict) -> bool:
            sent.append((recipient, title, msg))
            return True

        ch = TelegramChannel(send_fn=send_fn)
        await ch.send("@user", "Test", "Hello")
        assert len(sent) == 1

    def test_channel_name(self) -> None:
        assert TelegramChannel().channel_name == "telegram"


class TestDiscordChannel:

    @pytest.mark.asyncio
    async def test_send_stub(self) -> None:
        ch = DiscordChannel()
        result = await ch.send("channel-123", "Title", "Message")
        assert result is True

    def test_channel_name(self) -> None:
        assert DiscordChannel().channel_name == "discord"


class TestWebhookChannel:

    @pytest.mark.asyncio
    async def test_send_stub(self) -> None:
        ch = WebhookChannel()
        result = await ch.send("https://hook.example.com", "Title", "Message")
        assert result is True

    @pytest.mark.asyncio
    async def test_send_failure(self) -> None:
        ch = WebhookChannel(send_fn=lambda r, t, m, d: False)
        result = await ch.send("https://hook.example.com", "Title", "Message")
        assert result is False

    def test_channel_name(self) -> None:
        assert WebhookChannel().channel_name == "webhook"
