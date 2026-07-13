"""
Data models for the Execution Engine.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from core.types import OrderResult, OrderSide, OrderType


class ExecutionOrderStatus(str, Enum):
    """Internal lifecycle status managed by the Execution Engine."""

    PENDING = "pending"
    SUBMITTING = "submitting"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass
class OrderRequest:
    """Request to place an order through the Execution Engine.

    Every request MUST include a unique ``request_id`` that acts as an
    idempotency key. Duplicate requests with the same id return the cached
    result without hitting the exchange again.
    """

    request_id: uuid.UUID
    exchange_account_id: uuid.UUID
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: Decimal
    price: Decimal | None = None
    stop_price: Decimal | None = None
    client_order_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TrackedOrder:
    """Internal record kept by ExecutionEngine for each order."""

    request_id: uuid.UUID
    exchange_account_id: uuid.UUID
    result: OrderResult
    status: ExecutionOrderStatus
    created_at: datetime
    updated_at: datetime
    retry_count: int = 0

    def is_active(self) -> bool:
        """Return True if the order is still being worked on by the engine."""
        return self.status in {
            ExecutionOrderStatus.PENDING,
            ExecutionOrderStatus.SUBMITTING,
            ExecutionOrderStatus.OPEN,
            ExecutionOrderStatus.PARTIALLY_FILLED,
            ExecutionOrderStatus.CANCELLING,
        }

    def touch(self) -> None:
        """Update the updated_at timestamp to now."""
        self.updated_at = datetime.now(timezone.utc)
