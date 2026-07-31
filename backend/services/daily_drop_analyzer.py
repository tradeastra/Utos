"""
DailyDropAnalyzer — analyze daily candles to find the critical drop threshold.

The critical drop threshold is the daily drop percentage at which the market
tends to continue falling over the next ``continuation_window`` days. When
intraday drop reaches this threshold, the grid circuit breaker triggers:
pending buys are cancelled and the bot enters standby until TA (15m) confirms
a reversal.

Three tiers map continuation rate → window + future decline target:

  ┌──────────────┬──────┬─────────┬────────────────┬──────────────────────┐
  │ Tier         │ Rate │ Window  │ Future decline │ Meaning              │
  ├──────────────┼──────┼─────────┼────────────────┼──────────────────────┤
  │ Protective   │ 70%  │ 5 days  │ ≥ 9%           │ Stop averaging early │
  │ Balanced     │ 80%  │ 10 days │ ≥ 12%          │ Middle ground        │
  │ Fearless     │ 90%  │ 30 days │ ≥ 15%          │ Keep averaging long  │
  └──────────────┴──────┴─────────┴────────────────┴──────────────────────┘

Algorithm (multi-day continuation with fixed future decline target):
  1. For each day i with a daily drop, look ahead ``continuation_window`` days.
  2. A drop event "continues" if the price ``continuation_window`` days later
     is at least ``min_future_drop_pct`` below the drop-day close.
     E.g. Protective: drop day close $100 → 5 days later ≤ $91 (≥9% decline).
  3. For each candidate threshold T (from 1% to 15%, step 0.5%):
     - Collect days where daily_drop <= T%
     - Compute continuation_rate = #(continued) / #(drop events)
  4. Return the first T where continuation_rate >= min_continuation_rate.

This is more robust than checking only the next day: a single up-day right
after a drop no longer disqualifies a real multi-day downtrend. The fixed
future decline target ensures only meaningful downtrends count as "continued"
— a 3% drop followed by a mere 1% drift is NOT a valid continuation.

Configurable parameters:
  - lookback_days: how many daily candles to analyze (default 365)
  - continuation_window: days to look ahead (tier-dependent: 5/10/30)
  - min_future_drop_pct: minimum decline over the window to count as continued
    (tier-dependent: 9% / 12% / 15%)
  - min_continuation_rate: 0.70 / 0.80 / 0.90 (tier key)
  - min_samples: minimum number of drop events required for a threshold to be
    considered valid (avoid noise from tiny samples)

If data is insufficient or no threshold meets the criteria, a conservative
fallback is returned based on the min_continuation_rate:
  - 0.70 -> 3.0%
  - 0.80 -> 4.0%
  - 0.90 -> 5.0%
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from core.domain_types import Candle
from core.logging import get_logger

logger = get_logger(__name__)

# Candidate thresholds scanned from small to large drop (absolute % values).
# A threshold "qualifies" when enough historical days dropped at least that
# much AND the continuation rate meets the user-selected minimum.
_CANDIDATE_THRESHOLDS = [
    Decimal("1.0"), Decimal("1.5"), Decimal("2.0"), Decimal("2.5"),
    Decimal("3.0"), Decimal("3.5"), Decimal("4.0"), Decimal("4.5"),
    Decimal("5.0"), Decimal("5.5"), Decimal("6.0"), Decimal("6.5"),
    Decimal("7.0"), Decimal("7.5"), Decimal("8.0"), Decimal("8.5"),
    Decimal("9.0"), Decimal("9.5"), Decimal("10.0"), Decimal("11.0"),
    Decimal("12.0"), Decimal("13.0"), Decimal("14.0"), Decimal("15.0"),
]

# Fallback thresholds when data is insufficient or no threshold qualifies.
# Higher continuation rate requirement -> more conservative (larger) fallback.
_FALLBACK_THRESHOLDS = {
    Decimal("0.70"): Decimal("3.0"),
    Decimal("0.80"): Decimal("4.0"),
    Decimal("0.90"): Decimal("5.0"),
}

# Tier configs: continuation rate → (window days, future decline %).
# Protective (70%): 5-day window, ≥9% future decline — trigger early.
# Balanced  (80%): 10-day window, ≥12% future decline — middle ground.
# Fearless   (90%): 30-day window, ≥15% future decline — keep averaging.
TIER_CONFIGS: dict[Decimal, tuple[int, Decimal]] = {
    Decimal("0.70"): (5, Decimal("9.0")),
    Decimal("0.80"): (10, Decimal("12.0")),
    Decimal("0.90"): (30, Decimal("15.0")),
}

DEFAULT_LOOKBACK_DAYS = 365
DEFAULT_CONTINUATION_WINDOW = 5
DEFAULT_MIN_FUTURE_DROP_PCT = Decimal("9.0")
DEFAULT_MIN_CONTINUATION_RATE = Decimal("0.80")
DEFAULT_MIN_SAMPLES = 3


@dataclass(frozen=True)
class AnalysisResult:
    """Detailed result of drop analysis.

    Attributes:
        threshold_pct: Critical drop threshold (positive %).
        used_fallback: True if no data-driven threshold was found.
        drop_events: Number of drop events at the returned threshold.
        continued_events: Number of those that continued.
        continuation_rate: continued_events / drop_events (0 if no events).
    """

    threshold_pct: Decimal
    used_fallback: bool
    drop_events: int = 0
    continued_events: int = 0
    continuation_rate: Decimal = Decimal("0")


class DailyDropAnalyzer:
    """Analyze daily candles to find the critical intraday drop threshold."""

    def analyze(
        self,
        daily_candles: list[Candle],
        min_continuation_rate: Decimal = DEFAULT_MIN_CONTINUATION_RATE,
        min_samples: int = DEFAULT_MIN_SAMPLES,
        continuation_window: int = DEFAULT_CONTINUATION_WINDOW,
        min_future_drop_pct: Decimal = DEFAULT_MIN_FUTURE_DROP_PCT,
    ) -> Decimal:
        """Return the critical drop threshold as a positive percentage.

        Thin wrapper around ``analyze_detailed`` — returns only the threshold.
        See ``analyze_detailed`` for full docs and the ``used_fallback`` flag.
        """
        return self.analyze_detailed(
            daily_candles,
            min_continuation_rate=min_continuation_rate,
            min_samples=min_samples,
            continuation_window=continuation_window,
            min_future_drop_pct=min_future_drop_pct,
        ).threshold_pct

    def analyze_detailed(
        self,
        daily_candles: list[Candle],
        min_continuation_rate: Decimal = DEFAULT_MIN_CONTINUATION_RATE,
        min_samples: int = DEFAULT_MIN_SAMPLES,
        continuation_window: int = DEFAULT_CONTINUATION_WINDOW,
        min_future_drop_pct: Decimal = DEFAULT_MIN_FUTURE_DROP_PCT,
    ) -> AnalysisResult:
        """Analyze daily candles and return threshold + fallback status.

        Args:
            daily_candles: Daily (1d) candles, oldest first. Needs at least
                ``continuation_window + 2`` candles to produce a meaningful
                result.
            min_continuation_rate: Tier key (0.70/0.80/0.90). Higher rate
                requires more historical evidence that drops continue.
            min_samples: Minimum number of drop events at a threshold for it
                to be considered statistically meaningful.
            continuation_window: Days to look ahead (tier-dependent: 5/10/30).
            min_future_drop_pct: Minimum decline over the window to count as
                continued (tier-dependent: 9% / 12% / 15%).

        Returns:
            ``AnalysisResult`` with threshold, ``used_fallback`` flag, and
            drop event statistics.
        """
        if continuation_window < 1:
            continuation_window = 1

        # Need: 1 (prev) + 1 (drop day) + window (lookahead) + slack for
        # min_samples distinct drop events.
        min_candles = continuation_window + 2
        if len(daily_candles) < min_candles:
            logger.warning(
                "Insufficient daily candles for drop analysis",
                extra={
                    "candle_count": len(daily_candles),
                    "required": min_candles,
                    "continuation_window": continuation_window,
                },
            )
            return AnalysisResult(
                threshold_pct=self._fallback(min_continuation_rate),
                used_fallback=True,
            )

        # Build drop events: (daily_drop%, future_close, drop_day_close).
        # A drop event "continues" if future_close is at least
        # min_future_drop_pct below drop_day_close.
        # daily_drop is negative when price fell.
        drops: list[tuple[Decimal, Decimal, Decimal]] = []
        for i in range(1, len(daily_candles) - continuation_window):
            prev_close = daily_candles[i - 1].close
            curr_close = daily_candles[i].close
            future_close = daily_candles[i + continuation_window].close
            if prev_close <= 0 or curr_close <= 0:
                continue
            daily_drop = (curr_close - prev_close) / prev_close * Decimal("100")
            drops.append((daily_drop, future_close, curr_close))

        if len(drops) < min_samples:
            logger.warning(
                "Not enough drop events for drop analysis",
                extra={
                    "events": len(drops),
                    "continuation_window": continuation_window,
                },
            )
            return AnalysisResult(
                threshold_pct=self._fallback(min_continuation_rate),
                used_fallback=True,
            )

        # Scan thresholds from small to large drop. The first threshold whose
        # continuation rate meets the requirement wins — smaller thresholds
        # that qualify mean the breaker triggers earlier (more protective).
        min_drop_factor = Decimal("1") - min_future_drop_pct / Decimal("100")
        for threshold_abs in _CANDIDATE_THRESHOLDS:
            threshold = -threshold_abs  # negative because drops are negative
            subset = [d for d in drops if d[0] <= threshold]
            if len(subset) < min_samples:
                continue
            # Fixed future drop: continued if
            # close[i + window] <= close[i] * (1 - min_future_drop_pct/100)
            continued = sum(1 for d in subset if d[1] <= d[2] * min_drop_factor)
            rate = Decimal(continued) / Decimal(len(subset))
            if rate >= min_continuation_rate:
                logger.info(
                    "Critical drop threshold found",
                    extra={
                        "threshold_pct": str(threshold_abs),
                        "continuation_rate": str(rate),
                        "samples": len(subset),
                        "min_continuation_rate": str(min_continuation_rate),
                        "continuation_window": continuation_window,
                        "min_future_drop_pct": str(min_future_drop_pct),
                    },
                )
                return AnalysisResult(
                    threshold_pct=threshold_abs,
                    used_fallback=False,
                    drop_events=len(subset),
                    continued_events=continued,
                    continuation_rate=rate,
                )

        logger.info(
            "No threshold met continuation rate; using fallback",
            extra={
                "min_continuation_rate": str(min_continuation_rate),
                "continuation_window": continuation_window,
                "min_future_drop_pct": str(min_future_drop_pct),
            },
        )
        return AnalysisResult(
            threshold_pct=self._fallback(min_continuation_rate),
            used_fallback=True,
        )

    @staticmethod
    def _fallback(min_continuation_rate: Decimal) -> Decimal:
        """Conservative fallback threshold based on continuation rate."""
        key = Decimal(str(min_continuation_rate))
        return _FALLBACK_THRESHOLDS.get(key, Decimal("4.0"))
