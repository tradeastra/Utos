"""
Unit tests for GridPlanner.
"""

from decimal import Decimal

from core.domain_types import GridLevel, GridLevelStatus, GridState
from engine.grid.planner import GridPlanner
from engine.grid.state import GridStateStore, GridStatus


def _make_store_with_levels(
    instance_id: str = "test-1",
    levels: list[GridLevel] | None = None,
    grid_status: str = GridStatus.ACTIVE,
) -> GridStateStore:
    if levels is None:
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
    store = GridStateStore()
    state = GridState(
        instance_id=instance_id,
        status=grid_status,
        upper_price=Decimal("100"),
        lower_price=Decimal("50"),
        grid_count=3,
        grid_spacing=Decimal("10"),
        investment_per_grid=Decimal("100"),
        levels=levels,
    )
    store.put(instance_id, state)
    return store


class TestGridPlannerPlan:

    def test_plan_empty_when_no_grid(self) -> None:
        store = GridStateStore()
        planner = GridPlanner(store)
        plan = planner.plan("nonexistent", Decimal("65"))
        assert plan.is_empty

    def test_place_buy_when_price_below_buy_price(self) -> None:
        store = _make_store_with_levels()
        planner = GridPlanner(store)
        plan = planner.plan("test-1", Decimal("49"))
        buy_actions = [a for a in plan.actions if a.action == "place_buy"]
        assert len(buy_actions) == 3  # all levels below current price

    def test_no_action_when_price_above_buy_and_level_waiting(self) -> None:
        store = _make_store_with_levels()
        planner = GridPlanner(store)
        plan = planner.plan("test-1", Decimal("80"))
        assert plan.is_empty  # all levels waiting, price above all buy prices

    def test_place_sell_when_level_filled_and_price_above_sell(self) -> None:
        store = _make_store_with_levels()
        store.transition_level("test-1", 1, GridLevelStatus.OPEN)
        store.transition_level("test-1", 1, GridLevelStatus.FILLED)
        planner = GridPlanner(store)
        plan = planner.plan("test-1", Decimal("71"))
        sell_actions = [a for a in plan.actions if a.action == "place_sell"]
        assert len(sell_actions) == 1
        assert sell_actions[0].level == 1
        assert sell_actions[0].price == Decimal("70")

    def test_place_buy_when_tp_hit(self) -> None:
        store = _make_store_with_levels()
        store.transition_level("test-1", 0, GridLevelStatus.OPEN)
        store.transition_level("test-1", 0, GridLevelStatus.FILLED)
        store.transition_level("test-1", 0, GridLevelStatus.TP_HIT)
        planner = GridPlanner(store)
        plan = planner.plan("test-1", Decimal("75"))
        buy_actions = [a for a in plan.actions if a.action == "place_buy"]
        assert len(buy_actions) == 1
        assert buy_actions[0].level == 0


class TestGridPlannerPlanInitial:

    def test_initial_plan_places_buys_below_current_price(self) -> None:
        store = _make_store_with_levels()
        planner = GridPlanner(store)
        plan = planner.plan_initial("test-1", Decimal("65"))
        buy_actions = [a for a in plan.actions if a.action == "place_buy"]
        assert len(buy_actions) == 2  # levels 0 (50) and 1 (60) are below 65
        assert buy_actions[0].level == 0
        assert buy_actions[1].level == 1

    def test_initial_plan_no_buys_when_price_below_all(self) -> None:
        store = _make_store_with_levels()
        planner = GridPlanner(store)
        plan = planner.plan_initial("test-1", Decimal("45"))
        assert plan.is_empty


class TestGridPlannerPlanCancelAll:

    def test_cancel_all_open_orders(self) -> None:
        store = _make_store_with_levels()
        store.transition_level("test-1", 0, GridLevelStatus.OPEN)
        store.update_level("test-1", 0, buy_order_id="order-1")
        store.transition_level("test-1", 1, GridLevelStatus.OPEN)
        store.update_level("test-1", 1, buy_order_id="order-2")
        planner = GridPlanner(store)
        plan = planner.plan_cancel_all("test-1")
        cancel_actions = [a for a in plan.actions if a.action == "cancel"]
        assert len(cancel_actions) == 2
        assert cancel_actions[0].order_id == "order-1"
        assert cancel_actions[1].order_id == "order-2"

    def test_cancel_all_no_open_orders(self) -> None:
        store = _make_store_with_levels()
        planner = GridPlanner(store)
        plan = planner.plan_cancel_all("test-1")
        assert plan.is_empty
