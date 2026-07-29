"""
Unit tests for CircuitBreakerState — daily drop circuit breaker state machine.

State transitions:
  NORMAL (triggered=False)
    -> check_new_day rolls over day_open on a new UTC date
    -> should_trigger True when intraday_drop <= -critical_threshold
    -> trigger() sets triggered=True, records price/time, seeds bottom_price
  TRIGGERED (triggered=True)
    -> should_trigger stays False (no re-trigger same day)
    -> update_bottom() tracks the intraday low (for TRAILING_BUY mode)
    -> resume behavior depends on resume_mode:
       - TA_CONFIRM: get_ta_15m_configs() → reset on TA pass
       - WIDEN_STEP: keep buying with widened step; reset on TA pass
       - TRAILING_BUY: should_resume_trailing() True when price recovers
         recovery_pct from bottom → reset
    -> check_new_day on a new date clears triggered and resets day_open
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from engine.grid.circuit_breaker import (
    DEFAULT_RECOVERY_PCT,
    DEFAULT_WIDEN_MULTIPLIER,
    BreakerResumeMode,
    CircuitBreakerState,
)


class TestCircuitBreakerState:
    def setup_method(self) -> None:
        self.breaker = CircuitBreakerState(
            instance_id="inst-1",
            critical_threshold=Decimal("4.0"),
            min_continuation_rate=Decimal("0.90"),
            day_open_price=Decimal("100"),
        )

    def test_initial_state_not_triggered(self) -> None:
        assert self.breaker.triggered is False
        assert self.breaker.day_open_price == Decimal("100")

    def test_intraday_drop_calculation(self) -> None:
        # 100 -> 96 = -4%
        drop = self.breaker.intraday_drop_pct(Decimal("96"))
        assert drop == Decimal("-4")

    def test_should_trigger_at_exact_threshold(self) -> None:
        # drop exactly -4% should trigger (<= -threshold)
        assert self.breaker.should_trigger(Decimal("96")) is True

    def test_should_trigger_beyond_threshold(self) -> None:
        # drop -5% should trigger
        assert self.breaker.should_trigger(Decimal("95")) is True

    def test_should_not_trigger_above_threshold(self) -> None:
        # drop -3.9% should NOT trigger
        assert self.breaker.should_trigger(Decimal("96.1")) is False

    def test_should_not_trigger_when_already_triggered(self) -> None:
        self.breaker.trigger(Decimal("96"))
        assert self.breaker.triggered is True
        # Even a deeper drop should not re-trigger
        assert self.breaker.should_trigger(Decimal("90")) is False

    def test_trigger_records_price_and_time(self) -> None:
        self.breaker.trigger(Decimal("95"))
        assert self.breaker.trigger_price == Decimal("95")
        assert self.breaker.triggered_at is not None
        assert self.breaker.triggered is True

    def test_reset_clears_triggered(self) -> None:
        self.breaker.trigger(Decimal("96"))
        self.breaker.reset()
        assert self.breaker.triggered is False

    def test_default_ta_15m_configs_present(self) -> None:
        configs = self.breaker.get_ta_15m_configs()
        assert len(configs) == 2
        indicators = {c["indicator"] for c in configs}
        assert indicators == {"rsi", "macd"}
        for c in configs:
            assert c["time_frame"] == "15m"
            assert c["enabled"] is True

    def test_custom_ta_15m_configs_override(self) -> None:
        custom = [{"indicator": "rsi", "time_frame": "15m", "operator": "and",
                   "params": {"period": 21}, "enabled": True, "priority": 1}]
        breaker = CircuitBreakerState(
            instance_id="inst-2",
            critical_threshold=Decimal("3.0"),
            ta_15m_configs=custom,
        )
        assert breaker.get_ta_15m_configs() == custom

    def test_check_new_day_resets_and_sets_open(self) -> None:
        # Trigger first
        self.breaker.trigger(Decimal("96"))
        assert self.breaker.triggered is True

        # Simulate a new day by forcing trigger_date to yesterday
        self.breaker.trigger_date = date.today() - timedelta(days=1)

        # New price on the new day
        self.breaker.check_new_day(Decimal("94"))
        assert self.breaker.triggered is False
        assert self.breaker.day_open_price == Decimal("94")
        assert self.breaker.trigger_date == date.today()

    def test_check_new_day_same_day_no_reset(self) -> None:
        # Set trigger_date to today so check_new_day treats it as same day
        self.breaker.trigger_date = date.today()
        original_open = self.breaker.day_open_price
        self.breaker.check_new_day(Decimal("98"))
        # Same day -> open price unchanged
        assert self.breaker.day_open_price == original_open

    def test_intraday_drop_with_no_open_returns_zero(self) -> None:
        breaker = CircuitBreakerState(
            instance_id="inst-3",
            critical_threshold=Decimal("4.0"),
        )
        assert breaker.day_open_price is None
        assert breaker.intraday_drop_pct(Decimal("90")) == Decimal("0")
        assert breaker.should_trigger(Decimal("90")) is False

    def test_check_new_day_seeds_open_when_none(self) -> None:
        breaker = CircuitBreakerState(
            instance_id="inst-4",
            critical_threshold=Decimal("4.0"),
        )
        assert breaker.day_open_price is None
        breaker.check_new_day(Decimal("100"))
        assert breaker.day_open_price == Decimal("100")


class TestResumeModeDefaults:
    """Default resume mode is TA_CONFIRM (legacy behavior preserved)."""

    def test_default_resume_mode_is_ta_confirm(self) -> None:
        breaker = CircuitBreakerState(
            instance_id="inst",
            critical_threshold=Decimal("4.0"),
        )
        assert breaker.resume_mode == BreakerResumeMode.TA_CONFIRM

    def test_default_recovery_pct_is_5(self) -> None:
        breaker = CircuitBreakerState(
            instance_id="inst",
            critical_threshold=Decimal("4.0"),
        )
        assert breaker.recovery_pct == DEFAULT_RECOVERY_PCT
        assert breaker.recovery_pct == Decimal("5.0")

    def test_default_widen_multiplier_is_2(self) -> None:
        breaker = CircuitBreakerState(
            instance_id="inst",
            critical_threshold=Decimal("4.0"),
        )
        assert breaker.widen_multiplier == DEFAULT_WIDEN_MULTIPLIER
        assert breaker.widen_multiplier == Decimal("2")

    def test_trigger_seeds_bottom_price(self) -> None:
        breaker = CircuitBreakerState(
            instance_id="inst",
            critical_threshold=Decimal("4.0"),
            day_open_price=Decimal("100"),
        )
        breaker.trigger(Decimal("96"))
        assert breaker.bottom_price == Decimal("96")


class TestTrailingBuyMode:
    """TRAILING_BUY: stop buys, resume after price recovers recovery_pct from low.

    Scenario: threshold 4%, day_open $100, recovery_pct 5%.
      - Trigger at $96 (drop 4%).
      - Price keeps falling to $90 (new bottom).
      - Price recovers to $94.5 → recovery from $90 = 5% → resume.
      - Price recovers to $94.4 → recovery < 5% → still blocked.
    """

    def setup_method(self) -> None:
        self.breaker = CircuitBreakerState(
            instance_id="inst",
            critical_threshold=Decimal("4.0"),
            day_open_price=Decimal("100"),
            resume_mode=BreakerResumeMode.TRAILING_BUY,
            recovery_pct=Decimal("5.0"),
        )

    def test_should_resume_false_before_any_recovery(self) -> None:
        self.breaker.trigger(Decimal("96"))
        # Bottom seeded at trigger price 96. Price still at 96 → 0% recovery.
        assert self.breaker.should_resume_trailing(Decimal("96")) is False

    def test_update_bottom_tracks_new_low(self) -> None:
        self.breaker.trigger(Decimal("96"))
        assert self.breaker.bottom_price == Decimal("96")
        self.breaker.update_bottom(Decimal("92"))
        assert self.breaker.bottom_price == Decimal("92")
        # Higher price does not update bottom.
        self.breaker.update_bottom(Decimal("95"))
        assert self.breaker.bottom_price == Decimal("92")

    def test_update_bottom_ignored_when_not_triggered(self) -> None:
        # Not triggered yet → update_bottom is a no-op.
        self.breaker.update_bottom(Decimal("50"))
        assert self.breaker.bottom_price is None

    def test_resume_at_exact_recovery_threshold(self) -> None:
        # bottom=90, recovery 5% → 90 × 1.05 = 94.5 → resume at exactly 94.5.
        self.breaker.trigger(Decimal("96"))
        self.breaker.update_bottom(Decimal("90"))
        assert self.breaker.should_resume_trailing(Decimal("94.5")) is True

    def test_no_resume_below_recovery_threshold(self) -> None:
        self.breaker.trigger(Decimal("96"))
        self.breaker.update_bottom(Decimal("90"))
        # 94.4 < 94.5 → not enough recovery.
        assert self.breaker.should_resume_trailing(Decimal("94.4")) is False

    def test_resume_after_strong_recovery(self) -> None:
        self.breaker.trigger(Decimal("96"))
        self.breaker.update_bottom(Decimal("90"))
        # 99 > 94.5 → well past recovery threshold.
        assert self.breaker.should_resume_trailing(Decimal("99")) is True

    def test_no_resume_when_not_triggered(self) -> None:
        # Without trigger, bottom_price is None → cannot resume.
        assert self.breaker.should_resume_trailing(Decimal("100")) is False

    def test_custom_recovery_pct_changes_threshold(self) -> None:
        breaker = CircuitBreakerState(
            instance_id="inst",
            critical_threshold=Decimal("4.0"),
            day_open_price=Decimal("100"),
            resume_mode=BreakerResumeMode.TRAILING_BUY,
            recovery_pct=Decimal("10.0"),  # stricter: 10% recovery
        )
        breaker.trigger(Decimal("96"))
        breaker.update_bottom(Decimal("90"))
        # 90 × 1.10 = 99 → need 99 to resume.
        assert breaker.should_resume_trailing(Decimal("98.9")) is False
        assert breaker.should_resume_trailing(Decimal("99")) is True

    def test_check_new_day_clears_bottom_price(self) -> None:
        self.breaker.trigger(Decimal("96"))
        self.breaker.update_bottom(Decimal("90"))
        assert self.breaker.bottom_price == Decimal("90")
        # Force a new day.
        self.breaker.trigger_date = date.today() - timedelta(days=1)
        self.breaker.check_new_day(Decimal("94"))
        assert self.breaker.bottom_price is None
        assert self.breaker.triggered is False


class TestWidenStepMode:
    """WIDEN_STEP: keep buying with widened step; reset on TA confirmation.

    The breaker state itself does not block buys in this mode (the engine
    handles that). These tests verify the state fields and that the breaker
    still resets normally on TA pass / new day.
    """

    def test_widen_step_mode_field(self) -> None:
        breaker = CircuitBreakerState(
            instance_id="inst",
            critical_threshold=Decimal("4.0"),
            resume_mode=BreakerResumeMode.WIDEN_STEP,
            widen_multiplier=Decimal("3"),
        )
        assert breaker.resume_mode == BreakerResumeMode.WIDEN_STEP
        assert breaker.widen_multiplier == Decimal("3")

    def test_widen_step_trigger_still_records_bottom(self) -> None:
        # bottom_price is tracked regardless of mode (cheap, useful for audit).
        breaker = CircuitBreakerState(
            instance_id="inst",
            critical_threshold=Decimal("4.0"),
            day_open_price=Decimal("100"),
            resume_mode=BreakerResumeMode.WIDEN_STEP,
        )
        breaker.trigger(Decimal("96"))
        assert breaker.triggered is True
        assert breaker.bottom_price == Decimal("96")

    def test_widen_step_reset_clears_triggered(self) -> None:
        breaker = CircuitBreakerState(
            instance_id="inst",
            critical_threshold=Decimal("4.0"),
            day_open_price=Decimal("100"),
            resume_mode=BreakerResumeMode.WIDEN_STEP,
        )
        breaker.trigger(Decimal("96"))
        breaker.reset()
        assert breaker.triggered is False


class TestTaConfirmMode:
    """TA_CONFIRM (default / legacy): stop buys, resume on 15m TA reversal.

    This is the original behavior — verified here to ensure the new resume_mode
    field does not break existing flow.
    """

    def test_ta_confirm_default_ta_configs_present(self) -> None:
        breaker = CircuitBreakerState(
            instance_id="inst",
            critical_threshold=Decimal("4.0"),
            resume_mode=BreakerResumeMode.TA_CONFIRM,
        )
        configs = breaker.get_ta_15m_configs()
        assert len(configs) == 2
        indicators = {c["indicator"] for c in configs}
        assert indicators == {"rsi", "macd"}

    def test_ta_confirm_does_not_use_trailing_resume(self) -> None:
        # In TA_CONFIRM mode, should_resume_trailing is irrelevant — the
        # engine uses TA 15m configs instead. But the method still works
        # mechanically (returns False because bottom tracking is incidental).
        breaker = CircuitBreakerState(
            instance_id="inst",
            critical_threshold=Decimal("4.0"),
            day_open_price=Decimal("100"),
            resume_mode=BreakerResumeMode.TA_CONFIRM,
        )
        breaker.trigger(Decimal("96"))
        breaker.update_bottom(Decimal("90"))
        # Even with strong recovery, TA_CONFIRM mode does not resume via
        # trailing — the engine ignores should_resume_trailing for this mode.
        # The method itself still returns True (mechanical), but the engine
        # will not call it. This test documents that the method is mode-agnostic.
        assert breaker.should_resume_trailing(Decimal("99")) is True
