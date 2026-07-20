"""
GridStateMachine — validates grid and per-level state transitions.
GridStateStore — in-memory store of GridState per instance_id.
"""

from __future__ import annotations

from typing import Any

from core.domain_types import GridLevel, GridLevelStatus, GridState
from core.exceptions import GridError, InvalidStateTransition


class GridStatus:
    """Overall grid status constants."""

    IDLE = "idle"
    INITIALIZED = "initialized"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class GridStateMachine:
    """Validates transitions for the overall grid and individual levels."""

    GRID_TRANSITIONS: dict[str, set[str]] = {
        GridStatus.IDLE: {GridStatus.INITIALIZED},
        GridStatus.INITIALIZED: {GridStatus.ACTIVE, GridStatus.ERROR},
        GridStatus.ACTIVE: {
            GridStatus.PAUSED,
            GridStatus.COMPLETED,
            GridStatus.ERROR,
        },
        GridStatus.PAUSED: {
            GridStatus.ACTIVE,
            GridStatus.COMPLETED,
            GridStatus.ERROR,
        },
        GridStatus.ERROR: {GridStatus.ACTIVE, GridStatus.PAUSED},
        GridStatus.COMPLETED: set(),
    }

    LEVEL_TRANSITIONS: dict[GridLevelStatus, set[GridLevelStatus]] = {
        GridLevelStatus.WAITING: {
            GridLevelStatus.OPEN,
            GridLevelStatus.CANCELLED,
        },
        GridLevelStatus.OPEN: {
            GridLevelStatus.FILLED,
            GridLevelStatus.CANCELLED,
            GridLevelStatus.WAITING,
            GridLevelStatus.TP_HIT,
        },
        GridLevelStatus.FILLED: {
            GridLevelStatus.OPEN,
            GridLevelStatus.TP_HIT,
            GridLevelStatus.CANCELLED,
        },
        GridLevelStatus.TP_HIT: {
            GridLevelStatus.WAITING,
            GridLevelStatus.OPEN,
        },
        GridLevelStatus.CANCELLED: {
            GridLevelStatus.WAITING,
        },
    }

    @classmethod
    def validate_grid_transition(cls, from_status: str, to_status: str) -> None:
        allowed = cls.GRID_TRANSITIONS.get(from_status)
        if allowed is None or to_status not in allowed:
            raise InvalidStateTransition(
                f"Invalid grid transition: {from_status} → {to_status}",
                current_state=from_status,
                target_state=to_status,
            )

    @classmethod
    def validate_level_transition(
        cls, from_status: GridLevelStatus, to_status: GridLevelStatus
    ) -> None:
        allowed = cls.LEVEL_TRANSITIONS.get(from_status)
        if allowed is None or to_status not in allowed:
            raise InvalidStateTransition(
                f"Invalid grid level transition: {from_status.value} → {to_status.value}",
                current_state=from_status.value,
                target_state=to_status.value,
            )

    @classmethod
    def is_grid_terminal(cls, status: str) -> bool:
        return status in {GridStatus.COMPLETED}

    @classmethod
    def is_level_terminal(cls, status: GridLevelStatus) -> bool:
        return status == GridLevelStatus.TP_HIT


class GridStateStore:
    """In-memory store of GridState keyed by instance_id."""

    def __init__(self) -> None:
        self._grids: dict[str, GridState] = {}

    def put(self, instance_id: str, state: GridState) -> None:
        self._grids[instance_id] = state

    def get(self, instance_id: str) -> GridState | None:
        return self._grids.get(instance_id)

    def remove(self, instance_id: str) -> GridState | None:
        return self._grids.pop(instance_id, None)

    def transition_grid(self, instance_id: str, to_status: str) -> GridState:
        state = self._grids.get(instance_id)
        if state is None:
            raise GridError(f"Grid not found for instance {instance_id}")
        GridStateMachine.validate_grid_transition(state.status, to_status)
        state.status = to_status
        return state

    def transition_level(
        self, instance_id: str, level: int, to_status: GridLevelStatus
    ) -> GridLevel:
        state = self._grids.get(instance_id)
        if state is None:
            raise GridError(f"Grid not found for instance {instance_id}")
        grid_level: GridLevel | None = None
        for lv in state.levels:
            if lv.level == level:
                grid_level = lv
                break
        if grid_level is None:
            raise GridError(f"Grid level {level} not found for instance {instance_id}")
        GridStateMachine.validate_level_transition(grid_level.status, to_status)
        grid_level.status = to_status
        return grid_level

    def get_level(self, instance_id: str, level: int) -> GridLevel | None:
        state = self._grids.get(instance_id)
        if state is None:
            return None
        for lv in state.levels:
            if lv.level == level:
                return lv
        return None

    def update_level(self, instance_id: str, level: int, **kwargs: Any) -> GridLevel:
        lv = self.get_level(instance_id, level)
        if lv is None:
            raise GridError(f"Grid level {level} not found for instance {instance_id}")
        for key, value in kwargs.items():
            setattr(lv, key, value)
        return lv

    def list_levels(self, instance_id: str) -> list[GridLevel]:
        state = self._grids.get(instance_id)
        if state is None:
            return []
        return list(state.levels)

    def clear(self) -> None:
        self._grids.clear()
