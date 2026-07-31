"""
GridPlanner — determines which grid levels should have active orders
based on the current market price and existing level states.

The planner is pure logic: it produces a GridPlan describing what actions
the GridEngine should take. It does not place or cancel orders itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from core.domain_types import GridLevel, GridLevelStatus

from engine.grid.state import GridStateStore


@dataclass
class GridAction:
    """A single action the GridEngine should perform."""

    level: int
    action: str  # "place_buy", "place_sell", "cancel"
    side: str  # "buy" | "sell"
    price: Decimal
    quantity: Decimal
    order_id: str | None = None  # existing order_id to cancel (for "cancel")


@dataclass
class GridPlan:
    """Result of GridPlanner.plan() — list of actions to execute."""

    actions: list[GridAction] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return len(self.actions) == 0


class GridPlanner:
    """Decides which orders to place/cancel based on current price and level states."""

    def __init__(self, store: GridStateStore) -> None:
        self._store = store

    def plan(
        self,
        instance_id: str,
        current_price: Decimal,
        breaker_active: bool = False,
        widen_multiplier: Decimal = Decimal("1"),
    ) -> GridPlan:
        """Produce a plan of actions for the grid given the current price.

        Args:
            instance_id: Grid instance id.
            current_price: Latest market price.
            breaker_active: Whether the daily drop circuit breaker is currently
                triggered. When True and ``widen_multiplier > 1``, buy actions
                are only placed at every Nth level (N = widen_multiplier) so the
                grid averages more conservatively into the drop. Sell actions
                are unaffected (exits always proceed).
            widen_multiplier: Grid step multiplier while the breaker is active
                (e.g. 2 = place buys at every 2nd level = 2× wider spacing).
                Ignored when ``breaker_active`` is False.
        """
        levels = self._store.list_levels(instance_id)
        if not levels:
            return GridPlan()

        # When the breaker is active with a widened step, skip buy levels whose
        # index is not a multiple of the multiplier. E.g. multiplier=2 → only
        # levels 0, 2, 4, ... get buys (every other level = 2× wider spacing).
        skip_buy_levels: set[int] | None = None
        if breaker_active and widen_multiplier and widen_multiplier > 1:
            mult_int = int(widen_multiplier)
            if mult_int > 1:
                skip_buy_levels = {
                    lv.level for lv in levels if lv.level % mult_int != 0
                }

        actions: list[GridAction] = []

        for lv in levels:
            action = self._plan_level(lv, current_price)
            if action is None:
                continue
            # WIDEN_STEP: skip buys at non-multiple levels. Sells always proceed.
            if (
                skip_buy_levels is not None
                and action.action == "place_buy"
                and action.level in skip_buy_levels
            ):
                continue
            actions.append(action)

        return GridPlan(actions=actions)

    def _plan_level(self, lv: GridLevel, current_price: Decimal) -> GridAction | None:
        status = lv.status

        if status == GridLevelStatus.WAITING:
            if current_price <= lv.buy_price:
                return GridAction(
                    level=lv.level,
                    action="place_buy",
                    side="buy",
                    price=lv.buy_price,
                    quantity=lv.quantity,
                )

        elif status == GridLevelStatus.FILLED:
            if current_price >= lv.sell_price:
                return GridAction(
                    level=lv.level,
                    action="place_sell",
                    side="sell",
                    price=lv.sell_price,
                    quantity=lv.quantity,
                )

        elif status == GridLevelStatus.TP_HIT:
            return GridAction(
                level=lv.level,
                action="place_buy",
                side="buy",
                price=lv.buy_price,
                quantity=lv.quantity,
            )

        elif status == GridLevelStatus.OPEN:
            pass

        return None

    def plan_initial(
        self,
        instance_id: str,
        current_price: Decimal,
    ) -> GridPlan:
        """Plan the initial set of orders when activating a grid.

        Places buy orders for all levels whose buy_price is below current_price.
        """
        levels = self._store.list_levels(instance_id)
        if not levels:
            return GridPlan()

        actions: list[GridAction] = []

        for lv in levels:
            if lv.status == GridLevelStatus.WAITING and current_price > lv.buy_price:
                actions.append(
                    GridAction(
                        level=lv.level,
                        action="place_buy",
                        side="buy",
                        price=lv.buy_price,
                        quantity=lv.quantity,
                    )
                )

        return GridPlan(actions=actions)

    def plan_cancel_all(self, instance_id: str) -> GridPlan:
        """Plan cancellation of all open orders."""
        levels = self._store.list_levels(instance_id)
        if not levels:
            return GridPlan()

        actions: list[GridAction] = []

        for lv in levels:
            if lv.status == GridLevelStatus.OPEN:
                order_id = lv.buy_order_id or lv.sell_order_id
                if order_id is not None:
                    actions.append(
                        GridAction(
                            level=lv.level,
                            action="cancel",
                            side="buy" if lv.buy_order_id else "sell",
                            price=lv.buy_price,
                            quantity=lv.quantity,
                            order_id=order_id,
                        )
                    )

        return GridPlan(actions=actions)
