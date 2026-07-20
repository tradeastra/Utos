"""
ProfitLockPolicy — determines when the lock level should rise and when to execute.

Pure logic: produces a PolicyDecision. Does not place orders or modify state.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from engine.profit_lock.calculator import ProfitResult
from engine.profit_lock.state import ProfitLockState, ProfitLockStatus


@dataclass
class PolicyDecision:
    """Result of ProfitLockPolicy.evaluate()."""

    action: str  # "none", "update_lock", "trigger_lock", "execute_lock"
    new_lock_price: Decimal | None = None
    reason: str = ""


class ProfitLockPolicy:
    """Decide profit lock actions based on current price, profit, and state."""

    @staticmethod
    def evaluate(
        current_price: Decimal,
        profit: ProfitResult,
        state: ProfitLockState,
    ) -> PolicyDecision:
        """Evaluate the policy and return a decision.

        Logic:
        1. If not enabled or not monitoring/triggered → no action
        2. If max_profit_cap > 0 and profit % >= max_profit_cap → execute lock immediately
        3. If profit % < trigger_percentage → no action (still monitoring)
        4. If profit % >= trigger_percentage and not triggered → trigger lock
        5. If triggered and price makes new high → update lock_price (trailing)
        6. If triggered and price drops below lock_price → execute lock
        """
        if not state.enabled:
            return PolicyDecision(action="none", reason="profit lock not enabled")

        if state.status not in (
            ProfitLockStatus.MONITORING,
            ProfitLockStatus.TRIGGERED,
        ):
            return PolicyDecision(action="none", reason=f"status is {state.status}")

        # Check max profit cap — auto-execute if reached
        if state.max_profit_percentage > 0 and profit.profit_percentage >= state.max_profit_percentage:
            return PolicyDecision(
                action="execute_lock",
                new_lock_price=current_price,
                reason=f"profit {profit.profit_percentage}% >= max cap {state.max_profit_percentage}%",
            )

        # Update highest price if current price is higher
        if state.highest_price is None or current_price > state.highest_price:
            new_highest = current_price
        else:
            new_highest = state.highest_price

        # Check if trigger condition is met
        if state.status == ProfitLockStatus.MONITORING:
            if profit.profit_percentage >= state.trigger_percentage:
                lock_price = new_highest * (
                    Decimal("1") - state.trail_percentage / Decimal("100")
                )
                return PolicyDecision(
                    action="trigger_lock",
                    new_lock_price=lock_price,
                    reason=f"profit {profit.profit_percentage}% >= trigger {state.trigger_percentage}%",
                )
            return PolicyDecision(
                action="none",
                reason=f"profit {profit.profit_percentage}% < trigger {state.trigger_percentage}%",
            )

        # Status is TRIGGERED — check for trailing update or execution
        if state.status == ProfitLockStatus.TRIGGERED:
            # Update highest price and lock price if new high
            if new_highest > (state.highest_price or Decimal("0")):
                new_lock = new_highest * (
                    Decimal("1") - state.trail_percentage / Decimal("100")
                )
                if state.lock_price is None or new_lock > state.lock_price:
                    return PolicyDecision(
                        action="update_lock",
                        new_lock_price=new_lock,
                        reason=f"new high {new_highest}, lock updated to {new_lock}",
                    )

            # Check if price dropped below lock price
            if state.lock_price is not None and current_price <= state.lock_price:
                return PolicyDecision(
                    action="execute_lock",
                    new_lock_price=state.lock_price,
                    reason=f"price {current_price} <= lock {state.lock_price}",
                )

            return PolicyDecision(action="none", reason="price within lock range")

        return PolicyDecision(action="none", reason="no action")

    @staticmethod
    def compute_lock_price(
        highest_price: Decimal,
        trail_percentage: Decimal,
    ) -> Decimal:
        """Compute lock price from highest price and trail percentage."""
        return highest_price * (Decimal("1") - trail_percentage / Decimal("100"))
