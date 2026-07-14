"""
GridEngine — orchestrates the entire grid trading cycle.

Key design constraints:
- Does NOT know about exchanges (Binance, Hyperliquid, etc.)
- Does NOT poll prices — receives price updates via on_price_update()
- Delegates all order operations to ExecutionEngine
- Execution Engine remains stateless about strategies
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from core.exceptions import GridError, ValidationError
from core.logging import get_logger
from core.types import GridLevel, GridLevelStatus, GridState, OrderSide, OrderType
from engine.execution.execution_engine import ExecutionEngine
from engine.execution.models import OrderRequest
from engine.grid.calculator import GridCalculator
from engine.grid.planner import GridAction, GridPlanner
from engine.grid.state import GridStateStore, GridStateMachine, GridStatus

logger = get_logger(__name__)


class GridEngine:
    """Orchestrates grid trading: level calculation, order placement, fill handling."""

    def __init__(
        self,
        execution_engine: ExecutionEngine,
        calculator: GridCalculator | None = None,
        planner: GridPlanner | None = None,
        store: GridStateStore | None = None,
    ) -> None:
        self._exec = execution_engine
        self._calculator = calculator or GridCalculator()
        self._store = store or GridStateStore()
        self._planner = planner or GridPlanner(self._store)

    # ------------------------------------------------------------------
    # Grid lifecycle
    # ------------------------------------------------------------------

    async def initialize_grid(
        self,
        instance_id: str,
        exchange_account_id: uuid.UUID,
        symbol: str,
        upper_price: Decimal,
        lower_price: Decimal,
        grid_count: int,
        investment_per_grid: Decimal,
    ) -> GridState:
        """Initialize grid levels for a trading instance."""
        data = self._calculator.calculate_grid_state_data(
            upper_price, lower_price, grid_count, investment_per_grid
        )
        state = GridState(
            instance_id=instance_id,
            status=GridStatus.IDLE,
            upper_price=upper_price,
            lower_price=lower_price,
            grid_count=grid_count,
            grid_spacing=data["grid_spacing"],
            investment_per_grid=investment_per_grid,
            levels=data["levels"],
            exchange_account_id=exchange_account_id,
            symbol=symbol,
        )
        self._store.put(instance_id, state)
        self._store.transition_grid(instance_id, GridStatus.INITIALIZED)
        logger.info(
            "Grid initialized",
            extra={
                "instance_id": instance_id,
                "grid_count": grid_count,
                "upper_price": str(upper_price),
                "lower_price": str(lower_price),
            },
        )
        return self._store.get(instance_id)  # type: ignore[return-value]

    async def activate_grid(self, instance_id: str, current_price: Decimal) -> bool:
        """Activate grid: transition to ACTIVE and place initial buy orders."""
        state = self._store.get(instance_id)
        if state is None:
            raise GridError(f"Grid not found for instance {instance_id}")

        self._store.transition_grid(instance_id, GridStatus.ACTIVE)
        state.current_price = current_price

        plan = self._planner.plan_initial(instance_id, current_price)
        for action in plan.actions:
            await self._place_order(instance_id, action)

        logger.info(
            "Grid activated",
            extra={
                "instance_id": instance_id,
                "orders_placed": len(plan.actions),
                "current_price": str(current_price),
            },
        )
        return True

    async def pause_grid(self, instance_id: str) -> bool:
        """Pause grid: cancel all open orders and transition to PAUSED."""
        state = self._store.get(instance_id)
        if state is None:
            raise GridError(f"Grid not found for instance {instance_id}")

        plan = self._planner.plan_cancel_all(instance_id)
        for action in plan.actions:
            await self._cancel_order(instance_id, action)

        self._store.transition_grid(instance_id, GridStatus.PAUSED)
        logger.info(
            "Grid paused",
            extra={"instance_id": instance_id, "orders_cancelled": len(plan.actions)},
        )
        return True

    async def resume_grid(self, instance_id: str, current_price: Decimal) -> bool:
        """Resume grid: transition to ACTIVE and re-place orders."""
        state = self._store.get(instance_id)
        if state is None:
            raise GridError(f"Grid not found for instance {instance_id}")

        self._store.transition_grid(instance_id, GridStatus.ACTIVE)
        state.current_price = current_price

        plan = self._planner.plan(instance_id, current_price)
        for action in plan.actions:
            await self._place_order(instance_id, action)

        logger.info(
            "Grid resumed",
            extra={"instance_id": instance_id, "orders_placed": len(plan.actions)},
        )
        return True

    async def close_all_grid_orders(self, instance_id: str) -> bool:
        """Cancel all grid orders (does not change grid status)."""
        plan = self._planner.plan_cancel_all(instance_id)
        for action in plan.actions:
            await self._cancel_order(instance_id, action)
        logger.info(
            "All grid orders cancelled",
            extra={"instance_id": instance_id, "count": len(plan.actions)},
        )
        return True

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def on_price_update(self, instance_id: str, price: Decimal) -> None:
        """Handle a price update from Market Hub — place/cancel orders as needed."""
        state = self._store.get(instance_id)
        if state is None:
            return
        if state.status != GridStatus.ACTIVE:
            return

        state.current_price = price
        plan = self._planner.plan(instance_id, price)
        for action in plan.actions:
            if action.action == "cancel":
                await self._cancel_order(instance_id, action)
            else:
                await self._place_order(instance_id, action)

    async def on_buy_filled(
        self,
        instance_id: str,
        grid_level: int,
        fill_price: Decimal,
        quantity: Decimal,
    ) -> None:
        """Handle buy order filled — transition level and place sell order."""
        lv = self._store.get_level(instance_id, grid_level)
        if lv is None:
            raise GridError(f"Grid level {grid_level} not found for instance {instance_id}")

        self._store.transition_level(instance_id, grid_level, GridLevelStatus.FILLED)
        lv.buy_order_id = None

        state = self._store.get(instance_id)
        if state and state.status == GridStatus.ACTIVE:
            await self._place_order(
                instance_id,
                GridAction(
                    level=grid_level,
                    action="place_sell",
                    side="sell",
                    price=lv.sell_price,
                    quantity=lv.quantity,
                ),
            )

        logger.info(
            "Buy filled, sell order placed",
            extra={
                "instance_id": instance_id,
                "grid_level": grid_level,
                "fill_price": str(fill_price),
                "quantity": str(quantity),
            },
        )

    async def on_sell_filled(
        self,
        instance_id: str,
        grid_level: int,
        fill_price: Decimal,
        quantity: Decimal,
    ) -> None:
        """Handle sell order filled — transition level to TP_HIT, increment cycles."""
        lv = self._store.get_level(instance_id, grid_level)
        if lv is None:
            raise GridError(f"Grid level {grid_level} not found for instance {instance_id}")

        self._store.transition_level(instance_id, grid_level, GridLevelStatus.TP_HIT)
        lv.sell_order_id = None

        state = self._store.get(instance_id)
        if state is not None:
            state.total_cycles += 1
            profit = (fill_price - lv.buy_price) * quantity
            state.total_profit += profit

        if state and state.status == GridStatus.ACTIVE:
            self._store.transition_level(instance_id, grid_level, GridLevelStatus.WAITING)

        logger.info(
            "Sell filled, cycle complete",
            extra={
                "instance_id": instance_id,
                "grid_level": grid_level,
                "fill_price": str(fill_price),
                "quantity": str(quantity),
                "total_cycles": state.total_cycles if state else 0,
            },
        )

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    async def get_grid_state(self, instance_id: str) -> GridState:
        state = self._store.get(instance_id)
        if state is None:
            raise GridError(f"Grid not found for instance {instance_id}")
        return state

    async def get_grid_level(self, instance_id: str, level: int) -> GridLevel | None:
        return self._store.get_level(instance_id, level)

    async def get_grid_levels(self, instance_id: str) -> list[GridLevel]:
        return self._store.list_levels(instance_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _place_order(self, instance_id: str, action: GridAction) -> str:
        """Place an order via ExecutionEngine and update level state."""
        state = self._store.get(instance_id)
        if state is None:
            raise GridError(f"Grid not found for instance {instance_id}")

        side = OrderSide.BUY if action.side == "buy" else OrderSide.SELL
        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=state.exchange_account_id,  # type: ignore[arg-type]
            symbol=state.symbol,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=action.quantity,
            price=action.price,
        )
        result = await self._exec.place_order(request)

        if action.side == "buy":
            self._store.update_level(
                instance_id, action.level, buy_order_id=result.order_id
            )
        else:
            self._store.update_level(
                instance_id, action.level, sell_order_id=result.order_id
            )
        self._store.transition_level(instance_id, action.level, GridLevelStatus.OPEN)
        return result.order_id

    async def _cancel_order(self, instance_id: str, action: GridAction) -> None:
        """Cancel an order via ExecutionEngine and update level state."""
        state = self._store.get(instance_id)
        if state is None:
            raise GridError(f"Grid not found for instance {instance_id}")
        if action.order_id is None:
            return

        await self._exec.cancel_order(state.exchange_account_id, action.order_id)  # type: ignore[arg-type]

        if action.side == "buy":
            self._store.update_level(instance_id, action.level, buy_order_id=None)
        else:
            self._store.update_level(instance_id, action.level, sell_order_id=None)
        self._store.transition_level(instance_id, action.level, GridLevelStatus.CANCELLED)
