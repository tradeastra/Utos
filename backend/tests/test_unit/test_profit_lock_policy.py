"""
Unit tests for ProfitLockPolicy.
"""

from decimal import Decimal

import pytest

from engine.profit_lock.calculator import ProfitCalculator, ProfitResult
from engine.profit_lock.policy import PolicyDecision, ProfitLockPolicy
from engine.profit_lock.state import ProfitLockState, ProfitLockStatus


def _make_state(
    status: str = ProfitLockStatus.MONITORING,
    trigger_percentage: Decimal = Decimal("10"),
    trail_percentage: Decimal = Decimal("5"),
    highest_price: Decimal | None = Decimal("100"),
    lock_price: Decimal | None = None,
    is_triggered: bool = False,
) -> ProfitLockState:
    return ProfitLockState(
        instance_id="inst-1",
        status=status,
        enabled=True,
        trigger_percentage=trigger_percentage,
        trail_percentage=trail_percentage,
        entry_price=Decimal("100"),
        quantity=Decimal("2"),
        side="long",
        highest_price=highest_price,
        lock_price=lock_price,
        is_triggered=is_triggered,
    )


def _make_profit(percentage: Decimal, current_price: Decimal) -> ProfitResult:
    return ProfitResult(
        floating_profit=Decimal("20"),
        profit_percentage=percentage,
        is_profitable=percentage > 0,
        entry_price=Decimal("100"),
        current_price=current_price,
        quantity=Decimal("2"),
    )


class TestProfitLockPolicyMonitoring:

    def test_no_action_when_profit_below_trigger(self) -> None:
        state = _make_state()
        profit = _make_profit(Decimal("5"), Decimal("105"))
        decision = ProfitLockPolicy.evaluate(Decimal("105"), profit, state)
        assert decision.action == "none"

    def test_trigger_lock_when_profit_exceeds_trigger(self) -> None:
        state = _make_state(trigger_percentage=Decimal("10"), trail_percentage=Decimal("5"))
        profit = _make_profit(Decimal("12"), Decimal("112"))
        decision = ProfitLockPolicy.evaluate(Decimal("112"), profit, state)
        assert decision.action == "trigger_lock"
        assert decision.new_lock_price is not None
        # lock = 112 * (1 - 5/100) = 112 * 0.95 = 106.4
        assert decision.new_lock_price == Decimal("112") * Decimal("0.95")

    def test_trigger_lock_at_exact_trigger(self) -> None:
        state = _make_state(trigger_percentage=Decimal("10"))
        profit = _make_profit(Decimal("10"), Decimal("110"))
        decision = ProfitLockPolicy.evaluate(Decimal("110"), profit, state)
        assert decision.action == "trigger_lock"

    def test_no_action_when_disabled(self) -> None:
        state = _make_state()
        state.enabled = False
        profit = _make_profit(Decimal("20"), Decimal("120"))
        decision = ProfitLockPolicy.evaluate(Decimal("120"), profit, state)
        assert decision.action == "none"


class TestProfitLockPolicyTriggered:

    def test_update_lock_on_new_high(self) -> None:
        state = _make_state(
            status=ProfitLockStatus.TRIGGERED,
            highest_price=Decimal("110"),
            lock_price=Decimal("104.5"),  # 110 * 0.95
            is_triggered=True,
        )
        profit = _make_profit(Decimal("15"), Decimal("115"))
        decision = ProfitLockPolicy.evaluate(Decimal("115"), profit, state)
        assert decision.action == "update_lock"
        # new lock = 115 * 0.95 = 109.25
        assert decision.new_lock_price == Decimal("115") * Decimal("0.95")

    def test_no_update_when_price_below_high(self) -> None:
        state = _make_state(
            status=ProfitLockStatus.TRIGGERED,
            highest_price=Decimal("115"),
            lock_price=Decimal("109.25"),
            is_triggered=True,
        )
        profit = _make_profit(Decimal("12"), Decimal("112"))
        decision = ProfitLockPolicy.evaluate(Decimal("112"), profit, state)
        assert decision.action == "none"

    def test_execute_lock_when_price_drops_below_lock(self) -> None:
        state = _make_state(
            status=ProfitLockStatus.TRIGGERED,
            highest_price=Decimal("115"),
            lock_price=Decimal("109.25"),
            is_triggered=True,
        )
        profit = _make_profit(Decimal("8"), Decimal("108"))
        decision = ProfitLockPolicy.evaluate(Decimal("108"), profit, state)
        assert decision.action == "execute_lock"
        assert decision.new_lock_price == Decimal("109.25")

    def test_execute_lock_at_exact_lock_price(self) -> None:
        state = _make_state(
            status=ProfitLockStatus.TRIGGERED,
            highest_price=Decimal("115"),
            lock_price=Decimal("109.25"),
            is_triggered=True,
        )
        profit = _make_profit(Decimal("9.25"), Decimal("109.25"))
        decision = ProfitLockPolicy.evaluate(Decimal("109.25"), profit, state)
        assert decision.action == "execute_lock"

    def test_no_action_when_price_above_lock_but_below_high(self) -> None:
        state = _make_state(
            status=ProfitLockStatus.TRIGGERED,
            highest_price=Decimal("115"),
            lock_price=Decimal("109.25"),
            is_triggered=True,
        )
        profit = _make_profit(Decimal("10"), Decimal("110"))
        decision = ProfitLockPolicy.evaluate(Decimal("110"), profit, state)
        assert decision.action == "none"


class TestProfitLockPolicyComputeLockPrice:

    def test_compute_lock_price(self) -> None:
        lock = ProfitLockPolicy.compute_lock_price(Decimal("100"), Decimal("5"))
        assert lock == Decimal("95")

    def test_compute_lock_price_zero_trail(self) -> None:
        lock = ProfitLockPolicy.compute_lock_price(Decimal("100"), Decimal("0"))
        assert lock == Decimal("100")

    def test_compute_lock_price_50_percent(self) -> None:
        lock = ProfitLockPolicy.compute_lock_price(Decimal("200"), Decimal("50"))
        assert lock == Decimal("100")


class TestProfitLockPolicyNonActiveStates:

    def test_no_action_when_disabled_status(self) -> None:
        state = _make_state(status=ProfitLockStatus.DISABLED)
        profit = _make_profit(Decimal("20"), Decimal("120"))
        decision = ProfitLockPolicy.evaluate(Decimal("120"), profit, state)
        assert decision.action == "none"

    def test_no_action_when_executing(self) -> None:
        state = _make_state(status=ProfitLockStatus.EXECUTING)
        profit = _make_profit(Decimal("20"), Decimal("120"))
        decision = ProfitLockPolicy.evaluate(Decimal("120"), profit, state)
        assert decision.action == "none"

    def test_no_action_when_locked(self) -> None:
        state = _make_state(status=ProfitLockStatus.LOCKED)
        profit = _make_profit(Decimal("20"), Decimal("120"))
        decision = ProfitLockPolicy.evaluate(Decimal("120"), profit, state)
        assert decision.action == "none"
