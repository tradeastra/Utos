"""
ProfitLockState + ProfitLockStateMachine + ProfitLockStore.

State tracking for per-instance profit lock lifecycle.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from core.exceptions import InvalidStateTransition, ProfitLockError


class ProfitLockStatus:
    """Profit lock status constants."""

    DISABLED = "disabled"
    MONITORING = "monitoring"
    TRIGGERED = "triggered"
    EXECUTING = "executing"
    LOCKED = "locked"
    CANCELLED = "cancelled"
    ERROR = "error"


@dataclass
class ProfitLockState:
    """Per-instance profit lock state."""

    instance_id: str
    status: str = ProfitLockStatus.DISABLED
    enabled: bool = False
    trigger_percentage: Decimal = Decimal("0")
    trail_percentage: Decimal = Decimal("0")
    max_profit_percentage: Decimal = Decimal("0")  # 0 = no cap
    entry_price: Decimal = Decimal("0")
    quantity: Decimal = Decimal("0")
    side: str = "long"
    highest_price: Decimal | None = None
    lock_price: Decimal | None = None
    is_triggered: bool = False
    is_executed: bool = False
    lock_order_id: str | None = None
    exchange_account_id: uuid.UUID | None = None
    symbol: str = ""


@dataclass
class ProfitLockMetrics:
    """Internal metrics for observability."""

    decisions_made: int = 0
    avg_decision_time_ms: float = 0.0
    errors_count: int = 0
    retries_count: int = 0
    events_processed: int = 0
    locks_triggered: int = 0
    locks_executed: int = 0
    _decision_times: list[float] = field(default_factory=list, repr=False)

    def record_decision(self, duration_ms: float) -> None:
        self.decisions_made += 1
        self._decision_times.append(duration_ms)
        if self._decision_times:
            self.avg_decision_time_ms = sum(self._decision_times) / len(
                self._decision_times
            )

    def record_event(self) -> None:
        self.events_processed += 1

    def record_error(self) -> None:
        self.errors_count += 1

    def record_retry(self) -> None:
        self.retries_count += 1

    def record_lock_triggered(self) -> None:
        self.locks_triggered += 1

    def record_lock_executed(self) -> None:
        self.locks_executed += 1


class ProfitLockStateMachine:
    """Validates profit lock state transitions."""

    TRANSITIONS: dict[str, set[str]] = {
        ProfitLockStatus.DISABLED: {
            ProfitLockStatus.MONITORING,
            ProfitLockStatus.CANCELLED,
        },
        ProfitLockStatus.MONITORING: {
            ProfitLockStatus.TRIGGERED,
            ProfitLockStatus.DISABLED,
            ProfitLockStatus.CANCELLED,
            ProfitLockStatus.ERROR,
        },
        ProfitLockStatus.TRIGGERED: {
            ProfitLockStatus.TRIGGERED,  # trailing update
            ProfitLockStatus.EXECUTING,
            ProfitLockStatus.DISABLED,
            ProfitLockStatus.CANCELLED,
            ProfitLockStatus.ERROR,
        },
        ProfitLockStatus.EXECUTING: {
            ProfitLockStatus.LOCKED,
            ProfitLockStatus.TRIGGERED,  # order cancelled, resume trailing
            ProfitLockStatus.DISABLED,
            ProfitLockStatus.CANCELLED,
            ProfitLockStatus.ERROR,
        },
        ProfitLockStatus.LOCKED: {
            ProfitLockStatus.MONITORING,  # reset for new position
            ProfitLockStatus.DISABLED,
            ProfitLockStatus.CANCELLED,
        },
        ProfitLockStatus.CANCELLED: {
            ProfitLockStatus.DISABLED,
            ProfitLockStatus.MONITORING,
        },
        ProfitLockStatus.ERROR: {
            ProfitLockStatus.MONITORING,
            ProfitLockStatus.TRIGGERED,
            ProfitLockStatus.DISABLED,
        },
    }

    @classmethod
    def validate_transition(cls, from_status: str, to_status: str) -> None:
        allowed = cls.TRANSITIONS.get(from_status)
        if allowed is None or to_status not in allowed:
            raise InvalidStateTransition(
                f"Invalid profit lock transition: {from_status} → {to_status}",
                current_state=from_status,
                target_state=to_status,
            )

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        return status in {ProfitLockStatus.LOCKED, ProfitLockStatus.DISABLED}


class ProfitLockStore:
    """In-memory store of ProfitLockState and metrics, keyed by instance_id."""

    def __init__(self) -> None:
        self._states: dict[str, ProfitLockState] = {}
        self._metrics: dict[str, ProfitLockMetrics] = {}

    def put(self, instance_id: str, state: ProfitLockState) -> None:
        self._states[instance_id] = state
        if instance_id not in self._metrics:
            self._metrics[instance_id] = ProfitLockMetrics()

    def get(self, instance_id: str) -> ProfitLockState | None:
        return self._states.get(instance_id)

    def remove(self, instance_id: str) -> ProfitLockState | None:
        self._metrics.pop(instance_id, None)
        return self._states.pop(instance_id, None)

    def transition(self, instance_id: str, to_status: str) -> ProfitLockState:
        state = self._states.get(instance_id)
        if state is None:
            raise ProfitLockError(f"Profit lock not found for instance {instance_id}")
        ProfitLockStateMachine.validate_transition(state.status, to_status)
        state.status = to_status
        return state

    def get_metrics(self, instance_id: str) -> ProfitLockMetrics:
        if instance_id not in self._metrics:
            self._metrics[instance_id] = ProfitLockMetrics()
        return self._metrics[instance_id]

    def update(self, instance_id: str, **kwargs: Any) -> ProfitLockState:
        state = self._states.get(instance_id)
        if state is None:
            raise ProfitLockError(f"Profit lock not found for instance {instance_id}")
        for key, value in kwargs.items():
            setattr(state, key, value)
        return state

    def clear(self) -> None:
        self._states.clear()
        self._metrics.clear()
