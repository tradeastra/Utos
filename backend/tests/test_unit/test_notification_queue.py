"""Unit tests for NotificationQueue."""

import pytest

from engine.notification.queue import NotificationQueue, QueuedNotification


class TestEnqueue:

    def test_enqueue(self) -> None:
        nq = NotificationQueue()
        nid = nq.create_and_enqueue("user-1", "telegram", "@user", "Title", "Message")
        assert isinstance(nid, str)
        assert nq.get_pending_count() == 1
        assert nq.get_metrics()["enqueued"] == 1

    def test_enqueue_notification_object(self) -> None:
        nq = NotificationQueue()
        notification = QueuedNotification(
            id="test-1",
            user_id="user-1",
            channel="email",
            recipient="user@example.com",
            title="Test",
            message="Hello",
        )
        nid = nq.enqueue(notification)
        assert nid == "test-1"
        assert nq.get_pending_count() == 1


class TestProcess:

    @pytest.mark.asyncio
    async def test_process_success(self) -> None:
        sent: list[QueuedNotification] = []
        def send_fn(n: QueuedNotification) -> bool:
            sent.append(n)
            return True
        nq = NotificationQueue(send_fn=send_fn)
        nq.create_and_enqueue("user-1", "telegram", "@user", "Title", "Message")
        results = await nq.process()
        assert len(results) == 1
        assert results[0].status == "success"
        assert len(sent) == 1
        assert nq.get_metrics()["sent"] == 1

    @pytest.mark.asyncio
    async def test_process_no_send_fn(self) -> None:
        nq = NotificationQueue()
        nq.create_and_enqueue("user-1", "telegram", "@user", "Title", "Message")
        results = await nq.process()
        assert results[0].status == "failed"
        assert "No send function" in results[0].error

    @pytest.mark.asyncio
    async def test_retry_then_success(self) -> None:
        attempts: list[int] = []
        def send_fn(n: QueuedNotification) -> bool:
            attempts.append(1)
            if len(attempts) < 2:
                raise RuntimeError("fail")
            return True
        nq = NotificationQueue(send_fn=send_fn, max_retries=3)
        nq.create_and_enqueue("user-1", "telegram", "@user", "Title", "Message")
        await nq.process()
        if nq.get_pending_count() > 0:
            await nq.process()
        assert nq.get_metrics()["sent"] == 1
        assert len(attempts) == 2

    @pytest.mark.asyncio
    async def test_fail_after_max_retries(self) -> None:
        dlq_entries: list[tuple] = []
        def dlq_cb(n: QueuedNotification, reason: str) -> None:
            dlq_entries.append((n.id, reason))

        def always_fail(n: QueuedNotification) -> bool:
            raise RuntimeError("permanent")

        nq = NotificationQueue(send_fn=always_fail, max_retries=2, dlq_callback=dlq_cb)
        nq.create_and_enqueue("user-1", "telegram", "@user", "Title", "Message")
        await nq.process()
        if nq.get_pending_count() > 0:
            await nq.process()
        assert nq.get_metrics()["failed"] == 1
        assert nq.get_metrics()["moved_to_dlq"] == 1
        assert len(dlq_entries) == 1

    @pytest.mark.asyncio
    async def test_async_send_fn(self) -> None:
        sent: list[QueuedNotification] = []

        async def async_send(n: QueuedNotification) -> bool:
            sent.append(n)
            return True

        nq = NotificationQueue(send_fn=async_send)
        nq.create_and_enqueue("user-1", "telegram", "@user", "Title", "Message")
        results = await nq.process()
        assert results[0].status == "success"
        assert len(sent) == 1

    @pytest.mark.asyncio
    async def test_empty_queue(self) -> None:
        nq = NotificationQueue(send_fn=lambda n: True)
        results = await nq.process()
        assert len(results) == 0
