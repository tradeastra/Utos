"""
OrderTracker: in-memory tracking of orders managed by the Execution Engine.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from core.domain_types import OrderResult, OrderStatus

from engine.execution.models import ExecutionOrderStatus, TrackedOrder


class OrderTracker:
    """Tracks order state and acts as an idempotency cache for OrderRequest.

    The tracker stores:
      - (exchange_account_id, order_id) -> TrackedOrder
      - request_id -> (exchange_account_id, order_id)
    """

    def __init__(self) -> None:
        self._orders: dict[tuple[uuid.UUID, str], TrackedOrder] = {}
        self._request_index: dict[uuid.UUID, tuple[uuid.UUID, str]] = {}

    def track(
        self,
        request_id: uuid.UUID,
        exchange_account_id: uuid.UUID,
        result: OrderResult,
        status: ExecutionOrderStatus,
    ) -> TrackedOrder:
        """Create and store a new tracked order."""
        now = datetime.now(UTC)
        tracked = TrackedOrder(
            request_id=request_id,
            exchange_account_id=exchange_account_id,
            result=result,
            status=status,
            created_at=now,
            updated_at=now,
        )
        key = (exchange_account_id, result.order_id)
        self._orders[key] = tracked
        self._request_index[request_id] = key
        return tracked

    def get_by_request_id(self, request_id: uuid.UUID) -> TrackedOrder | None:
        """Return the tracked order for a given request idempotency key."""
        key = self._request_index.get(request_id)
        if key is None:
            return None
        return self._orders.get(key)

    def get(
        self,
        exchange_account_id: uuid.UUID,
        order_id: str,
    ) -> TrackedOrder | None:
        """Return the tracked order by exchange account and order ID."""
        return self._orders.get((exchange_account_id, order_id))

    def re_key(
        self,
        exchange_account_id: uuid.UUID,
        old_order_id: str,
        new_order_id: str,
    ) -> TrackedOrder | None:
        """Re-key a tracked order when the exchange returns a different order_id."""
        old_key = (exchange_account_id, old_order_id)
        tracked = self._orders.pop(old_key, None)
        if tracked is None:
            return None
        new_key = (exchange_account_id, new_order_id)
        self._orders[new_key] = tracked
        self._request_index[tracked.request_id] = new_key
        return tracked

    def update(
        self,
        exchange_account_id: uuid.UUID,
        order_id: str,
        result: OrderResult,
        status: ExecutionOrderStatus | None = None,
        increment_retry: bool = False,
    ) -> TrackedOrder | None:
        """Update an existing tracked order with fresh data."""
        tracked = self._orders.get((exchange_account_id, order_id))
        if tracked is None:
            return None
        tracked.result = result
        if status is not None:
            tracked.status = status
        if increment_retry:
            tracked.retry_count += 1
        tracked.touch()
        return tracked

    def update_status(
        self,
        exchange_account_id: uuid.UUID,
        order_id: str,
        status: ExecutionOrderStatus,
    ) -> TrackedOrder | None:
        """Update only the internal status of a tracked order."""
        tracked = self._orders.get((exchange_account_id, order_id))
        if tracked is None:
            return None
        tracked.status = status
        tracked.touch()
        return tracked

    def list_active(
        self, exchange_account_id: uuid.UUID | None = None
    ) -> list[TrackedOrder]:
        """Return active orders, optionally filtered by exchange account."""
        return [
            order
            for (acct_id, _order_id), order in self._orders.items()
            if order.is_active()
            and (exchange_account_id is None or acct_id == exchange_account_id)
        ]

    def list_all(
        self, exchange_account_id: uuid.UUID | None = None
    ) -> list[TrackedOrder]:
        """Return all orders, optionally filtered by exchange account."""
        return [
            order
            for (acct_id, _order_id), order in self._orders.items()
            if exchange_account_id is None or acct_id == exchange_account_id
        ]

    def clear(self) -> None:
        """Clear all tracked orders. Used in tests."""
        self._orders.clear()
        self._request_index.clear()

    @staticmethod
    def map_exchange_status(status: str | OrderStatus) -> ExecutionOrderStatus:
        """Map an exchange OrderStatus to the engine's internal status."""
        value = status.value if isinstance(status, OrderStatus) else str(status).lower()
        mapping = {
            "pending": ExecutionOrderStatus.PENDING,
            "open": ExecutionOrderStatus.OPEN,
            "partially_filled": ExecutionOrderStatus.PARTIALLY_FILLED,
            "filled": ExecutionOrderStatus.FILLED,
            "cancelled": ExecutionOrderStatus.CANCELLED,
            "rejected": ExecutionOrderStatus.REJECTED,
            "expired": ExecutionOrderStatus.CANCELLED,
        }
        return mapping.get(value, ExecutionOrderStatus.OPEN)
