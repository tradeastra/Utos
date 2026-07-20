"""
Unit tests for ProfitLockStateMachine and ProfitLockStore.
"""

import uuid
from decimal import Decimal

import pytest
from core.exceptions import InvalidStateTransition, ProfitLockError
from engine.profit_lock.state import (
    ProfitLockMetrics,
    ProfitLockState,
    ProfitLockStateMachine,
    ProfitLockStatus,
    ProfitLockStore,
)


class TestProfitLockStateMachine:

    def test_disabled_to_monitoring(self) -> None:
        ProfitLockStateMachine.validate_transition(
            ProfitLockStatus.DISABLED, ProfitLockStatus.MONITORING
        )

    def test_monitoring_to_triggered(self) -> None:
        ProfitLockStateMachine.validate_transition(
            ProfitLockStatus.MONITORING, ProfitLockStatus.TRIGGERED
        )

    def test_triggered_to_triggered(self) -> None:
        ProfitLockStateMachine.validate_transition(
            ProfitLockStatus.TRIGGERED, ProfitLockStatus.TRIGGERED
        )

    def test_triggered_to_executing(self) -> None:
        ProfitLockStateMachine.validate_transition(
            ProfitLockStatus.TRIGGERED, ProfitLockStatus.EXECUTING
        )

    def test_executing_to_locked(self) -> None:
        ProfitLockStateMachine.validate_transition(
            ProfitLockStatus.EXECUTING, ProfitLockStatus.LOCKED
        )

    def test_executing_to_triggered(self) -> None:
        ProfitLockStateMachine.validate_transition(
            ProfitLockStatus.EXECUTING, ProfitLockStatus.TRIGGERED
        )

    def test_locked_to_monitoring(self) -> None:
        ProfitLockStateMachine.validate_transition(
            ProfitLockStatus.LOCKED, ProfitLockStatus.MONITORING
        )

    def test_any_to_disabled(self) -> None:
        for status in [
            ProfitLockStatus.MONITORING,
            ProfitLockStatus.TRIGGERED,
            ProfitLockStatus.EXECUTING,
            ProfitLockStatus.LOCKED,
        ]:
            ProfitLockStateMachine.validate_transition(
                status, ProfitLockStatus.DISABLED
            )

    def test_invalid_transition_raises(self) -> None:
        with pytest.raises(InvalidStateTransition):
            ProfitLockStateMachine.validate_transition(
                ProfitLockStatus.DISABLED, ProfitLockStatus.TRIGGERED
            )

    def test_disabled_to_locked_raises(self) -> None:
        with pytest.raises(InvalidStateTransition):
            ProfitLockStateMachine.validate_transition(
                ProfitLockStatus.DISABLED, ProfitLockStatus.LOCKED
            )

    def test_locked_is_terminal(self) -> None:
        assert ProfitLockStateMachine.is_terminal(ProfitLockStatus.LOCKED)
        assert ProfitLockStateMachine.is_terminal(ProfitLockStatus.DISABLED)
        assert not ProfitLockStateMachine.is_terminal(ProfitLockStatus.TRIGGERED)


class TestProfitLockStore:

    def _make_state(self, instance_id: str = "inst-1") -> ProfitLockState:
        return ProfitLockState(
            instance_id=instance_id,
            status=ProfitLockStatus.MONITORING,
            enabled=True,
            trigger_percentage=Decimal("10"),
            trail_percentage=Decimal("5"),
            entry_price=Decimal("100"),
            quantity=Decimal("2"),
            side="long",
            highest_price=Decimal("100"),
            exchange_account_id=uuid.uuid4(),
            symbol="BTCUSDT",
        )

    def test_put_and_get(self) -> None:
        store = ProfitLockStore()
        state = self._make_state()
        store.put("inst-1", state)
        assert store.get("inst-1") is state

    def test_get_nonexistent_returns_none(self) -> None:
        store = ProfitLockStore()
        assert store.get("nonexistent") is None

    def test_remove(self) -> None:
        store = ProfitLockStore()
        store.put("inst-1", self._make_state())
        removed = store.remove("inst-1")
        assert removed is not None
        assert store.get("inst-1") is None

    def test_transition(self) -> None:
        store = ProfitLockStore()
        store.put("inst-1", self._make_state())
        state = store.transition("inst-1", ProfitLockStatus.TRIGGERED)
        assert state.status == ProfitLockStatus.TRIGGERED

    def test_transition_invalid_raises(self) -> None:
        store = ProfitLockStore()
        store.put("inst-1", self._make_state())
        with pytest.raises(InvalidStateTransition):
            store.transition("inst-1", ProfitLockStatus.LOCKED)

    def test_transition_nonexistent_raises(self) -> None:
        store = ProfitLockStore()
        with pytest.raises(ProfitLockError):
            store.transition("nonexistent", ProfitLockStatus.TRIGGERED)

    def test_update(self) -> None:
        store = ProfitLockStore()
        store.put("inst-1", self._make_state())
        state = store.update("inst-1", lock_price=Decimal("105"))
        assert state.lock_price == Decimal("105")

    def test_get_metrics(self) -> None:
        store = ProfitLockStore()
        store.put("inst-1", self._make_state())
        metrics = store.get_metrics("inst-1")
        assert isinstance(metrics, ProfitLockMetrics)
        assert metrics.decisions_made == 0

    def test_get_metrics_nonexistent_creates(self) -> None:
        store = ProfitLockStore()
        metrics = store.get_metrics("nonexistent")
        assert isinstance(metrics, ProfitLockMetrics)

    def test_clear(self) -> None:
        store = ProfitLockStore()
        store.put("inst-1", self._make_state())
        store.clear()
        assert store.get("inst-1") is None


class TestProfitLockMetrics:

    def test_record_decision(self) -> None:
        metrics = ProfitLockMetrics()
        metrics.record_decision(1.5)
        metrics.record_decision(2.5)
        assert metrics.decisions_made == 2
        assert metrics.avg_decision_time_ms == 2.0

    def test_record_event(self) -> None:
        metrics = ProfitLockMetrics()
        metrics.record_event()
        metrics.record_event()
        assert metrics.events_processed == 2

    def test_record_error(self) -> None:
        metrics = ProfitLockMetrics()
        metrics.record_error()
        assert metrics.errors_count == 1

    def test_record_lock_triggered(self) -> None:
        metrics = ProfitLockMetrics()
        metrics.record_lock_triggered()
        assert metrics.locks_triggered == 1

    def test_record_lock_executed(self) -> None:
        metrics = ProfitLockMetrics()
        metrics.record_lock_executed()
        assert metrics.locks_executed == 1
