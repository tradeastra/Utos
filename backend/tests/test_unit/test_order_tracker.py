"""
Unit tests for OrderTracker.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from core.types import OrderResult, OrderStatus
from engine.execution.models import ExecutionOrderStatus
from engine.execution.tracker import OrderTracker


@pytest.fixture
def tracker() -> OrderTracker:
    return OrderTracker()


@pytest.fixture
def account_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def sample_result(account_id: uuid.UUID) -> OrderResult:
    return OrderResult(
        order_id="local_123",
        exchange_order_id="ex_123",
        symbol="BTCUSDT",
        side="buy",
        order_type="limit",
        quantity=Decimal("0.1"),
        price=Decimal("50000"),
        filled_quantity=Decimal("0"),
        average_fill_price=None,
        status=OrderStatus.OPEN.value,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestOrderTracker:
    def test_track_and_get(self, tracker: OrderTracker, account_id: uuid.UUID, sample_result: OrderResult) -> None:
        request_id = uuid.uuid4()
        tracked = tracker.track(request_id, account_id, sample_result, ExecutionOrderStatus.OPEN)
        assert tracker.get(account_id, sample_result.order_id) == tracked

    def test_get_by_request_id(self, tracker: OrderTracker, account_id: uuid.UUID, sample_result: OrderResult) -> None:
        request_id = uuid.uuid4()
        tracker.track(request_id, account_id, sample_result, ExecutionOrderStatus.OPEN)
        found = tracker.get_by_request_id(request_id)
        assert found is not None
        assert found.result.order_id == sample_result.order_id

    def test_update(self, tracker: OrderTracker, account_id: uuid.UUID, sample_result: OrderResult) -> None:
        request_id = uuid.uuid4()
        tracker.track(request_id, account_id, sample_result, ExecutionOrderStatus.OPEN)
        filled = OrderResult(
            order_id=sample_result.order_id,
            exchange_order_id=sample_result.exchange_order_id,
            symbol="BTCUSDT",
            side="buy",
            order_type="limit",
            quantity=Decimal("0.1"),
            price=Decimal("50000"),
            filled_quantity=Decimal("0.1"),
            average_fill_price=Decimal("49900"),
            status=OrderStatus.FILLED.value,
            created_at=sample_result.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        tracker.update(account_id, sample_result.order_id, filled, status=ExecutionOrderStatus.FILLED)
        tracked = tracker.get(account_id, sample_result.order_id)
        assert tracked is not None
        assert tracked.status == ExecutionOrderStatus.FILLED
        assert tracked.result.filled_quantity == Decimal("0.1")

    def test_update_status(self, tracker: OrderTracker, account_id: uuid.UUID, sample_result: OrderResult) -> None:
        request_id = uuid.uuid4()
        tracker.track(request_id, account_id, sample_result, ExecutionOrderStatus.OPEN)
        tracker.update_status(account_id, sample_result.order_id, ExecutionOrderStatus.CANCELLED)
        tracked = tracker.get(account_id, sample_result.order_id)
        assert tracked is not None
        assert tracked.status == ExecutionOrderStatus.CANCELLED

    def test_list_active(self, tracker: OrderTracker, account_id: uuid.UUID, sample_result: OrderResult) -> None:
        request_id = uuid.uuid4()
        tracker.track(request_id, account_id, sample_result, ExecutionOrderStatus.OPEN)
        assert len(tracker.list_active()) == 1
        assert len(tracker.list_active(account_id)) == 1

    def test_list_active_filters_by_account(self, tracker: OrderTracker, account_id: uuid.UUID, sample_result: OrderResult) -> None:
        request_id = uuid.uuid4()
        tracker.track(request_id, account_id, sample_result, ExecutionOrderStatus.OPEN)
        other_account = uuid.uuid4()
        assert len(tracker.list_active(other_account)) == 0

    def test_list_active_does_not_return_terminal(self, tracker: OrderTracker, account_id: uuid.UUID, sample_result: OrderResult) -> None:
        request_id = uuid.uuid4()
        tracker.track(request_id, account_id, sample_result, ExecutionOrderStatus.FILLED)
        assert len(tracker.list_active()) == 0

    def test_clear(self, tracker: OrderTracker, account_id: uuid.UUID, sample_result: OrderResult) -> None:
        request_id = uuid.uuid4()
        tracker.track(request_id, account_id, sample_result, ExecutionOrderStatus.OPEN)
        tracker.clear()
        assert tracker.get(account_id, sample_result.order_id) is None
        assert tracker.get_by_request_id(request_id) is None

    def test_map_exchange_status(self, tracker: OrderTracker) -> None:
        assert tracker.map_exchange_status("open") == ExecutionOrderStatus.OPEN
        assert tracker.map_exchange_status("filled") == ExecutionOrderStatus.FILLED
        assert tracker.map_exchange_status("partially_filled") == ExecutionOrderStatus.PARTIALLY_FILLED
        assert tracker.map_exchange_status("expired") == ExecutionOrderStatus.CANCELLED
