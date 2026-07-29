"""
CircuitBreakerState — per-instance state for the daily drop circuit breaker.

When intraday price drops by at least ``critical_threshold`` percent from the
day's open, the breaker triggers:
  - All pending buy orders are cancelled.
  - No new buy orders are placed (the bot stops averaging into a falling knife).
  - Sell orders on already-filled levels remain active (exits are not blocked).
  - The bot enters standby until the configured ``resume_mode`` allows buys
    again (see ``BreakerResumeMode``).

Resume modes (what happens AFTER trigger):
  - TA_CONFIRM (default): wait for 15m TA reversal (RSI<30 AND MACD bullish
    cross), then reset and place one buy at the current price.
  - WIDEN_STEP: do NOT stop buys — keep averaging but with grid step widened
    by ``widen_multiplier`` (default 2×). Buys are spaced further apart so
    the bot averages more conservatively into the drop.
  - TRAILING_BUY: stop buys, track the intraday low, and resume only after
    price recovers by ``recovery_pct`` (default 5%) from that low. Avoids
    catching the falling knife without relying on TA.

The breaker automatically resets at the start of each new UTC day: a fresh
``day_open_price`` is captured and ``triggered`` is cleared.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum

from core.logging import get_logger

logger = get_logger(__name__)


class BreakerResumeMode(str, Enum):
    """What the bot does after the breaker triggers.

    - TA_CONFIRM: stop buys, wait for 15m TA reversal confirmation.
    - WIDEN_STEP: keep buying but with grid step × widen_multiplier.
    - TRAILING_BUY: stop buys, resume after price recovers recovery_pct
      from the intraday low recorded since the trigger.
    """

    TA_CONFIRM = "ta_confirm"
    WIDEN_STEP = "widen_step"
    TRAILING_BUY = "trailing_buy"


# Default recovery % from the intraday low for TRAILING_BUY mode.
DEFAULT_RECOVERY_PCT = Decimal("5.0")
# Default step multiplier for WIDEN_STEP mode (2× wider grid spacing).
DEFAULT_WIDEN_MULTIPLIER = Decimal("2")


def _utc_today() -> date:
    """Today's date in UTC (exchange candles are typically UTC-based)."""
    return datetime.now(UTC).date()


