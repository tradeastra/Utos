"""
Order state machine for the Execution Engine.
"""

from core.exceptions import InvalidStateTransition

from engine.execution.models import ExecutionOrderStatus


class OrderStateMachine:
    """Validates lifecycle transitions for an order handled by ExecutionEngine."""

    TRANSITIONS: dict[ExecutionOrderStatus, set[ExecutionOrderStatus]] = {
        ExecutionOrderStatus.PENDING: {ExecutionOrderStatus.SUBMITTING},
        ExecutionOrderStatus.SUBMITTING: {
            ExecutionOrderStatus.OPEN,
            ExecutionOrderStatus.PARTIALLY_FILLED,
            ExecutionOrderStatus.FILLED,
            ExecutionOrderStatus.REJECTED,
            ExecutionOrderStatus.FAILED,
        },
        ExecutionOrderStatus.OPEN: {
            ExecutionOrderStatus.PARTIALLY_FILLED,
            ExecutionOrderStatus.FILLED,
            ExecutionOrderStatus.CANCELLING,
            ExecutionOrderStatus.CANCELLED,
        },
        ExecutionOrderStatus.PARTIALLY_FILLED: {
            ExecutionOrderStatus.PARTIALLY_FILLED,
            ExecutionOrderStatus.FILLED,
            ExecutionOrderStatus.CANCELLING,
            ExecutionOrderStatus.CANCELLED,
        },
        ExecutionOrderStatus.CANCELLING: {
            ExecutionOrderStatus.CANCELLED,
            ExecutionOrderStatus.FILLED,
            ExecutionOrderStatus.PARTIALLY_FILLED,
        },
        ExecutionOrderStatus.FAILED: {ExecutionOrderStatus.SUBMITTING},
        # Terminal states
        ExecutionOrderStatus.FILLED: set(),
        ExecutionOrderStatus.CANCELLED: set(),
        ExecutionOrderStatus.REJECTED: set(),
    }

    @classmethod
    def validate_transition(
        cls,
        current: ExecutionOrderStatus,
        target: ExecutionOrderStatus,
    ) -> None:
        """Raise InvalidStateTransition if target is not allowed from current."""
        allowed = cls.TRANSITIONS.get(current, set())
        if target not in allowed:
            raise InvalidStateTransition(
                message=(
                    f"Cannot transition order from {current.value} "
                    f"to {target.value}"
                ),
                current_state=current.value,
                target_state=target.value,
            )

    @classmethod
    def is_terminal(cls, status: ExecutionOrderStatus) -> bool:
        """Return True if the status is terminal."""
        return status in {
            ExecutionOrderStatus.FILLED,
            ExecutionOrderStatus.CANCELLED,
            ExecutionOrderStatus.REJECTED,
        }
