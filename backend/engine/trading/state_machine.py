"""Process state machine and transition validation."""

from core.exceptions import InvalidStateTransition
from core.types import TradingInstanceStatus


class ProcessStateMachine:
    """Validates state transitions for a TradingProcess."""

    TRANSITIONS: dict[TradingInstanceStatus, set[TradingInstanceStatus]] = {
        TradingInstanceStatus.CREATED: {TradingInstanceStatus.READY},
        TradingInstanceStatus.READY: {TradingInstanceStatus.RUNNING},
        TradingInstanceStatus.RUNNING: {
            TradingInstanceStatus.PAUSED,
            TradingInstanceStatus.STOPPING,
            TradingInstanceStatus.RECOVERING,
            TradingInstanceStatus.ERROR,
        },
        TradingInstanceStatus.PAUSED: {
            TradingInstanceStatus.RUNNING,
            TradingInstanceStatus.RECOVERING,
            TradingInstanceStatus.ERROR,
        },
        TradingInstanceStatus.STOPPING: {TradingInstanceStatus.STOPPED, TradingInstanceStatus.ERROR},
        TradingInstanceStatus.STOPPED: set(),
        TradingInstanceStatus.ERROR: set(),
        TradingInstanceStatus.RECOVERING: {TradingInstanceStatus.RECOVERED, TradingInstanceStatus.ERROR},
        TradingInstanceStatus.RECOVERED: {
            TradingInstanceStatus.RUNNING,
            TradingInstanceStatus.PAUSED,
            TradingInstanceStatus.ERROR,
        },
    }

    @classmethod
    def validate_transition(
        cls,
        current: TradingInstanceStatus,
        target: TradingInstanceStatus,
    ) -> None:
        """Raise InvalidStateTransition if the target state is not allowed."""
        if current == target:
            raise InvalidStateTransition(
                message=f"Process is already in state {current.value}",
                current_state=current.value,
                target_state=target.value,
            )
        allowed = cls.TRANSITIONS.get(current, set())
        if target not in allowed:
            raise InvalidStateTransition(
                message=f"Cannot transition from {current.value} to {target.value}",
                current_state=current.value,
                target_state=target.value,
            )

    @classmethod
    def can_transition(
        cls,
        current: TradingInstanceStatus,
        target: TradingInstanceStatus,
    ) -> bool:
        """Return True if the transition is valid."""
        if current == target:
            return False
        return target in cls.TRANSITIONS.get(current, set())
