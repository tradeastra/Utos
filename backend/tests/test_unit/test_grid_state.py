"""
Unit tests for GridStateMachine and GridStateStore.
"""

from decimal import Decimal

import pytest
from core.domain_types import GridLevel, GridLevelStatus, GridState
from core.exceptions import GridError, InvalidStateTransition
from engine.grid.state import (
    GridStateMachine,
    GridStateStore,
    GridStatus,
)


class TestGridStateMachine:

    def test_idle_to_initialized(self) -> None:
        GridStateMachine.validate_grid_transition(
            GridStatus.IDLE, GridStatus.INITIALIZED
        )

    def test_initialized_to_active(self) -> None:
        GridStateMachine.validate_grid_transition(
            GridStatus.INITIALIZED, GridStatus.ACTIVE
        )

    def test_active_to_paused(self) -> None:
        GridStateMachine.validate_grid_transition(GridStatus.ACTIVE, GridStatus.PAUSED)

    def test_paused_to_active(self) -> None:
        GridStateMachine.validate_grid_transition(GridStatus.PAUSED, GridStatus.ACTIVE)

    def test_active_to_error(self) -> None:
        GridStateMachine.validate_grid_transition(GridStatus.ACTIVE, GridStatus.ERROR)

    def test_error_to_active(self) -> None:
        GridStateMachine.validate_grid_transition(GridStatus.ERROR, GridStatus.ACTIVE)

    def test_completed_is_terminal(self) -> None:
        assert GridStateMachine.is_grid_terminal(GridStatus.COMPLETED)
        assert not GridStateMachine.is_grid_terminal(GridStatus.ACTIVE)

    def test_invalid_grid_transition_raises(self) -> None:
        with pytest.raises(InvalidStateTransition):
            GridStateMachine.validate_grid_transition(
                GridStatus.IDLE, GridStatus.ACTIVE
            )

    def test_completed_to_active_raises(self) -> None:
        with pytest.raises(InvalidStateTransition):
            GridStateMachine.validate_grid_transition(
                GridStatus.COMPLETED, GridStatus.ACTIVE
            )


class TestGridLevelStateMachine:

    def test_waiting_to_open(self) -> None:
        GridStateMachine.validate_level_transition(
            GridLevelStatus.WAITING, GridLevelStatus.OPEN
        )

    def test_open_to_filled(self) -> None:
        GridStateMachine.validate_level_transition(
            GridLevelStatus.OPEN, GridLevelStatus.FILLED
        )

    def test_filled_to_open(self) -> None:
        GridStateMachine.validate_level_transition(
            GridLevelStatus.FILLED, GridLevelStatus.OPEN
        )

    def test_open_to_cancelled(self) -> None:
        GridStateMachine.validate_level_transition(
            GridLevelStatus.OPEN, GridLevelStatus.CANCELLED
        )

    def test_cancelled_to_waiting(self) -> None:
        GridStateMachine.validate_level_transition(
            GridLevelStatus.CANCELLED, GridLevelStatus.WAITING
        )

    def test_filled_to_tp_hit(self) -> None:
        GridStateMachine.validate_level_transition(
            GridLevelStatus.FILLED, GridLevelStatus.TP_HIT
        )

    def test_open_to_tp_hit(self) -> None:
        GridStateMachine.validate_level_transition(
            GridLevelStatus.OPEN, GridLevelStatus.TP_HIT
        )

    def test_tp_hit_to_waiting(self) -> None:
        GridStateMachine.validate_level_transition(
            GridLevelStatus.TP_HIT, GridLevelStatus.WAITING
        )

    def test_tp_hit_is_terminal(self) -> None:
        assert GridStateMachine.is_level_terminal(GridLevelStatus.TP_HIT)
        assert not GridStateMachine.is_level_terminal(GridLevelStatus.WAITING)

    def test_invalid_level_transition_raises(self) -> None:
        with pytest.raises(InvalidStateTransition):
            GridStateMachine.validate_level_transition(
                GridLevelStatus.WAITING, GridLevelStatus.TP_HIT
            )

    def test_waiting_to_filled_raises(self) -> None:
        with pytest.raises(InvalidStateTransition):
            GridStateMachine.validate_level_transition(
                GridLevelStatus.WAITING, GridLevelStatus.FILLED
            )


