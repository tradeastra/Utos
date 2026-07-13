"""
Unit tests for ExecutionEngine order state machine.
"""

import pytest

from core.exceptions import InvalidStateTransition
from engine.execution.models import ExecutionOrderStatus
from engine.execution.order_state import OrderStateMachine


class TestOrderStateMachine:
    def test_pending_to_submitting(self) -> None:
        OrderStateMachine.validate_transition(
            ExecutionOrderStatus.PENDING, ExecutionOrderStatus.SUBMITTING
        )

    def test_pending_to_open_raises(self) -> None:
        with pytest.raises(InvalidStateTransition):
            OrderStateMachine.validate_transition(
                ExecutionOrderStatus.PENDING, ExecutionOrderStatus.OPEN
            )

    def test_submitting_to_open(self) -> None:
        OrderStateMachine.validate_transition(
            ExecutionOrderStatus.SUBMITTING, ExecutionOrderStatus.OPEN
        )

    def test_submitting_to_filled(self) -> None:
        OrderStateMachine.validate_transition(
            ExecutionOrderStatus.SUBMITTING, ExecutionOrderStatus.FILLED
        )

    def test_submitting_to_rejected(self) -> None:
        OrderStateMachine.validate_transition(
            ExecutionOrderStatus.SUBMITTING, ExecutionOrderStatus.REJECTED
        )

    def test_submitting_to_cancelled_raises(self) -> None:
        with pytest.raises(InvalidStateTransition):
            OrderStateMachine.validate_transition(
                ExecutionOrderStatus.SUBMITTING, ExecutionOrderStatus.CANCELLED
            )

    def test_open_to_filled(self) -> None:
        OrderStateMachine.validate_transition(
            ExecutionOrderStatus.OPEN, ExecutionOrderStatus.FILLED
        )

    def test_open_to_cancelling(self) -> None:
        OrderStateMachine.validate_transition(
            ExecutionOrderStatus.OPEN, ExecutionOrderStatus.CANCELLING
        )

    def test_open_to_cancelled(self) -> None:
        OrderStateMachine.validate_transition(
            ExecutionOrderStatus.OPEN, ExecutionOrderStatus.CANCELLED
        )

    def test_partially_filled_to_filled(self) -> None:
        OrderStateMachine.validate_transition(
            ExecutionOrderStatus.PARTIALLY_FILLED, ExecutionOrderStatus.FILLED
        )

    def test_cancelling_to_cancelled(self) -> None:
        OrderStateMachine.validate_transition(
            ExecutionOrderStatus.CANCELLING, ExecutionOrderStatus.CANCELLED
        )

    def test_filled_is_terminal(self) -> None:
        assert OrderStateMachine.is_terminal(ExecutionOrderStatus.FILLED) is True

    def test_open_is_not_terminal(self) -> None:
        assert OrderStateMachine.is_terminal(ExecutionOrderStatus.OPEN) is False

    def test_failed_to_submitting(self) -> None:
        OrderStateMachine.validate_transition(
            ExecutionOrderStatus.FAILED, ExecutionOrderStatus.SUBMITTING
        )

    def test_partially_filled_to_partially_filled(self) -> None:
        OrderStateMachine.validate_transition(
            ExecutionOrderStatus.PARTIALLY_FILLED,
            ExecutionOrderStatus.PARTIALLY_FILLED,
        )

    def test_cancelling_to_filled(self) -> None:
        OrderStateMachine.validate_transition(
            ExecutionOrderStatus.CANCELLING, ExecutionOrderStatus.FILLED
        )

    def test_cancelling_to_partially_filled(self) -> None:
        OrderStateMachine.validate_transition(
            ExecutionOrderStatus.CANCELLING, ExecutionOrderStatus.PARTIALLY_FILLED
        )

    def test_filled_to_anything_raises(self) -> None:
        with pytest.raises(InvalidStateTransition):
            OrderStateMachine.validate_transition(
                ExecutionOrderStatus.FILLED, ExecutionOrderStatus.CANCELLED
            )
