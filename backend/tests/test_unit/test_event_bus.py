"""Unit tests for EventBus."""

import pytest
from engine.scheduler.bus import EventBus


class TestPublishSubscribe:

    @pytest.mark.asyncio
    async def test_publish_to_subscriber(self) -> None:
        bus = EventBus()
        received: list[dict] = []
        bus.subscribe("ORDER_FILLED", lambda e: received.append(e))
        await bus.publish("ORDER_FILLED", {"order_id": "123"})
        assert len(received) == 1
        assert received[0]["data"]["order_id"] == "123"
        assert received[0]["event_type"] == "ORDER_FILLED"

    @pytest.mark.asyncio
    async def test_publish_to_multiple_subscribers(self) -> None:
        bus = EventBus()
        received_a: list[dict] = []
        received_b: list[dict] = []
        bus.subscribe("ORDER_FILLED", lambda e: received_a.append(e))
        bus.subscribe("ORDER_FILLED", lambda e: received_b.append(e))
        await bus.publish("ORDER_FILLED", {"order_id": "123"})
        assert len(received_a) == 1
        assert len(received_b) == 1

    @pytest.mark.asyncio
    async def test_publish_no_subscribers(self) -> None:
        bus = EventBus()
        event_id = await bus.publish("UNKNOWN_EVENT", {"data": 1})
        assert isinstance(event_id, str)

    @pytest.mark.asyncio
    async def test_async_handler(self) -> None:
        bus = EventBus()
        received: list[dict] = []

        async def handler(event: dict) -> None:
            received.append(event)

        bus.subscribe("PRICE_UPDATE", handler)
        await bus.publish("PRICE_UPDATE", {"price": 100})
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_handler_exception_does_not_block_others(self) -> None:
        bus = EventBus()
        received: list[dict] = []

        def bad_handler(e: dict) -> None:
            raise RuntimeError("boom")

        bus.subscribe("TEST", bad_handler)
        bus.subscribe("TEST", lambda e: received.append(e))
        await bus.publish("TEST", {"v": 1})
        assert len(received) == 1


class TestUnsubscribe:

    @pytest.mark.asyncio
    async def test_unsubscribe(self) -> None:
        bus = EventBus()
        received: list[dict] = []
        sub_id = bus.subscribe("TEST", lambda e: received.append(e))
        await bus.publish("TEST", {"v": 1})
        assert len(received) == 1
        assert bus.unsubscribe(sub_id) is True
        await bus.publish("TEST", {"v": 2})
        assert len(received) == 1

    def test_unsubscribe_nonexistent(self) -> None:
        bus = EventBus()
        assert bus.unsubscribe("fake-id") is False


class TestMetrics:

    @pytest.mark.asyncio
    async def test_metrics_tracked(self) -> None:
        bus = EventBus()
        bus.subscribe("TEST", lambda e: None)
        bus.subscribe("TEST", lambda e: None)
        await bus.publish("TEST", {"v": 1})
        metrics = bus.get_metrics()
        assert metrics["events_published"] == 1
        assert metrics["events_delivered"] == 2
        assert metrics["subscribers_added"] == 2

    def test_subscriber_count(self) -> None:
        bus = EventBus()
        bus.subscribe("A", lambda e: None)
        bus.subscribe("A", lambda e: None)
        bus.subscribe("B", lambda e: None)
        assert bus.get_subscriber_count("A") == 2
        assert bus.get_subscriber_count("B") == 1
        assert bus.get_subscriber_count("C") == 0
