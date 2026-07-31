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

from core.domain_types import (
    GridLevel,
    GridLevelStatus,
    GridState,
    OrderSide,
    OrderType,
)
from core.exceptions import GridError
from core.logging import get_logger

from engine.execution.execution_engine import ExecutionEngine
from engine.execution.models import OrderRequest
from engine.grid.calculator import GridCalculator
from engine.grid.circuit_breaker import BreakerResumeMode, CircuitBreakerState
from engine.grid.planner import GridAction, GridPlanner
from engine.grid.state import GridStateStore, GridStatus
from engine.profit_lock.engine import ProfitLockEngine

logger = get_logger(__name__)


class GridEngine:
    """Orchestrates grid trading: level calculation, order placement, fill handling."""

    def __init__(
        self,
        execution_engine: ExecutionEngine,
        calculator: GridCalculator | None = None,
        planner: GridPlanner | None = None,
        store: GridStateStore | None = None,
        profit_lock_engine: ProfitLockEngine | None = None,
    ) -> None:
        self._exec = execution_engine
        self._calculator = calculator or GridCalculator()
        self._store = store or GridStateStore()
        self._planner = planner or GridPlanner(self._store)
        self._profit_lock = profit_lock_engine
        self._trailing_config: dict[str, dict[str, Decimal]] = {}
        self._ta_configs: dict[str, list[dict]] = {}
        self._ta_candles: dict[str, list[dict]] = {}
        # Circuit breaker state per instance (daily drop protection).
        self._breakers: dict[str, CircuitBreakerState] = {}
        # 15m candle cache per instance, used while the breaker is active.
        self._ta_candles_15m: dict[str, list[dict]] = {}

    # ------------------------------------------------------------------
    # Trailing profit configuration
    # ------------------------------------------------------------------

    def configure_trailing_profit(
        self,
        instance_id: str,
        trigger_percentage: Decimal,
        trail_percentage: Decimal,
        max_profit_percentage: Decimal = Decimal("0"),
    ) -> None:
        """Configure trailing profit for a grid instance.

        When enabled, every buy-filled level will automatically activate
        ProfitLockEngine to trail the price upward and lock in profit.

        Args:
            max_profit_percentage: If > 0, auto-sell when profit reaches this %.
                                   0 means no cap (ride trend indefinitely).
        """
        self._trailing_config[instance_id] = {
            "trigger_percentage": trigger_percentage,
            "trail_percentage": trail_percentage,
            "max_profit_percentage": max_profit_percentage,
        }
        logger.info(
            "Trailing profit configured",
            extra={
                "instance_id": instance_id,
                "trigger_percentage": str(trigger_percentage),
                "trail_percentage": str(trail_percentage),
                "max_profit_percentage": str(max_profit_percentage),
            },
        )

    # ------------------------------------------------------------------
    # TA configuration
    # ------------------------------------------------------------------

    def configure_ta(
        self,
        instance_id: str,
        configs: list[dict],
    ) -> None:
        """Set TA indicator configs for a trading instance.

        When configs is empty or None, the TA gate is disabled (all orders pass).
        """
        if configs:
            self._ta_configs[instance_id] = configs
        else:
            self._ta_configs.pop(instance_id, None)
        logger.info(
            "TA configs updated",
            extra={
                "instance_id": instance_id,
                "indicator_count": len(configs) if configs else 0,
            },
        )

    def update_ta_candles(
        self,
        instance_id: str,
        candles: list[dict],
    ) -> None:
        """Update cached candle data for TA evaluation."""
        self._ta_candles[instance_id] = candles

    # ------------------------------------------------------------------
    # Circuit breaker configuration
    # ------------------------------------------------------------------

    def configure_circuit_breaker(
        self,
        instance_id: str,
        critical_threshold: Decimal,
        min_continuation_rate: Decimal = Decimal("0.80"),
        resume_mode: BreakerResumeMode = BreakerResumeMode.TA_CONFIRM,
        recovery_pct: Decimal | None = None,
        widen_multiplier: Decimal | None = None,
        day_open_price: Decimal | None = None,
        ta_15m_configs: list[dict] | None = None,
    ) -> None:
        """Install a daily drop circuit breaker for a grid instance.

        Args:
            instance_id: Trading instance id.
            critical_threshold: Intraday drop % (positive number) that triggers
                the breaker — derived from DailyDropAnalyzer.
            min_continuation_rate: Continuation rate used to derive the
                threshold (kept for audit/logging).
            resume_mode: What the bot does after the breaker triggers. See
                ``BreakerResumeMode``. Defaults to ``TA_CONFIRM`` (legacy:
                wait for 15m TA reversal). Alternatives:
                - ``WIDEN_STEP``: keep buying but with grid step × multiplier.
                - ``TRAILING_BUY``: stop buys, resume after price recovers
                  ``recovery_pct`` from the intraday low.
            recovery_pct: For ``TRAILING_BUY`` mode — % recovery from the low
                required to resume (defaults to 5.0%).
            widen_multiplier: For ``WIDEN_STEP`` mode — grid step multiplier
                while active (defaults to 2 = 2× wider spacing).
            day_open_price: Price at the start of the current UTC day. If
                ``None``, the next price update will seed it.
            ta_15m_configs: Optional override for the reversal-confirmation TA
                configs (only used by ``TA_CONFIRM`` mode; defaults to
                RSI<30 AND MACD bullish cross on 15m).
        """
        from engine.grid.circuit_breaker import DEFAULT_RECOVERY_PCT, DEFAULT_WIDEN_MULTIPLIER
        breaker = CircuitBreakerState(
            instance_id=instance_id,
            critical_threshold=critical_threshold,
            min_continuation_rate=min_continuation_rate,
            resume_mode=resume_mode,
            recovery_pct=recovery_pct if recovery_pct is not None else DEFAULT_RECOVERY_PCT,
            widen_multiplier=widen_multiplier if widen_multiplier is not None else DEFAULT_WIDEN_MULTIPLIER,
            day_open_price=day_open_price,
            ta_15m_configs=ta_15m_configs or [],
        )
        self._breakers[instance_id] = breaker
        logger.info(
            "Circuit breaker configured",
            extra={
                "instance_id": instance_id,
                "critical_threshold": str(critical_threshold),
                "min_continuation_rate": str(min_continuation_rate),
                "resume_mode": resume_mode.value,
                "recovery_pct": str(breaker.recovery_pct),
                "widen_multiplier": str(breaker.widen_multiplier),
                "day_open": str(day_open_price) if day_open_price else "pending",
            },
        )

    def update_ta_candles_15m(
        self,
        instance_id: str,
        candles: list[dict],
    ) -> None:
        """Update the 15m candle cache used while the breaker is active."""
        self._ta_candles_15m[instance_id] = candles

    def get_circuit_breaker(self, instance_id: str) -> CircuitBreakerState | None:
        """Return the breaker state for an instance (or ``None`` if none)."""
        return self._breakers.get(instance_id)

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
        averaging_steps: list[dict] | None = None,
    ) -> GridState:
        """Initialize grid levels for a trading instance.

        If ``averaging_steps`` is provided, levels are generated using per-step
        drop rates from the averaging config instead of evenly-spaced grid.
        In that case, ``upper_price`` is used as ``start_price`` and
        ``lower_price``/``grid_count`` are derived from the steps.
        """
        if averaging_steps:
            data = self._calculator.calculate_grid_state_data_with_averaging(
                start_price=upper_price,
                investment_per_grid=investment_per_grid,
                averaging_steps=averaging_steps,
            )
            actual_grid_count = len(data["levels"])
            actual_lower = data["levels"][-1].buy_price
        else:
            data = self._calculator.calculate_grid_state_data(
                upper_price, lower_price, grid_count, investment_per_grid
            )
            actual_grid_count = grid_count
            actual_lower = lower_price

        state = GridState(
            instance_id=instance_id,
            status=GridStatus.IDLE,
            upper_price=upper_price,
            lower_price=actual_lower,
            grid_count=actual_grid_count,
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
                "grid_count": actual_grid_count,
                "upper_price": str(upper_price),
                "lower_price": str(actual_lower),
                "averaging": averaging_steps is not None,
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
        """Handle a price update from Market Hub — place/cancel orders and forward to profit lock.

        The daily drop circuit breaker (if configured) is evaluated first:
          - On a new UTC day the breaker is rolled over and ``day_open`` is set.
          - If intraday drop reaches the critical threshold, the breaker
            triggers: pending buys are cancelled and no new buys are placed.
            Sells on already-filled levels still proceed.
          - While triggered, buys are only allowed after the 15m TA reversal
            gate (RSI<30 AND MACD bullish cross by default) passes. On pass,
            the breaker resets and the grid resumes normal operation.
        """
        state = self._store.get(instance_id)
        if state is None:
            return
        if state.status != GridStatus.ACTIVE:
            return

        state.current_price = price

        # ── Circuit breaker: day rollover & trigger check ──────────────
        breaker = self._breakers.get(instance_id)
        breaker_just_triggered = False
        if breaker is not None:
            breaker.check_new_day(price)
            if breaker.should_trigger(price):
                breaker.trigger(price)
                breaker_just_triggered = True
                # Cancel every pending buy so we stop averaging into the drop.
                await self._cancel_all_pending_buys(instance_id)

        # Pass breaker context to the planner so WIDEN_STEP mode can skip
        # buy levels (widen the grid spacing) while the breaker is active.
        breaker_active = breaker is not None and breaker.triggered
        widen_mult = (
            breaker.widen_multiplier
            if breaker_active
            and breaker.resume_mode == BreakerResumeMode.WIDEN_STEP
            else Decimal("1")
        )
        plan = self._planner.plan(
            instance_id,
            price,
            breaker_active=breaker_active,
            widen_multiplier=widen_mult,
        )

        # ── TA gate / resume logic ────────────────────────────────────
        # While the breaker is active, the resume behavior depends on its
        # ``resume_mode``:
        #   - TA_CONFIRM: override the TA gate with the 15m reversal-confirmation
        #     configs. A pass resets the breaker and allows exactly one buy at
        #     the current price; the grid then resumes normally.
        #   - WIDEN_STEP: do NOT block buys — keep placing buys but with the
        #     grid step widened by ``widen_multiplier``. The breaker stays
        #     triggered (so the widened step remains in effect) until TA 15m
        #     confirms a reversal OR a new UTC day rolls over.
        #   - TRAILING_BUY: block buys until price recovers ``recovery_pct``
        #     from the intraday low. On recovery, reset the breaker and resume.
        ta_configs = self._ta_configs.get(instance_id)
        ta_candles = self._ta_candles.get(instance_id)
        ta_gate_passed = True

        if breaker is not None and breaker.triggered:
            # Track the intraday low for TRAILING_BUY mode (cheap to always do).
            breaker.update_bottom(price)

            if breaker.resume_mode == BreakerResumeMode.WIDEN_STEP:
                # Keep buying — do not block. The widened step is applied by
                # the planner when it sees the breaker is active (TODO: planner
                # integration). For now, buys proceed normally; the breaker
                # resets only on TA 15m confirmation or new day.
                ta_gate_passed = True
                # Still try TA 15m to reset the breaker (back to normal step).
                from services.ta_engine import TAEngine
                ta_engine = TAEngine()
                breaker_configs = breaker.get_ta_15m_configs()
                breaker_candles = self._ta_candles_15m.get(instance_id)
                if breaker_configs and breaker_candles:
                    ta_result = ta_engine.evaluate(breaker_configs, breaker_candles, price)
                    if ta_result.passed:
                        breaker.reset()
                        logger.info(
                            "Circuit breaker cleared by TA 15m (WIDEN_STEP → normal step)",
                            extra={
                                "instance_id": instance_id,
                                "price": str(price),
                                "ta_summary": ta_result.summary,
                            },
                        )
            elif breaker.resume_mode == BreakerResumeMode.TRAILING_BUY:
                # Block buys until price recovers recovery_pct from the low.
                if breaker.should_resume_trailing(price):
                    breaker.reset()
                    ta_gate_passed = True
                    logger.info(
                        "Circuit breaker cleared by trailing recovery",
                        extra={
                            "instance_id": instance_id,
                            "price": str(price),
                            "bottom_price": str(breaker.bottom_price),
                            "recovery_pct": str(breaker.recovery_pct),
                        },
                    )
                else:
                    ta_gate_passed = False
                    logger.debug(
                        "Circuit breaker active (TRAILING_BUY) — waiting for recovery",
                        extra={
                            "instance_id": instance_id,
                            "price": str(price),
                            "bottom_price": str(breaker.bottom_price)
                            if breaker.bottom_price
                            else "none",
                        },
                    )
            else:  # BreakerResumeMode.TA_CONFIRM (default / legacy)
                from services.ta_engine import TAEngine
                ta_engine = TAEngine()
                breaker_configs = breaker.get_ta_15m_configs()
                breaker_candles = self._ta_candles_15m.get(instance_id)
                if breaker_configs and breaker_candles:
                    ta_result = ta_engine.evaluate(breaker_configs, breaker_candles, price)
                    ta_gate_passed = ta_result.passed
                    if ta_gate_passed:
                        # Reversal confirmed — clear the breaker, resume normal grid.
                        breaker.reset()
                        logger.info(
                            "Circuit breaker cleared by TA 15m confirmation",
                            extra={
                                "instance_id": instance_id,
                                "price": str(price),
                                "ta_summary": ta_result.summary,
                            },
                        )
                    else:
                        logger.info(
                            "Circuit breaker active — TA 15m gate blocked buy",
                            extra={
                                "instance_id": instance_id,
                                "ta_summary": ta_result.summary,
                            },
                        )
                else:
                    # No 15m candles available yet — stay protected, block buys.
                    ta_gate_passed = False
                    logger.debug(
                        "Circuit breaker active — no 15m candles, buys blocked",
                        extra={"instance_id": instance_id},
                    )
        elif ta_configs and ta_candles:
            from services.ta_engine import TAEngine
            ta_engine = TAEngine()
            ta_result = ta_engine.evaluate(ta_configs, ta_candles, price)
            ta_gate_passed = ta_result.passed
            if not ta_gate_passed:
                logger.info(
                    "TA gate blocked order placement",
                    extra={
                        "instance_id": instance_id,
                        "ta_summary": ta_result.summary,
                    },
                )

        # ── Execute plan ───────────────────────────────────────────────
        # When the breaker just triggered we already cancelled pending buys;
        # skip placing new buys this tick (sells from the plan still run).
        for action in plan.actions:
            if action.action == "cancel":
                await self._cancel_order(instance_id, action)
            elif action.action == "place_buy":
                if breaker_just_triggered or not ta_gate_passed:
                    logger.debug(
                        "Buy skipped (breaker/TA gate)",
                        extra={
                            "instance_id": instance_id,
                            "level": action.level,
                            "breaker_just_triggered": breaker_just_triggered,
                            "ta_gate_passed": ta_gate_passed,
                        },
                    )
                    continue
                await self._place_order(instance_id, action)
            else:
                await self._place_order(instance_id, action)

        # Forward price update to ProfitLockEngine for all active lock keys
        if self._profit_lock and instance_id in self._trailing_config:
            for lv in self._store.list_levels(instance_id):
                if lv.status == GridLevelStatus.FILLED:
                    lock_key = f"{instance_id}:level:{lv.level}"
                    try:
                        await self._profit_lock.on_price_update(lock_key, price)
                    except Exception as exc:
                        logger.warning(
                            f"ProfitLock price update failed for level {lv.level}: {exc}",
                            extra={"instance_id": instance_id, "grid_level": lv.level},
                        )

    async def _cancel_all_pending_buys(self, instance_id: str) -> None:
        """Cancel every WAITING grid level's open buy order for an instance."""
        state = self._store.get(instance_id)
        if state is None:
            return
        exchange_account_id = state.exchange_account_id
        levels = self._store.list_levels(instance_id)
        for lv in levels:
            if lv.status == GridLevelStatus.WAITING and lv.buy_order_id:
                try:
                    await self._exec.cancel_order(
                        exchange_account_id, lv.buy_order_id
                    )
                    lv.buy_order_id = None
                    logger.info(
                        "Cancelled pending buy (circuit breaker)",
                        extra={
                            "instance_id": instance_id,
                            "level": lv.level,
                        },
                    )
                except Exception as exc:
                    logger.warning(
                        f"Failed to cancel pending buy for level {lv.level}: {exc}",
                        extra={"instance_id": instance_id, "level": lv.level},
                    )

    async def on_buy_filled(
        self,
        instance_id: str,
        grid_level: int,
        fill_price: Decimal,
        quantity: Decimal,
    ) -> None:
        """Handle buy order filled — transition level, place sell order, enable trailing profit."""
        lv = self._store.get_level(instance_id, grid_level)
        if lv is None:
            raise GridError(
                f"Grid level {grid_level} not found for instance {instance_id}"
            )

        self._store.transition_level(instance_id, grid_level, GridLevelStatus.FILLED)
        lv.buy_order_id = None

        state = self._store.get(instance_id)
        trailing = self._trailing_config.get(instance_id)

        # If trailing profit is active, skip grid sell — trailing will handle exit
        if state and state.status == GridStatus.ACTIVE and not trailing:
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

        # Auto-enable trailing profit if configured
        if trailing and self._profit_lock and state:
            lock_key = f"{instance_id}:level:{grid_level}"
            try:
                await self._profit_lock.enable(
                    instance_id=lock_key,
                    exchange_account_id=state.exchange_account_id,
                    symbol=state.symbol,
                    entry_price=fill_price,
                    quantity=quantity,
                    side="long",
                    trigger_percentage=trailing["trigger_percentage"],
                    trail_percentage=trailing["trail_percentage"],
                    max_profit_percentage=trailing.get("max_profit_percentage", Decimal("0")),
                )
                logger.info(
                    "Trailing profit auto-enabled for grid level",
                    extra={
                        "instance_id": instance_id,
                        "grid_level": grid_level,
                        "lock_key": lock_key,
                        "fill_price": str(fill_price),
                    },
                )
            except Exception as exc:
                logger.warning(
                    f"Failed to enable trailing profit for level {grid_level}: {exc}",
                    extra={"instance_id": instance_id, "grid_level": grid_level},
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
        """Handle sell order filled — transition level to TP_HIT, increment cycles, disable trailing."""
        lv = self._store.get_level(instance_id, grid_level)
        if lv is None:
            raise GridError(
                f"Grid level {grid_level} not found for instance {instance_id}"
            )

        self._store.transition_level(instance_id, grid_level, GridLevelStatus.TP_HIT)
        lv.sell_order_id = None

        # Disable profit lock for this level (position is closed)
        if self._profit_lock:
            lock_key = f"{instance_id}:level:{grid_level}"
            try:
                pl_state = self._profit_lock.get_state(lock_key)
                if pl_state.enabled:
                    await self._profit_lock.disable(lock_key)
                    logger.info(
                        "Profit lock disabled after sell filled",
                        extra={
                            "instance_id": instance_id,
                            "grid_level": grid_level,
                            "lock_key": lock_key,
                        },
                    )
            except Exception:
                pass  # profit lock may not exist for this level

        state = self._store.get(instance_id)
        if state is not None:
            state.total_cycles += 1
            profit = (fill_price - lv.buy_price) * quantity
            state.total_profit += profit

        if state and state.status == GridStatus.ACTIVE:
            self._store.transition_level(
                instance_id, grid_level, GridLevelStatus.WAITING
            )

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
    # Force operations (manual override)
    # ------------------------------------------------------------------

    async def force_buy(
        self,
        instance_id: str,
        level: int | None = None,
        price: Decimal | None = None,
        quantity: Decimal | None = None,
    ) -> dict:
        """Manually place a buy order, bypassing the planner.

        Spot market logic:
        - If level is specified, buy at that level's configured buy_price (or override with price).
        - If level is None, find the next WAITING level below current price and buy there.
        - After the forced buy fills, the grid continues averaging automatically:
          subsequent levels will place buy orders as price drops per the averaging config.

        Args:
            instance_id: Trading instance ID
            level: Optional grid level to force buy at (0-indexed)
            price: Optional override price (defaults to level's buy_price or current market price)
            quantity: Optional override quantity (defaults to level's configured quantity)

        Returns:
            dict with order_id, level, price, quantity
        """
        state = self._store.get(instance_id)
        if state is None:
            raise GridError(f"Grid not found for instance {instance_id}")
        if state.status != GridStatus.ACTIVE:
            raise GridError(
                f"Grid must be ACTIVE to force buy, current status: {state.status}"
            )

        # Determine target level
        if level is not None:
            lv = self._store.get_level(instance_id, level)
            if lv is None:
                raise GridError(f"Grid level {level} not found for instance {instance_id}")
            if lv.status == GridLevelStatus.FILLED:
                raise GridError(
                    f"Level {level} already has a filled position — cannot force buy again"
                )
        else:
            # Find next waiting level below current price
            lv = None
            for candidate in self._store.list_levels(instance_id):
                if (
                    candidate.status == GridLevelStatus.WAITING
                    and candidate.buy_price < state.current_price
                ):
                    lv = candidate
                    level = candidate.level
                    break
            if lv is None:
                raise GridError(
                    f"No waiting level below current price {state.current_price} to force buy"
                )

        # Determine price and quantity
        buy_price = price if price is not None else lv.buy_price
        buy_qty = quantity if quantity is not None else lv.quantity

        # Cancel existing buy order at this level if any
        if lv.buy_order_id is not None:
            try:
                await self._exec.cancel_order(state.exchange_account_id, lv.buy_order_id)
            except Exception as exc:
                logger.warning(
                    f"Failed to cancel existing buy order at level {level}: {exc}",
                    extra={"instance_id": instance_id, "grid_level": level},
                )

        # Place the buy order
        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=state.exchange_account_id,
            symbol=state.symbol,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=buy_qty,
            price=buy_price,
        )
        result = await self._exec.place_order(request)

        self._store.update_level(instance_id, level, buy_order_id=result.order_id)
        self._store.transition_level(instance_id, level, GridLevelStatus.OPEN)

        logger.info(
            "Force buy placed",
            extra={
                "instance_id": instance_id,
                "grid_level": level,
                "price": str(buy_price),
                "quantity": str(buy_qty),
                "order_id": result.order_id,
            },
        )

        return {
            "order_id": result.order_id,
            "level": level,
            "price": str(buy_price),
            "quantity": str(buy_qty),
            "side": "buy",
            "message": "Force buy placed. Averaging will continue automatically for subsequent levels.",
        }

    async def force_sell(
        self,
        instance_id: str,
        level: int | None = None,
        price: Decimal | None = None,
        quantity: Decimal | None = None,
    ) -> dict:
        """Manually sell an existing position, bypassing the planner.

        Spot market logic:
        - Can only sell levels that have a FILLED status (i.e., we hold the coin).
        - If level is specified, sell that level's position.
        - If level is None, sell ALL filled positions (close all).
        - If quantity is specified, sell partial; otherwise sell the full level quantity.
        - After sell, the level resets to WAITING so it can buy again on the next drop.

        Args:
            instance_id: Trading instance ID
            level: Optional grid level to force sell (must be FILLED)
            price: Optional override price (defaults to current market price)
            quantity: Optional partial quantity (defaults to full position)

        Returns:
            dict with order_ids, levels_sold, total_quantity, total_value
        """
        state = self._store.get(instance_id)
        if state is None:
            raise GridError(f"Grid not found for instance {instance_id}")
        if state.status != GridStatus.ACTIVE:
            raise GridError(
                f"Grid must be ACTIVE to force sell, current status: {state.status}"
            )

        sell_price = price if price is not None else state.current_price
        levels_to_sell: list[GridLevel] = []

        if level is not None:
            lv = self._store.get_level(instance_id, level)
            if lv is None:
                raise GridError(f"Grid level {level} not found for instance {instance_id}")
            if lv.status != GridLevelStatus.FILLED:
                raise GridError(
                    f"Level {level} is not FILLED (status: {lv.status.value}) — "
                    "cannot force sell a position that doesn't exist (spot market)"
                )
            levels_to_sell.append(lv)
        else:
            # Sell all filled positions
            for lv in self._store.list_levels(instance_id):
                if lv.status == GridLevelStatus.FILLED:
                    levels_to_sell.append(lv)
            if not levels_to_sell:
                raise GridError(
                    "No filled positions to sell — force sell only works on existing holdings (spot market)"
                )

        order_ids: list[str] = []
        total_qty = Decimal("0")
        total_value = Decimal("0")

        for lv in levels_to_sell:
            sell_qty = quantity if quantity is not None else lv.quantity
            if sell_qty > lv.quantity:
                sell_qty = lv.quantity  # Can't sell more than we hold

            # Cancel existing sell order at this level if any
            if lv.sell_order_id is not None:
                try:
                    await self._exec.cancel_order(
                        state.exchange_account_id, lv.sell_order_id
                    )
                except Exception as exc:
                    logger.warning(
                        f"Failed to cancel existing sell order at level {lv.level}: {exc}",
                        extra={"instance_id": instance_id, "grid_level": lv.level},
                    )

            request = OrderRequest(
                request_id=uuid.uuid4(),
                exchange_account_id=state.exchange_account_id,
                symbol=state.symbol,
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                quantity=sell_qty,
                price=sell_price,
            )
            result = await self._exec.place_order(request)
            order_ids.append(result.order_id)
            total_qty += sell_qty
            total_value += sell_qty * sell_price

            self._store.update_level(instance_id, lv.level, sell_order_id=result.order_id)

            logger.info(
                "Force sell placed",
                extra={
                    "instance_id": instance_id,
                    "grid_level": lv.level,
                    "price": str(sell_price),
                    "quantity": str(sell_qty),
                    "order_id": result.order_id,
                },
            )

        return {
            "order_ids": order_ids,
            "levels_sold": [lv.level for lv in levels_to_sell],
            "price": str(sell_price),
            "total_quantity": str(total_qty),
            "total_value": str(total_value),
            "side": "sell",
            "message": f"Force sell placed for {len(levels_to_sell)} level(s). "
                       "Levels will reset to WAITING after fill.",
        }

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
        self._store.transition_level(
            instance_id, action.level, GridLevelStatus.CANCELLED
        )
