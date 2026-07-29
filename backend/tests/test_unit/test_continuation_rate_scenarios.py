"""
Skenario Continuation Rate untuk 1 coin (BTCUSDT) — 3 tier demo.

Menunjukkan bagaimana DailyDropAnalyzer menghasilkan threshold drop kritis yang
BERBEDA untuk satu coin yang sama ketika user memilih continuation rate yang
berbeda. Tiga tier standar (lihat TIER_CONFIGS di daily_drop_analyzer.py):

  ┌──────────────┬──────┬─────────┬────────────────┬──────────────────────┐
  │ Tier         │ Rate │ Window  │ Future decline │ Arti                  │
  ├──────────────┼──────┼─────────┼────────────────┼──────────────────────┤
  │ Protective   │ 70%  │ 5 hari  │ ≥ 9%           │ Stop averaging awal   │
  │ Balanced     │ 80%  │ 10 hari │ ≥ 12%          │ Jalan tengah          │
  │ Patient      │ 90%  │ 30 hari │ ≥ 15%          │ Terus averaging lama  │
  └──────────────┴──────┴─────────┴────────────────┴──────────────────────┘

Setiap skenario membangun candle harian BTCUSDT buatan dengan pola:
  - "Killer" drop (kecil, lalu recover ke 100) → tidak continue.
  - "Target" drop (besar, lalu turun >= future_decline dalam window) → continue.

Threshold kritis = drop % terkecil yang continuation_rate-nya >= min_rate.
Tier yang lebih tinggi (90%) butuh bukti historis lebih kuat → threshold lebih
besar → breaker trigger lebih lambat → bot tetap averaging lebih lama.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from core.domain_types import Candle
from services.daily_drop_analyzer import (
    TIER_CONFIGS,
    DailyDropAnalyzer,
)

SYMBOL = "BTCUSDT"


# ---------------------------------------------------------------------------
# Helpers — bangun candle dari deretan close price.
# ---------------------------------------------------------------------------

def _candle(close: Decimal, days_ago: int = 0) -> Candle:
    ts = datetime.now(UTC) - timedelta(days=days_ago)
    return Candle(
        symbol=SYMBOL, interval="1d", open=close, high=close, low=close,
        close=close, volume=Decimal("1000"), timestamp=ts,
    )


def _candles_from_closes(closes: list[Decimal]) -> list[Candle]:
    n = len(closes)
    return [_candle(c, days_ago=n - i - 1) for i, c in enumerate(closes)]


def _killer(drop_pct: Decimal, window: int) -> list[Decimal]:
    """Drop yang recover — future close kembali ke 100.

    Pola: [100, 100*(1-d), 100, 100, ...] sepanjang window.
    Drop day di index 1, future close (index 1+window) = 100 (recovery).
    """
    drop_price = Decimal("100") * (Decimal("1") - drop_pct / Decimal("100"))
    padding = [Decimal("100")] * window
    return [Decimal("100"), drop_price] + padding


def _continue(
    drop_pct: Decimal, window: int, future_drop: Decimal
) -> list[Decimal]:
    """Drop yang continue — future decline >= future_drop dalam window.

    Pola: [100, 100*(1-d), plateau, ..., sharp_drop].
    Plateau menjaga drop antara = 0% (tidak polusi drop event lain).
    Future close = drop_price × (1 - future_drop/100).
    """
    drop_price = Decimal("100") * (Decimal("1") - drop_pct / Decimal("100"))
    future_close = drop_price * (Decimal("1") - future_drop / Decimal("100"))
    plateau = [drop_price] * (window - 1)
    return [Decimal("100"), drop_price] + plateau + [future_close]


def _continue_gradual(
    drop_pct: Decimal, window: int, future_drop: Decimal
) -> list[Decimal]:
    """Drop yang continue dengan decline GRADUAL — tidak ada sharp drop.

    Berbeda dari ``_continue``: decline dari drop_price ke future_close
    diinterpolasi linear selama ``window`` hari, sehingga daily drop per hari
    kecil (~future_drop/window %) dan TIDAK masuk subset threshold yang
    lebih besar dari step harian. Ini mencegah sharp_drop di akhir pola
    menjadi drop event polluting yang tidak continued.

    Pola: [100, 100*(1-d), gradual_decline_1, ..., gradual_decline_window]
    di mana gradual_decline_window = drop_price × (1 - future_drop/100).
    """
    drop_price = Decimal("100") * (Decimal("1") - drop_pct / Decimal("100"))
    future_close = drop_price * (Decimal("1") - future_drop / Decimal("100"))
    closes: list[Decimal] = []
    for i in range(1, window + 1):
        frac = Decimal(i) / Decimal(window)
        closes.append(drop_price + (future_close - drop_price) * frac)
    return [Decimal("100"), drop_price] + closes


# ---------------------------------------------------------------------------
# Skenario 1 — Protective (70%): window=5 hari, future decline ≥ 9%.
# ---------------------------------------------------------------------------

class TestScenarioProtective70:
    """Tier Protective: trigger paling awal, threshold paling kecil.

    Data BTCUSDT:
      - Killer 1%, 2%, 2.5%: drop kecil lalu recover → tidak continue.
        Killer 2.5% penting agar kandidat threshold 2.5% tidak lolos (rate
        hanya 50% < 70%), sehingga threshold data-driven jatuh di 3.0%.
      - Target 3%: drop 3% lalu turun 9%+ dalam 5 hari → continue.

    Expected: threshold = 3.0% (drop 3% adalah titik kritis untuk tier 70%).
    """

    def setup_method(self) -> None:
        self.analyzer = DailyDropAnalyzer()
        self.window, self.future_drop = TIER_CONFIGS[Decimal("0.70")]
        assert (self.window, self.future_drop) == (5, Decimal("9.0"))

    def _build_candles(self) -> list[Candle]:
        closes: list[Decimal] = []
        closes += _killer(Decimal("1"), self.window)
        closes += _killer(Decimal("2"), self.window)
        closes += _killer(Decimal("2.5"), self.window)
        closes += _continue(Decimal("3"), self.window, self.future_drop)
        return _candles_from_closes(closes)

    def test_protective_threshold_is_3_pct(self) -> None:
        candles = self._build_candles()
        result = self.analyzer.analyze(
            candles,
            min_continuation_rate=Decimal("0.70"),
            min_samples=1,
            continuation_window=self.window,
            min_future_drop_pct=self.future_drop,
        )
        assert result == Decimal("3.0")

    def test_protective_detailed_stats(self) -> None:
        candles = self._build_candles()
        detail = self.analyzer.analyze_detailed(
            candles,
            min_continuation_rate=Decimal("0.70"),
            min_samples=1,
            continuation_window=self.window,
            min_future_drop_pct=self.future_drop,
        )
        # Kandidat 2.5%: subset = {2.5% killer, 3% continue} → 1/2 = 50% < 70%.
        # Kandidat 3.0%: subset = {3% continue} → 1/1 = 100% >= 70% → qualify.
        assert detail.threshold_pct == Decimal("3.0")
        assert detail.used_fallback is False
        assert detail.drop_events == 1
        assert detail.continued_events == 1
        assert detail.continuation_rate == Decimal("1.0")


# ---------------------------------------------------------------------------
# Skenario 2 — Balanced (80%): window=10 hari, future decline ≥ 12%.
# ---------------------------------------------------------------------------

class TestScenarioBalanced80:
    """Tier Balanced: jalan tengah, threshold menengah.

    Data BTCUSDT:
      - Killer 3% & 3.5%: drop lalu recover → tidak continue.
        Killer 3.5% penting agar kandidat threshold 3.5% tidak lolos (rate
        hanya 50% < 80%), sehingga threshold data-driven jatuh di 4.0%.
      - Target 4%: drop 4% lalu turun 12%+ dalam 10 hari → continue.

    Expected: threshold = 4.0% (drop 4% adalah titik kritis untuk tier 80%).
    """

    def setup_method(self) -> None:
        self.analyzer = DailyDropAnalyzer()
        self.window, self.future_drop = TIER_CONFIGS[Decimal("0.80")]
        assert (self.window, self.future_drop) == (10, Decimal("12.0"))

    def _build_candles(self) -> list[Candle]:
        closes: list[Decimal] = []
        closes += _killer(Decimal("3"), self.window)
        closes += _killer(Decimal("3.5"), self.window)
        closes += _continue(Decimal("4"), self.window, self.future_drop)
        return _candles_from_closes(closes)

    def test_balanced_threshold_is_4_pct(self) -> None:
        candles = self._build_candles()
        result = self.analyzer.analyze(
            candles,
            min_continuation_rate=Decimal("0.80"),
            min_samples=1,
            continuation_window=self.window,
            min_future_drop_pct=self.future_drop,
        )
        assert result == Decimal("4.0")

    def test_balanced_killer_3pct_does_not_qualify(self) -> None:
        # Hanya killer 3% (recover) → tidak ada drop yang continue → fallback.
        closes = _killer(Decimal("3"), self.window)
        candles = _candles_from_closes(closes)

        result = self.analyzer.analyze(
            candles,
            min_continuation_rate=Decimal("0.80"),
            min_samples=1,
            continuation_window=self.window,
            min_future_drop_pct=self.future_drop,
        )
        # 3% drop recover → 0% continuation → fallback 4.0% untuk tier 80%.
        assert result == Decimal("4.0")


# ---------------------------------------------------------------------------
# Skenario 3 — Patient (90%): window=30 hari, future decline ≥ 15%.
# ---------------------------------------------------------------------------

class TestScenarioPatient90:
    """Tier Patient: trigger paling lambat, threshold paling besar.

    Data BTCUSDT:
      - Killer 4% & 4.5%: drop lalu recover → tidak continue.
        Killer 4.5% penting agar kandidat threshold 4.5% tidak lolos (rate
        hanya 50% < 90%), sehingga threshold data-driven jatuh di 5.0%.
      - Target 5%: drop 5% lalu turun 15%+ dalam 30 hari → continue.

    Expected: threshold = 5.0% (drop 5% adalah titik kritis untuk tier 90%).
    """

    def setup_method(self) -> None:
        self.analyzer = DailyDropAnalyzer()
        self.window, self.future_drop = TIER_CONFIGS[Decimal("0.90")]
        assert (self.window, self.future_drop) == (30, Decimal("15.0"))

    def _build_candles(self) -> list[Candle]:
        closes: list[Decimal] = []
        closes += _killer(Decimal("4"), self.window)
        closes += _killer(Decimal("4.5"), self.window)
        closes += _continue(Decimal("5"), self.window, self.future_drop)
        return _candles_from_closes(closes)

    def test_patient_threshold_is_5_pct(self) -> None:
        candles = self._build_candles()
        result = self.analyzer.analyze(
            candles,
            min_continuation_rate=Decimal("0.90"),
            min_samples=1,
            continuation_window=self.window,
            min_future_drop_pct=self.future_drop,
        )
        assert result == Decimal("5.0")

    def test_patient_killer_4pct_does_not_qualify(self) -> None:
        closes = _killer(Decimal("4"), self.window)
        candles = _candles_from_closes(closes)

        result = self.analyzer.analyze(
            candles,
            min_continuation_rate=Decimal("0.90"),
            min_samples=1,
            continuation_window=self.window,
            min_future_drop_pct=self.future_drop,
        )
        # 4% drop recover → 0% continuation → fallback 5.0% untuk tier 90%.
        assert result == Decimal("5.0")


# ---------------------------------------------------------------------------
# Skenario gabungan — 1 dataset BTCUSDT, 3 tier → 3 threshold berbeda.
# ---------------------------------------------------------------------------

class TestSingleCoinThreeTiers:
    """Satu dataset candle BTCUSDT, dijalankan dengan 3 tier config (bundled).

    NOTE — BUKAN apple-to-apple: tiap tier di TIER_CONFIGS mengikat 3 parameter
    sekaligus (rate, window, future_decline). Jadi ketika threshold berbeda
    (3% / 4% / 5%), kita TIDAK bisa mengklaim perbedaannya murni karena
    continuation rate — window & future_decline juga berubah. Test ini hanya
    menunjukkan perilaku tier default yang user pilih di UI.

    Untuk perbandingan apple-to-apple (hanya rate berubah), lihat
    ``TestApplesToApplesRateOnly`` di bawah.
    """

    def setup_method(self) -> None:
        self.analyzer = DailyDropAnalyzer()

    @pytest.mark.parametrize(
        "rate,expected",
        [
            (Decimal("0.70"), Decimal("3.0")),
            (Decimal("0.80"), Decimal("4.0")),
            (Decimal("0.90"), Decimal("5.0")),
        ],
        ids=["protective-70", "balanced-80", "patient-90"],
    )
    def test_three_tiers_yield_three_thresholds(
        self, rate: Decimal, expected: Decimal
    ) -> None:
        window, future_drop = TIER_CONFIGS[rate]
        # Bangun dataset: killer kecil + 3 target drop yang continue di tiap tier.
        closes: list[Decimal] = []
        closes += _killer(Decimal("1"), window)
        closes += _killer(Decimal("2"), window)
        closes += _continue(Decimal("3"), window, future_drop)
        closes += _continue(Decimal("4"), window, future_drop)
        closes += _continue(Decimal("5"), window, future_drop)
        candles = _candles_from_closes(closes)

        result = self.analyzer.analyze(
            candles,
            min_continuation_rate=rate,
            min_samples=1,
            continuation_window=window,
            min_future_drop_pct=future_drop,
        )
        assert result == expected


# ---------------------------------------------------------------------------
# Skenario apple-to-apple — window & future_decline FIXED, hanya rate berubah.
# ---------------------------------------------------------------------------
# Test di atas (TestSingleCoinThreeTiers) bukan apple-to-apple karena
# TIER_CONFIGS mengikat rate → window → future_decline bersamaan. Untuk
# benar-benar membuktikan "continuation rate saja yang mengubah threshold",
# kita fix window & future_decline lalu hanya ubah min_continuation_rate.
#
# Dataset BTCUSDT (window=5, future_decline=9% — sama untuk ketiga run):
#   - 3× drop 2% yang continue (future decline 9%+ dalam 5 hari)
#   - 1× drop 2% yang killer (recover ke 100)
# Pada threshold 2.0%: subset = 4 event, 3 continued → continuation rate 75%.
#   - rate 70%: 75% >= 70% → LOLOS → threshold = 2.0%
#   - rate 80%: 75% < 80%  → tidak lolos → fallback 4.0%
#   - rate 90%: 75% < 90%  → tidak lolos → fallback 5.0%
# ---------------------------------------------------------------------------


class TestApplesToApplesRateOnly:
    """Perbandingan apple-to-apple: window & future_decline FIXED, hanya rate berubah.

    Dataset BTCUSDT (window=5, future_decline=9% — sama untuk ketiga run):
      - 3× drop 2% yang continue (future decline 9%+ dalam 5 hari)
      - 1× drop 2% yang killer (recover ke 100)

    Pada threshold 2.0%: subset = 4 event, 3 continued → continuation rate 75%.
      - rate 70%: 75% >= 70% → LOLOS → threshold = 2.0%
      - rate 80%: 75% < 80%  → tidak lolos → fallback 4.0%
      - rate 90%: 75% < 90%  → tidak lolos → fallback 5.0%

    Inilah bukti apple-to-apple: dengan dataset & parameter identik, hanya
    continuation rate yang berubah → threshold berbeda (2.0 / 4.0 / 5.0).
    Rate lebih tinggi = butuh bukti historis lebih kuat = threshold lebih besar
    (atau fallback) = breaker trigger lebih lambat.
    """

    WINDOW = 5
    FUTURE_DROP = Decimal("9.0")

    def setup_method(self) -> None:
        self.analyzer = DailyDropAnalyzer()

    def _build_candles(self) -> list[Candle]:
        closes: list[Decimal] = []
        # 3 drop 2% yang continue (future decline >= 9% dalam 5 hari, gradual
        # decline agar tidak ada sharp drop yang polusi subset threshold).
        closes += _continue_gradual(Decimal("2"), self.WINDOW, self.FUTURE_DROP)
        closes += _continue_gradual(Decimal("2"), self.WINDOW, self.FUTURE_DROP)
        closes += _continue_gradual(Decimal("2"), self.WINDOW, self.FUTURE_DROP)
        # 1 drop 2% yang killer (recover ke 100) → tidak continue.
        closes += _killer(Decimal("2"), self.WINDOW)
        return _candles_from_closes(closes)

    @pytest.mark.parametrize(
        "rate,expected",
        [
            (Decimal("0.70"), Decimal("2.0")),  # 75% >= 70% → lolos di 2.0%
            (Decimal("0.80"), Decimal("4.0")),  # 75% < 80% → fallback
            (Decimal("0.90"), Decimal("5.0")),  # 75% < 90% → fallback
        ],
        ids=["rate-70-loosens", "rate-80-fallback", "rate-90-fallback"],
    )
    def test_same_data_different_rate_yields_different_threshold(
        self, rate: Decimal, expected: Decimal
    ) -> None:
        candles = self._build_candles()
        result = self.analyzer.analyze(
            candles,
            min_continuation_rate=rate,
            min_samples=1,
            continuation_window=self.WINDOW,
            min_future_drop_pct=self.FUTURE_DROP,
        )
        assert result == expected

    def test_apples_to_apples_detailed_stats(self) -> None:
        """Verifikasi continuation rate 75% pada threshold 2.0% (data-driven)."""
        candles = self._build_candles()
        detail = self.analyzer.analyze_detailed(
            candles,
            min_continuation_rate=Decimal("0.70"),
            min_samples=1,
            continuation_window=self.WINDOW,
            min_future_drop_pct=self.FUTURE_DROP,
        )
        assert detail.threshold_pct == Decimal("2.0")
        assert detail.used_fallback is False
        assert detail.drop_events == 4
        assert detail.continued_events == 3
        # 3/4 = 0.75
        assert detail.continuation_rate == Decimal("0.75")