class TestGridStateStore:

    def _make_state(self, instance_id: str = "test-1") -> GridState:
        levels = [
            GridLevel(
                level=0,
                buy_price=Decimal("50"),
                sell_price=Decimal("60"),
                quantity=Decimal("2"),
            ),
            GridLevel(
                level=1,
                buy_price=Decimal("60"),
                sell_price=Decimal("70"),
                quantity=Decimal("1.67"),
            ),
            GridLevel(
                level=2,
                buy_price=Decimal("70"),
                sell_price=Decimal("80"),
                quantity=Decimal("1.43"),
            ),
        ]
        return GridState(
            instance_id=instance_id,
            status=GridStatus.INITIALIZED,
            upper_price=Decimal("100"),
            lower_price=Decimal("50"),
            grid_count=3,
            grid_spacing=Decimal("10"),
            investment_per_grid=Decimal("100"),
            levels=levels,
        )

    def test_put_and_get(self) -> None:
        store = GridStateStore()
        state = self._make_state()
        store.put("test-1", state)
        assert store.get("test-1") is state

    def test_get_nonexistent_returns_none(self) -> None:
        store = GridStateStore()
        assert store.get("nonexistent") is None

    def test_remove(self) -> None:
        store = GridStateStore()
        state = self._make_state()
        store.put("test-1", state)
        removed = store.remove("test-1")
        assert removed is state
        assert store.get("test-1") is None

    def test_remove_nonexistent_returns_none(self) -> None:
        store = GridStateStore()
        assert store.remove("nonexistent") is None

    def test_transition_grid(self) -> None:
        store = GridStateStore()
        store.put("test-1", self._make_state())
        state = store.transition_grid("test-1", GridStatus.ACTIVE)
        assert state.status == GridStatus.ACTIVE

    def test_transition_grid_invalid_raises(self) -> None:
        store = GridStateStore()
        store.put("test-1", self._make_state())
        with pytest.raises(InvalidStateTransition):
            store.transition_grid("test-1", GridStatus.PAUSED)

    def test_transition_grid_nonexistent_raises(self) -> None:
        store = GridStateStore()
        with pytest.raises(GridError):
            store.transition_grid("nonexistent", GridStatus.ACTIVE)

    def test_transition_level(self) -> None:
        store = GridStateStore()
        store.put("test-1", self._make_state())
        lv = store.transition_level("test-1", 0, GridLevelStatus.OPEN)
        assert lv.status == GridLevelStatus.OPEN

    def test_transition_level_invalid_raises(self) -> None:
        store = GridStateStore()
        store.put("test-1", self._make_state())
        with pytest.raises(InvalidStateTransition):
            store.transition_level("test-1", 0, GridLevelStatus.TP_HIT)

    def test_transition_level_nonexistent_grid_raises(self) -> None:
        store = GridStateStore()
        with pytest.raises(GridError):
            store.transition_level("nonexistent", 0, GridLevelStatus.OPEN)

    def test_transition_level_nonexistent_level_raises(self) -> None:
        store = GridStateStore()
        store.put("test-1", self._make_state())
        with pytest.raises(GridError):
            store.transition_level("test-1", 99, GridLevelStatus.OPEN)

    def test_get_level(self) -> None:
        store = GridStateStore()
        store.put("test-1", self._make_state())
        lv = store.get_level("test-1", 1)
        assert lv is not None
        assert lv.level == 1

    def test_get_level_nonexistent(self) -> None:
        store = GridStateStore()
        store.put("test-1", self._make_state())
        assert store.get_level("test-1", 99) is None

    def test_update_level(self) -> None:
        store = GridStateStore()
        store.put("test-1", self._make_state())
        lv = store.update_level("test-1", 0, buy_order_id="order-123")
        assert lv.buy_order_id == "order-123"

    def test_list_levels(self) -> None:
        store = GridStateStore()
        store.put("test-1", self._make_state())
        levels = store.list_levels("test-1")
        assert len(levels) == 3

    def test_list_levels_empty(self) -> None:
        store = GridStateStore()
        assert store.list_levels("nonexistent") == []

    def test_clear(self) -> None:
        store = GridStateStore()
        store.put("test-1", self._make_state())
        store.clear()
        assert store.get("test-1") is None