@dataclass
class CircuitBreakerState:
    """State tracking for the daily drop circuit breaker of one grid instance.

    Attributes:
        instance_id: Trading instance id.
        critical_threshold: Intraday drop percentage that triggers the breaker
            (positive number, e.g. ``Decimal("4.0")`` = 4% drop).
        min_continuation_rate: The continuation rate the analyzer used to derive
            ``critical_threshold`` (kept for logging/audit).
        resume_mode: What the bot does after the breaker triggers. See
            ``BreakerResumeMode``. Defaults to ``TA_CONFIRM`` (legacy behavior).
        recovery_pct: For ``TRAILING_BUY`` mode — the % recovery from the
            intraday low required before buys resume (default 5%).
        widen_multiplier: For ``WIDEN_STEP`` mode — grid step is multiplied by
            this while the breaker is active (default 2 = 2× wider spacing).
        day_open_price: Price captured at the start of the current UTC day;
            intraday drop is measured relative to this.
        triggered: Whether the breaker is currently active (buys blocked).
        trigger_date: UTC date when the breaker last triggered.
        trigger_price: Price at which the breaker last triggered.
        triggered_at: Timestamp of the last trigger event.
        bottom_price: Lowest price observed since the breaker triggered
            (used by ``TRAILING_BUY`` mode to measure recovery). Reset on
            trigger and on day rollover.
        ta_15m_configs: TA configs used to confirm a reversal while the breaker
            is active (only used by ``TA_CONFIRM`` mode). Defaults to
            RSI(14) < 30 AND MACD bullish cross on 15m.
    """

    instance_id: str
    critical_threshold: Decimal
    min_continuation_rate: Decimal = Decimal("0.80")
    resume_mode: BreakerResumeMode = BreakerResumeMode.TA_CONFIRM
    recovery_pct: Decimal = DEFAULT_RECOVERY_PCT
    widen_multiplier: Decimal = DEFAULT_WIDEN_MULTIPLIER
    day_open_price: Decimal | None = None
    triggered: bool = False
    trigger_date: date | None = None
    trigger_price: Decimal | None = None
    triggered_at: datetime | None = None
    bottom_price: Decimal | None = None
    ta_15m_configs: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.ta_15m_configs:
            self.ta_15m_configs = self._default_ta_15m_configs()

    @staticmethod
    def _default_ta_15m_configs() -> list[dict]:
        """Default reversal-confirmation configs: RSI < 30 AND MACD bullish."""
        return [
            {
                "indicator": "rsi",
                "time_frame": "15m",
                "operator": "and",
                "params": {"period": 14, "oversold": 30},
                "enabled": True,
                "priority": 1,
                "description": "Breaker reversal gate — RSI oversold on 15m",
            },
            {
                "indicator": "macd",
                "time_frame": "15m",
                "operator": "and",
                "params": {
                    "fast_period": 12,
                    "slow_period": 26,
                    "signal_period": 9,
                    "bullish_cross": True,
                },
                "enabled": True,
                "priority": 2,
                "description": "Breaker reversal gate — MACD bullish cross on 15m",
            },
        ]

    # ------------------------------------------------------------------
    # Day rollover & intraday drop measurement
    # ------------------------------------------------------------------

    def check_new_day(self, current_price: Decimal) -> None:
        """Roll over to a new UTC day if needed.

        On a new day the breaker is cleared and ``day_open_price`` is reset to
        the first price observed that day. ``bottom_price`` is also cleared
        since the intraday low from yesterday no longer applies.

        If ``trigger_date`` is None (breaker just configured, never seen a
        price update yet), this seeds ``trigger_date`` to today WITHOUT
        overriding ``day_open_price`` — the caller (configure_circuit_breaker)
        may have already set a meaningful day_open. This avoids a spurious
        "day rollover" on the very first price update.
        """
        today = _utc_today()
        if self.trigger_date == today:
            return  # same day, no rollover needed
        if self.trigger_date is None:
            # First price update after configuration — seed trigger_date to
            # today but keep the configured day_open_price (if any).
            self.trigger_date = today
            if self.day_open_price is None:
                self.day_open_price = current_price
            logger.debug(
                "Circuit breaker seeded trigger_date (first update)",
                extra={
                    "instance_id": self.instance_id,
                    "day_open": str(self.day_open_price),
                    "date": str(today),
                },
            )
            return
        # Genuine new day — clear triggered, reset day_open + bottom.
        self.triggered = False
        self.trigger_date = today
        self.day_open_price = current_price
        self.bottom_price = None
        logger.info(
            "Circuit breaker day rollover",
            extra={
                "instance_id": self.instance_id,
                "new_day_open": str(current_price),
                "date": str(today),
            },
        )

    def intraday_drop_pct(self, current_price: Decimal) -> Decimal:
        """Return the intraday drop as a signed percentage (negative = fell).

        Returns ``Decimal("0")`` if no day-open price has been set yet.
        """
        if self.day_open_price is None or self.day_open_price <= 0:
            return Decimal("0")
        return (current_price - self.day_open_price) / self.day_open_price * Decimal("100")

    def should_trigger(self, current_price: Decimal) -> bool:
        """True if the intraday drop has reached the critical threshold."""
        if self.triggered:
            return False
        drop = self.intraday_drop_pct(current_price)
        # drop is negative when price fell; threshold is a positive magnitude.
        return drop <= -self.critical_threshold

    def update_bottom(self, current_price: Decimal) -> None:
        """Track the lowest price observed since the breaker triggered.

        Used by ``TRAILING_BUY`` mode to measure recovery from the intraday
        low. Only updates while the breaker is active; ignored otherwise.
        """
        if not self.triggered:
            return
        if self.bottom_price is None or current_price < self.bottom_price:
            self.bottom_price = current_price

    def should_resume_trailing(self, current_price: Decimal) -> bool:
        """True if price has recovered by ``recovery_pct`` from the low.

        For ``TRAILING_BUY`` mode. Returns ``False`` if no bottom has been
        recorded yet (e.g. breaker just triggered and no price update has
        arrived since).

        Recovery is measured as: current_price >= bottom × (1 + recovery_pct/100).
        E.g. bottom=95, recovery_pct=5 → resume when price >= 99.75.
        """
        if not self.triggered or self.bottom_price is None:
            return False
        if self.bottom_price <= 0:
            return False
        recovery_factor = Decimal("1") + self.recovery_pct / Decimal("100")
        return current_price >= self.bottom_price * recovery_factor

    # ------------------------------------------------------------------
    # Trigger / reset
    # ------------------------------------------------------------------

    def trigger(self, price: Decimal) -> None:
        """Mark the breaker as triggered at the given price.

        Seeds ``bottom_price`` with the trigger price so ``TRAILING_BUY``
        mode has a baseline to measure recovery from.
        """
        self.triggered = True
        self.trigger_price = price
        self.triggered_at = datetime.now(UTC)
        self.bottom_price = price
        logger.warning(
            "Circuit breaker triggered",
            extra={
                "instance_id": self.instance_id,
                "trigger_price": str(price),
                "critical_threshold": str(self.critical_threshold),
                "intraday_drop_pct": str(self.intraday_drop_pct(price)),
                "resume_mode": self.resume_mode.value,
            },
        )

    def reset(self) -> None:
        """Clear the triggered flag (e.g. after TA 15m confirmed a buy)."""
        was = self.triggered
        self.triggered = False
        if was:
            logger.info(
                "Circuit breaker reset after TA confirmation",
                extra={
                    "instance_id": self.instance_id,
                    "trigger_price": str(self.trigger_price) if self.trigger_price else None,
                },
            )

    def get_ta_15m_configs(self) -> list[dict]:
        """Return the TA configs to evaluate while the breaker is active."""
        return self.ta_15m_configs
