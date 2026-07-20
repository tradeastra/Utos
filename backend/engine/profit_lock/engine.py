"""
ProfitLockEngine — orchestrates the entire profit lock lifecycle.

Key design constraints:
- Does NOT know about exchanges (Binance, Hyperliquid, etc.)
- Does NOT poll prices — receives price updates via on_price_update()
- Does NOT call Grid Engine — completely independent sibling engine
- Delegates all order operations to ExecutionEngine
- Tracks internal metrics for observability
"""

from __future__ import annotations

import time
import uuid
from decimal import Decimal

from core.domain_types import OrderSide, OrderType
from core.exceptions import ProfitLockError, ValidationError
from core.logging import get_logger

from engine.execution.execution_engine import ExecutionEngine
from engine.execution.models import OrderRequest
from engine.profit_lock.calculator import ProfitCalculator
from engine.profit_lock.policy import ProfitLockPolicy
from engine.profit_lock.state import (
    ProfitLockMetrics,
    ProfitLockState,
    ProfitLockStatus,
    ProfitLockStore,
)

logger = get_logger(__name__)


class ProfitLockEngine:
    """Orchestrates profit lock: monitoring, trailing, execution, and recovery."""

    def __init__(
        self,
        execution_engine: ExecutionEngine,
        calculator: ProfitCalculator | None = None,
        policy: ProfitLockPolicy | None = None,
        store: ProfitLockStore | None = None,
    ) -> None:
        self._exec = execution_engine
        self._calculator = calculator or ProfitCalculator()
        self._policy = policy or ProfitLockPolicy()
        self._store = store or ProfitLockStore()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def enable(
        self,
        instance_id: str,
        exchange_account_id: uuid.UUID,
        symbol: str,
        entry_price: Decimal,
        quantity: Decimal,
        side: str,
        trigger_percentage: Decimal,
        trail_percentage: Decimal,
        max_profit_percentage: Decimal = Decimal("0"),
    ) -> bool:
        """Enable profit lock for a trading instance.

        Args:
            max_profit_percentage: If > 0, auto-sell when profit reaches this %.
                                   0 means no cap (ride trend indefinitely).
        """
        if trigger_percentage <= 0:
            raise ValidationError(
                f"trigger_percentage must be > 0, got {trigger_percentage}"
            )
        if trail_percentage <= 0:
            raise ValidationError(
                f"trail_percentage must be > 0, got {trail_percentage}"
            )
        if trail_percentage >= 100:
            raise ValidationError(
                f"trail_percentage must be < 100, got {trail_percentage}"
            )

        state = ProfitLockState(
            instance_id=instance_id,
            status=ProfitLockStatus.MONITORING,
            enabled=True,
            trigger_percentage=trigger_percentage,
            trail_percentage=trail_percentage,
            max_profit_percentage=max_profit_percentage,
            entry_price=entry_price,
            quantity=quantity,
            side=side,
            highest_price=entry_price,
            lock_price=None,
            is_triggered=False,
            is_executed=False,
            exchange_account_id=exchange_account_id,
            symbol=symbol,
        )
        self._store.put(instance_id, state)
        logger.info(
            "Profit lock enabled",
            extra={
                "instance_id": instance_id,
                "trigger_percentage": str(trigger_percentage),
                "trail_percentage": str(trail_percentage),
                "entry_price": str(entry_price),
            },
        )
        return True

    async def disable(self, instance_id: str) -> bool:
        """Disable profit lock — cancel any lock orders and transition to DISABLED."""
        state = self._store.get(instance_id)
        if state is None:
            raise ProfitLockError(f"Profit lock not found for instance {instance_id}")

        # Cancel lock order if executing
        if state.status == ProfitLockStatus.EXECUTING and state.lock_order_id:
            try:
                await self._exec.cancel_order(state.exchange_account_id, state.lock_order_id)  # type: ignore[arg-type]
            except Exception as exc:
                logger.warning(f"Failed to cancel lock order: {exc}")
                self._store.get_metrics(instance_id).record_error()

        self._store.transition(instance_id, ProfitLockStatus.DISABLED)
        state.enabled = False
        state.is_triggered = False
        state.lock_order_id = None
        logger.info("Profit lock disabled", extra={"instance_id": instance_id})
        return True

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def on_price_update(self, instance_id: str, current_price: Decimal) -> None:
        """Handle a price update — evaluate policy and act on decision."""
        state = self._store.get(instance_id)
        if state is None or not state.enabled:
            return
        if state.status not in (
            ProfitLockStatus.MONITORING,
            ProfitLockStatus.TRIGGERED,
        ):
            return

        metrics = self._store.get_metrics(instance_id)
        metrics.record_event()

        start_time = time.monotonic()

        profit = self._calculator.calculate(
            entry_price=state.entry_price,
            current_price=current_price,
            quantity=state.quantity,
            side=state.side,
        )

        decision = self._policy.evaluate(current_price, profit, state)

        elapsed_ms = (time.monotonic() - start_time) * 1000
        metrics.record_decision(elapsed_ms)

        if decision.action == "none":
            return

        if decision.action == "trigger_lock":
            await self._handle_trigger(
                instance_id, current_price, decision.new_lock_price
            )
        elif decision.action == "update_lock":
            await self._handle_update(
                instance_id, current_price, decision.new_lock_price
            )
        elif decision.action == "execute_lock":
            await self._handle_execute(instance_id, decision.new_lock_price)

    async def on_position_update(
        self,
        instance_id: str,
        entry_price: Decimal,
        quantity: Decimal,
    ) -> None:
        """Handle position update — update entry price and quantity."""
        state = self._store.get(instance_id)
        if state is None:
            return
        self._store.update(instance_id, entry_price=entry_price, quantity=quantity)
        logger.info(
            "Position updated",
            extra={
                "instance_id": instance_id,
                "entry_price": str(entry_price),
                "quantity": str(quantity),
            },
        )

    async def on_order_filled(
        self,
        instance_id: str,
        order_id: str,
        fill_price: Decimal,
        quantity: Decimal,
    ) -> None:
        """Handle order filled — if it's the lock order, transition to LOCKED."""
        state = self._store.get(instance_id)
        if state is None:
            return
        if state.lock_order_id != order_id:
            return
        if state.status != ProfitLockStatus.EXECUTING:
            return

        self._store.transition(instance_id, ProfitLockStatus.LOCKED)
        state.is_executed = True
        state.lock_order_id = None
        self._store.get_metrics(instance_id).record_lock_executed()

        logger.info(
            "Profit lock executed",
            extra={
                "instance_id": instance_id,
                "fill_price": str(fill_price),
                "quantity": str(quantity),
            },
        )

    async def on_order_cancelled(self, instance_id: str, order_id: str) -> None:
        """Handle order cancelled — if it's the lock order, resume trailing."""
        state = self._store.get(instance_id)
        if state is None:
            return
        if state.lock_order_id != order_id:
            return
        if state.status != ProfitLockStatus.EXECUTING:
            return

        self._store.transition(instance_id, ProfitLockStatus.TRIGGERED)
        state.lock_order_id = None
        logger.info(
            "Lock order cancelled, resuming trailing",
            extra={"instance_id": instance_id},
        )

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    async def get_state(self, instance_id: str) -> ProfitLockState:
        state = self._store.get(instance_id)
        if state is None:
            raise ProfitLockError(f"Profit lock not found for instance {instance_id}")
        return state

    def get_metrics(self, instance_id: str) -> ProfitLockMetrics:
        return self._store.get_metrics(instance_id)

    # ------------------------------------------------------------------
    # Manual execution
    # ------------------------------------------------------------------

    async def execute_lock(self, instance_id: str, lock_price: Decimal) -> bool:
        """Manually execute profit lock — place sell order at lock_price."""
        state = self._store.get(instance_id)
        if state is None:
            raise ProfitLockError(f"Profit lock not found for instance {instance_id}")
        return await self._place_lock_order(instance_id, lock_price)

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------

    async def _handle_trigger(
        self,
        instance_id: str,
        current_price: Decimal,
        lock_price: Decimal | None,
    ) -> None:
        """Handle trigger_lock decision — transition to TRIGGERED, set lock price."""
        state = self._store.get(instance_id)
        if state is None or lock_price is None:
            return

        if state.status == ProfitLockStatus.MONITORING:
            self._store.transition(instance_id, ProfitLockStatus.TRIGGERED)

        state.is_triggered = True
        state.highest_price = max(state.highest_price or current_price, current_price)
        state.lock_price = lock_price
        self._store.get_metrics(instance_id).record_lock_triggered()

        logger.info(
            "Profit lock triggered",
            extra={
                "instance_id": instance_id,
                "lock_price": str(lock_price),
                "highest_price": str(state.highest_price),
            },
        )

    async def _handle_update(
        self,
        instance_id: str,
        current_price: Decimal,
        new_lock_price: Decimal | None,
    ) -> None:
        """Handle update_lock decision — trail lock price upward."""
        state = self._store.get(instance_id)
        if state is None or new_lock_price is None:
            return

        state.highest_price = max(state.highest_price or current_price, current_price)
        state.lock_price = new_lock_price

        logger.info(
            "Profit lock trailing update",
            extra={
                "instance_id": instance_id,
                "new_lock_price": str(new_lock_price),
                "highest_price": str(state.highest_price),
            },
        )

    async def _handle_execute(
        self,
        instance_id: str,
        lock_price: Decimal | None,
    ) -> None:
        """Handle execute_lock decision — place sell order via ExecutionEngine."""
        if lock_price is None:
            return
        await self._place_lock_order(instance_id, lock_price)

    async def _place_lock_order(self, instance_id: str, lock_price: Decimal) -> bool:
        """Place a sell order via ExecutionEngine to lock profit."""
        state = self._store.get(instance_id)
        if state is None:
            raise ProfitLockError(f"Profit lock not found for instance {instance_id}")

        self._store.transition(instance_id, ProfitLockStatus.EXECUTING)

        side = OrderSide.SELL if state.side == "long" else OrderSide.BUY
        request = OrderRequest(
            request_id=uuid.uuid4(),
            exchange_account_id=state.exchange_account_id,  # type: ignore[arg-type]
            symbol=state.symbol,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=state.quantity,
            price=lock_price,
        )

        try:
            result = await self._exec.place_order(request)
            state.lock_order_id = result.order_id
            logger.info(
                "Lock order placed",
                extra={
                    "instance_id": instance_id,
                    "order_id": result.order_id,
                    "lock_price": str(lock_price),
                },
            )
            return True
        except Exception as exc:
            self._store.transition(instance_id, ProfitLockStatus.ERROR)
            self._store.get_metrics(instance_id).record_error()
            logger.error(
                "Failed to place lock order",
                extra={"instance_id": instance_id, "error": str(exc)},
            )
            raise ProfitLockError(f"Failed to place lock order: {exc}") from exc
