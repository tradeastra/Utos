"""
Unit tests for DailyDropAnalyzer — find the critical intraday drop threshold
from historical daily candles using multi-day continuation with proportional
future drop multiplier (3× daily drop).

Algorithm under test (defaults: continuation_window=5, future_drop_multiplier=3):
  1. For each day i with a daily drop, look ahead `continuation_window` days.
  2. A drop event "continues" if the future decline >= multiplier × |daily_drop|.
     E.g. a 3% drop needs >= 9% future decline; a 5% drop needs >= 15%.
  3. For each candidate threshold T (1%..15%): collect days with drop >= T%,
     compute continuation_rate = #(continued) / #(drop events).
  4. Return the first T whose continuation_rate >= min_continuation_rate.

Test data design: each test uses min_samples=1 for simplicity. Patterns are
built so that:
  - "Killer" drops (small, recover) have future closes that go back up.
  - "Target" drops (continue) have future closes that decline by >= 3× the
    daily drop. The sharp future decline is placed at the end of the pattern
    (outside the drop-event range) to avoid creating polluting drop events.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from core.domain_types import Candle
from services.daily_drop_analyzer import DailyDropAnalyzer


def _candle(close: Decimal, days_ago: int = 0, symbol: str = "BTCUSDT") -> Candle:
    ts = datetime.now(UTC) - timedelta(days=days_ago)
    return Candle(
        symbol=symbol, interval="1d", open=close, high=close, low=close,
        close=close, volume=Decimal("1000"), timestamp=ts,
    )


def _candles_from_closes(closes: list[Decimal]) -> list[Candle]:
    n = len(closes)
    return [_candle(c, days_ago=n - i - 1) for i, c in enumerate(closes)]


def _killer(drop_pct: Decimal, window: int = 5) -> list[Decimal]:
    """A drop that recovers — future close goes back to 100.

    Pattern: [100, 100*(1-d), 100, 100, ...] with enough candles for the window.
    The drop day is at index 1, future close (at index 1+window) = 100 (recovery).
    """
    drop_price = Decimal("100") * (Decimal("1") - drop_pct / Decimal("100"))
    padding = [Decimal("100")] * window
    return [Decimal("100"), drop_price] + padding


def _continue(drop_pct: Decimal, window: int = 5, future_drop: Decimal = Decimal("9.0")) -> list[Decimal]:
    """A drop that continues — future decline >= future_drop within window.

    Pattern: [100, 100*(1-d), plateau, ..., sharp_drop]
    The plateau keeps intermediate drops at 0% (no pollution).
    The sharp drop at the end is outside the drop-event range.
    Future close = drop_price × (1 - future_drop/100).
    """
    drop_price = Decimal("100") * (Decimal("1") - drop_pct / Decimal("100"))
    future_close = drop_price * (Decimal("1") - future_drop / Decimal("100"))
    # Plateau at drop_price for (window-1) days, then sharp drop.
    plateau = [drop_price] * (window - 1)
    return [Decimal("100"), drop_price] + plateau + [future_close]


class TestDailyDropAnalyzer:
    def setup_method(self) -> None:
        self.analyzer = DailyDropAnalyzer()

    def test_insufficient_data_returns_fallback(self) -> None:
        result = self.analyzer.analyze(
            _candles_from_closes([Decimal("100"), Decimal("95"), Decimal("90")]),
            min_continuation_rate=Decimal("0.80"),
        )
        assert result == Decimal("4.0")

    def test_fallback_differs_by_continuation_rate(self) -> None:
        candles = _candles_from_closes([Decimal("100")] * 3)
        assert self.analyzer.analyze(candles, min_continuation_rate=Decimal("0.70")) == Decimal("3.0")
        assert self.analyzer.analyze(candles, min_continuation_rate=Decimal("0.80")) == Decimal("4.0")
        assert self.analyzer.analyze(candles, min_continuation_rate=Decimal("0.90")) == Decimal("5.0")

    def test_multi_day_continuation_finds_threshold(self) -> None:
        # window=5, multiplier=3 (default).
        # Killers: 1%, 2%, 2.5% drops recover (future = 100).
        # Target: 3% drop continues (future decline >= 9%).
        w = 5
        closes: list[Decimal] = []
        closes += _killer(Decimal("1"), w)
        closes += _killer(Decimal("2"), w)
        closes += _killer(Decimal("2.5"), w)
        closes += _continue(Decimal("3"), w)
        candles = _candles_from_closes(closes)
        result = self.analyzer.analyze(
            candles, min_continuation_rate=Decimal("0.90"),
            min_samples=1, continuation_window=w,
        )
        assert result == Decimal("3.0")

    def test_intra_window_bounce_still_counts_as_continuation(self) -> None:
        # window=5, multiplier=3.
        # 4% drop: 100->96. Future decline needs >= 12% from 96 → future <= 84.48.
        # Pattern: [100, 96, 96, 96, 96, 96, 84] — plateau then sharp drop.
        # Killer 3.5%: recovers to 100.
        w = 5
        closes: list[Decimal] = []
        closes += _killer(Decimal("3.5"), w)
        closes += _continue(Decimal("4"), w)
        candles = _candles_from_closes(closes)
        result = self.analyzer.analyze(
            candles, min_continuation_rate=Decimal("0.90"),
            min_samples=1, continuation_window=w,
        )
        assert result == Decimal("4.0")

    def test_shallow_future_drop_does_not_count_as_continuation(self) -> None:
        # KEY test: 3% drop with only 5% future decline → NOT continued (need 9%).
        # 5% drop with 15%+ future decline → continued.
        # Pattern for 3% shallow: [100, 97, 97, 97, 97, 97, 92.15]
        #   future decline = (97-92.15)/97 = 5% < 9% → NOT continued
        # Pattern for 5% continue: [100, 95, 95, 95, 95, 95, 80.75]
        #   future decline = (95-80.75)/95 = 15% >= 15% → continued
        w = 5
        # 3% drop, only 5% future decline (NOT enough, need 9%)
        shallow = [Decimal("100"), Decimal("97"), Decimal("97"), Decimal("97"),
                   Decimal("97"), Decimal("97"), Decimal("92.15")]
        # 5% drop, 15% future decline (enough)
        deep = _continue(Decimal("5"), w)
        candles = _candles_from_closes(shallow + deep)
        # 3% threshold: 1 event (shallow), 0 continued → 0% → no qualify
        # 5% threshold: 1 event (deep), 1 continued → 100% → qualify at 90%
        result = self.analyzer.analyze(
            candles, min_continuation_rate=Decimal("0.90"),
            min_samples=1, continuation_window=w,
        )
        assert result == Decimal("5.0")

    def test_low_future_drop_threshold_is_permissive(self) -> None:
        # With min_future_drop_pct=4, a 4% drop with 4%+ future decline counts.
        # Killers at 1%, 2%, 3%, 3.5% recover (so lower thresholds don't qualify).
        w = 5
        closes: list[Decimal] = []
        closes += _killer(Decimal("1"), w)
        closes += _killer(Decimal("2"), w)
        closes += _killer(Decimal("3"), w)
        closes += _killer(Decimal("3.5"), w)
        closes += _continue(Decimal("4"), w, future_drop=Decimal("4.1"))
        candles = _candles_from_closes(closes)

        result = self.analyzer.analyze(
            candles, min_continuation_rate=Decimal("0.90"),
            min_samples=1, continuation_window=w,
            min_future_drop_pct=Decimal("4"),
        )
        assert result == Decimal("4.0")

        # With default future_drop=9: 4.1% < 9% → NOT continued → fallback
        result_default = self.analyzer.analyze(
            candles, min_continuation_rate=Decimal("0.90"),
            min_samples=1, continuation_window=w,
        )
        assert result_default == Decimal("5.0")  # fallback for 0.90

    def test_higher_continuation_rate_yields_larger_or_equal_threshold(self) -> None:
        # 3% drop continues (9%+ future decline). Killers at 1%, 2%, 2.5% recover.
        # With min_samples=1, all rates should find threshold 3.0%.
        w = 5
        closes: list[Decimal] = []
        closes += _killer(Decimal("1"), w)
        closes += _killer(Decimal("2"), w)
        closes += _killer(Decimal("2.5"), w)
        closes += _continue(Decimal("3"), w)
        candles = _candles_from_closes(closes)

        for rate in [Decimal("0.70"), Decimal("0.80"), Decimal("0.90")]:
            result = self.analyzer.analyze(
                candles, min_continuation_rate=rate, min_samples=1,
                continuation_window=w,
            )
            assert result == Decimal("3.0")

        flat = _candles_from_closes([Decimal("100")] * 3)
        fb_70 = self.analyzer.analyze(flat, min_continuation_rate=Decimal("0.70"))
        fb_90 = self.analyzer.analyze(flat, min_continuation_rate=Decimal("0.90"))
        assert fb_70 < fb_90

    def test_no_threshold_qualifies_returns_fallback(self) -> None:
        # All drops recover (no continuation).
        w = 5
        closes: list[Decimal] = []
        closes += _killer(Decimal("3"), w)
        closes += _killer(Decimal("5"), w)
        candles = _candles_from_closes(closes)
        result = self.analyzer.analyze(
            candles, min_continuation_rate=Decimal("0.90"),
            min_samples=1, continuation_window=w,
        )
        assert result == Decimal("5.0")  # fallback for 0.90

    def test_threshold_is_positive_decimal(self) -> None:
        w = 5
        candles = _candles_from_closes(_continue(Decimal("3"), w))
        result = self.analyzer.analyze(
            candles, min_continuation_rate=Decimal("0.70"),
            min_samples=1, continuation_window=w,
        )
        assert isinstance(result, Decimal)
        assert result > 0

    def test_default_window_is_5(self) -> None:
        from services.daily_drop_analyzer import DEFAULT_CONTINUATION_WINDOW
        assert DEFAULT_CONTINUATION_WINDOW == 5

    def test_custom_window_changes_required_data_length(self) -> None:
        # window=3: need >= 5 candles. window=10: need >= 12 candles.
        short = _candles_from_closes([Decimal("100")] * 5)
        result_short = self.analyzer.analyze(
            short, min_continuation_rate=Decimal("0.80"),
            continuation_window=3,
        )
        assert result_short == Decimal("4.0")  # fallback (no drops)

        too_short = _candles_from_closes([Decimal("100")] * 5)
        result_too_short = self.analyzer.analyze(
            too_short, min_continuation_rate=Decimal("0.80"),
            continuation_window=10,
        )
        assert result_too_short == Decimal("4.0")  # fallback (insufficient data)

    def test_tier_configs_defined(self) -> None:
        from services.daily_drop_analyzer import TIER_CONFIGS
        assert TIER_CONFIGS[Decimal("0.70")] == (5, Decimal("9.0"))
        assert TIER_CONFIGS[Decimal("0.80")] == (10, Decimal("12.0"))
        assert TIER_CONFIGS[Decimal("0.90")] == (30, Decimal("15.0"))

    def test_higher_future_drop_requires_larger_threshold(self) -> None:
        # With future_drop=6: 3% drop with 6.1% future decline counts.
        # Killers at 1%, 2%, 2.5% recover so lower thresholds don't qualify.
        w = 5
        closes: list[Decimal] = []
        closes += _killer(Decimal("1"), w)
        closes += _killer(Decimal("2"), w)
        closes += _killer(Decimal("2.5"), w)
        closes += _continue(Decimal("3"), w, future_drop=Decimal("6.1"))
        candles = _candles_from_closes(closes)

        result = self.analyzer.analyze(
            candles, min_continuation_rate=Decimal("0.90"),
            min_samples=1, continuation_window=w,
            min_future_drop_pct=Decimal("6"),
        )
        assert result == Decimal("3.0")

        # With future_drop=9: 6.1% < 9% → NOT continued → fallback
        result_9 = self.analyzer.analyze(
            candles, min_continuation_rate=Decimal("0.90"),
            min_samples=1, continuation_window=w,
            min_future_drop_pct=Decimal("9"),
        )
        assert result_9 == Decimal("5.0")  # fallback
