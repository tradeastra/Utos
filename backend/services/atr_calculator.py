"""ATR-based grid spacing calculator.

Computes adaptive grid spacing from historical daily candles using ATR
(Average True Range) and an adaptive factor that responds to current
volatility conditions.

Formula:
    spacing_pct = max(tp_range_pct, atr_pct × adaptive_factor)

Where:
    atr_pct = ATR(14) / current_price × 100
    adaptive_factor = clamp(1.5 × (atr_14 / avg_atr_30), 0.8, 2.5)

The adaptive factor compares recent volatility (ATR-14) against the
longer-term average (ATR-30). When volatility is expanding, the factor
increases → wider spacing → fewer trades (cautious). When volatility
is contracting, the factor decreases → tighter spacing → more trades
(aggressive capture of small oscillations).

TP range per strategy mode (take-profit target per grid level):
    A=0.3%, B=0.6%, C=0.9%, D=1.5%, U=3.0%
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from core.domain_types import Candle
from core.logging import get_logger

logger = get_logger(__name__)

# ATR periods.
ATR_PERIOD = 14
AVG_ATR_PERIOD = 30

# Adaptive factor bounds and base.
_BASE_FACTOR = 1.5
_MIN_FACTOR = 0.8
_MAX_FACTOR = 2.5

# Minimum candles needed for a meaningful ATR calculation.
_MIN_CANDLES = ATR_PERIOD + 1


@dataclass(frozen=True)
class SpacingResult:
    """Result of auto-calculating grid spacing from ATR + TP range.

    Attributes:
        tp_range_pct: Take-profit target per grid level (from strategy mode).
        atr_pct: Current ATR(14) as percentage of latest close.
        avg_atr_pct: Average ATR(30) as percentage of latest close.
        adaptive_factor: Multiplier derived from ATR ratio (0.8–2.5).
        spacing_pct: Final grid spacing = max(tp_range, atr × factor).
        used_fallback: True if insufficient candle data → spacing = tp_range.
        candle_count: Number of daily candles used.
    """

    tp_range_pct: float
    atr_pct: float
    avg_atr_pct: float
    adaptive_factor: float
    spacing_pct: float
    used_fallback: bool
    candle_count: int


def _true_ranges(candles: list[Candle]) -> list[Decimal]:
    """Compute True Range for each candle (needs at least 2 candles)."""
    ranges: list[Decimal] = []
    for i in range(1, len(candles)):
        prev_close = candles[i - 1].close
        high = candles[i].high
        low = candles[i].low
        if prev_close <= 0:
            continue
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close),
        )
        ranges.append(tr)
    return ranges


def _atr(candles: list[Candle], period: int = ATR_PERIOD) -> Decimal:
    """Compute ATR over the last ``period`` true ranges."""
    trs = _true_ranges(candles)
    if len(trs) < period:
        # Not enough data — use what we have.
        if not trs:
            return Decimal("0")
        return sum(trs, Decimal("0")) / Decimal(len(trs))
    return sum(trs[-period:], Decimal("0")) / Decimal(period)


def _avg_atr(candles: list[Candle], period: int = AVG_ATR_PERIOD) -> Decimal:
    """Compute average ATR over a longer window for the adaptive ratio."""
    trs = _true_ranges(candles)
    if not trs:
        return Decimal("0")
    window = trs[-period:] if len(trs) >= period else trs
    return sum(window, Decimal("0")) / Decimal(len(window))


def _adaptive_factor(atr: Decimal, avg_atr: Decimal) -> float:
    """Compute adaptive factor from ATR ratio.

    factor = clamp(1.5 × (atr / avg_atr), 0.8, 2.5)

    - Volatility expanding (atr > avg): factor > 1.5 → wider spacing.
    - Volatility normal (atr = avg): factor = 1.5.
    - Volatility contracting (atr < avg): factor < 1.5 → tighter spacing.
    """
    if avg_atr <= 0:
        return _BASE_FACTOR
    ratio = float(atr / avg_atr)
    factor = _BASE_FACTOR * ratio
    return max(_MIN_FACTOR, min(_MAX_FACTOR, factor))


def calculate_spacing(
    tp_range_pct: float,
    candles: list[Candle],
    atr_period: int = ATR_PERIOD,
    avg_period: int = AVG_ATR_PERIOD,
) -> SpacingResult:
    """Auto-calculate grid spacing from ATR + TP range.

    Args:
        tp_range_pct: Take-profit target per grid level (from strategy mode).
        candles: Daily (1d) candles, oldest first. Needs at least
            ``ATR_PERIOD + 1`` candles for a meaningful result.
        atr_period: ATR lookback (default 14).
        avg_period: Average ATR window for adaptive factor (default 30).

    Returns:
        ``SpacingResult`` with spacing and all intermediate values.
    """
    candle_count = len(candles)

    if candle_count < _MIN_CANDLES:
        logger.warning(
            "Insufficient candles for ATR spacing calculation",
            extra={"candle_count": candle_count, "required": _MIN_CANDLES},
        )
        return SpacingResult(
            tp_range_pct=tp_range_pct,
            atr_pct=0.0,
            avg_atr_pct=0.0,
            adaptive_factor=_BASE_FACTOR,
            spacing_pct=tp_range_pct,
            used_fallback=True,
            candle_count=candle_count,
        )

    latest_close = candles[-1].close
    if latest_close <= 0:
        return SpacingResult(
            tp_range_pct=tp_range_pct,
            atr_pct=0.0,
            avg_atr_pct=0.0,
            adaptive_factor=_BASE_FACTOR,
            spacing_pct=tp_range_pct,
            used_fallback=True,
            candle_count=candle_count,
        )

    atr = _atr(candles, atr_period)
    avg_atr = _avg_atr(candles, avg_period)
    factor = _adaptive_factor(atr, avg_atr)

    atr_pct = float(atr / latest_close * Decimal("100"))
    avg_atr_pct = float(avg_atr / latest_close * Decimal("100"))
    atr_based_spacing = atr_pct * factor
    spacing_pct = max(tp_range_pct, atr_based_spacing)

    logger.info(
        "Grid spacing calculated",
        extra={
            "tp_range_pct": tp_range_pct,
            "atr_pct": round(atr_pct, 4),
            "avg_atr_pct": round(avg_atr_pct, 4),
            "adaptive_factor": round(factor, 3),
            "spacing_pct": round(spacing_pct, 4),
            "candle_count": candle_count,
        },
    )

    return SpacingResult(
        tp_range_pct=tp_range_pct,
        atr_pct=round(atr_pct, 4),
        avg_atr_pct=round(avg_atr_pct, 4),
        adaptive_factor=round(factor, 3),
        spacing_pct=round(spacing_pct, 4),
        used_fallback=False,
        candle_count=candle_count,
    )
