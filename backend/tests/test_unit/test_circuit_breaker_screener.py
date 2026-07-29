"""
Unit tests for CircuitBreakerScreener — batch-screen multiple symbols to
derive per-symbol critical drop thresholds.

The screener fetches daily candles from a market hub for each symbol, runs
DailyDropAnalyzer, and returns a {symbol: BreakerScreeningResult} map.

Test data uses future_drop_multiplier=3 (default): a drop of X% needs future
decline >= 3×X% within the continuation window to count as "continued".
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from core.domain_types import Candle
from market.base import IMarketHub, MarketMetrics, MarketStatus
from services.circuit_breaker_screener import (
    BreakerScreeningResult,
    CircuitBreakerScreener,
    ScreenerConfig,
)


def _candle(close: Decimal, days_ago: int = 0) -> Candle:
    ts = datetime.now(UTC) - timedelta(days=days_ago)
    return Candle(
        symbol="X", interval="1d", open=close, high=close, low=close,
        close=close, volume=Decimal("1000"), timestamp=ts,
    )


def _candles_from_closes(closes: list[Decimal]) -> list[Candle]:
    n = len(closes)
    return [_candle(c, days_ago=n - i - 1) for i, c in enumerate(closes)]


def _killer(drop_pct: Decimal, window: int = 5) -> list[Decimal]:
    """A drop that recovers — future close goes back to 100."""
    drop_price = Decimal("100") * (Decimal("1") - drop_pct / Decimal("100"))
    padding = [Decimal("100")] * window
    return [Decimal("100"), drop_price] + padding


def _continue(drop_pct: Decimal, window: int = 5, future_drop: Decimal = Decimal("9.0")) -> list[Decimal]:
    """A drop that continues — future decline >= future_drop within window.

    Uses gradual daily decline (each day < drop_pct) to avoid creating
    polluting drop events in the threshold's subset.
    """
    drop_price = Decimal("100") * (Decimal("1") - drop_pct / Decimal("100"))
    future_close = drop_price * (Decimal("1") - future_drop / Decimal("100"))
    # Gradual decline: interpolate from drop_price to future_close over window days.
    closes: list[Decimal] = []
    for i in range(1, window + 1):
        frac = Decimal(i) / Decimal(window)
        c = drop_price + (future_close - drop_price) * frac
        closes.append(c)
    return [Decimal("100"), drop_price] + closes


class FakeMarketHub(IMarketHub):
    """In-memory market hub that returns pre-canned candles per symbol."""

    def __init__(self, candle_map: dict[str, list[Candle]] | None = None) -> None:
        self._candle_map = candle_map or {}
        self._fail_symbols: set[str] = set()

    def set_candles(self, symbol: str, candles: list[Candle]) -> None:
        self._candle_map[symbol.upper()] = candles

    def fail_symbol(self, symbol: str) -> None:
        self._fail_symbols.add(symbol.upper())

    async def get_candles(self, exchange: str, symbol: str, interval: str) -> list[Candle]:
        sym = symbol.upper()
        if sym in self._fail_symbols:
            raise RuntimeError(f"simulated fetch failure for {sym}")
        candles = self._candle_map.get(sym)
        if candles is None:
            raise RuntimeError(f"no candles for {sym}")
        return candles

    # --- unused IMarketHub methods (stubs) ---
    async def subscribe(self, *a, **kw): ...
    async def unsubscribe(self, *a, **kw): ...
    async def get_price(self, *a, **kw): return Decimal("0")
    async def get_ticker(self, *a, **kw): ...
    async def get_orderbook(self, *a, **kw): ...
    async def is_alive(self, *a, **kw): return True
    async def get_status(self, *a, **kw): return MarketStatus.CONNECTED
    async def get_metrics(self, *a, **kw): return MarketMetrics(exchange="x", symbol="y")
    async def start(self): ...
    async def stop(self): ...


def _btc_like_candles() -> list[Candle]:
    """365 candles where 4% drops all continue (low volatility coin).

    With multiplier=3, window=5, a 4% drop needs >= 12% future decline.
    Killers at 1%, 2%, 3%, 3.5% recover to prevent lower thresholds qualifying.
    """
    w = 5
    closes: list[Decimal] = []
    closes += [Decimal("100")] * 20
    # Killers (recover)
    for _ in range(3):
        closes += _killer(Decimal("1"), w)
    for _ in range(3):
        closes += _killer(Decimal("2"), w)
    for _ in range(3):
        closes += _killer(Decimal("3"), w)
    for _ in range(3):
        closes += _killer(Decimal("3.5"), w)
    # 4% drops continue (future decline >= 12%)
    for _ in range(3):
        closes += _continue(Decimal("4"), w)
    closes += [Decimal("100")] * (365 - len(closes))
    return _candles_from_closes(closes)


def _doge_like_candles() -> list[Candle]:
    """365 candles where 8% drops all continue (high volatility coin).

    With multiplier=3, window=5, an 8% drop needs >= 24% future decline.
    Killers at 4%, 5%, 6%, 7%, 7.5% recover.
    """
    w = 5
    closes: list[Decimal] = []
    closes += [Decimal("100")] * 20
    # Killers (recover)
    for _ in range(3):
        closes += _killer(Decimal("4"), w)
    for _ in range(3):
        closes += _killer(Decimal("5"), w)
    for _ in range(3):
        closes += _killer(Decimal("6"), w)
    for _ in range(3):
        closes += _killer(Decimal("7"), w)
    for _ in range(3):
        closes += _killer(Decimal("7.5"), w)
    # 8% drops continue (future decline >= 24%)
    for _ in range(3):
        closes += _continue(Decimal("8"), w)
    closes += [Decimal("100")] * (365 - len(closes))
    return _candles_from_closes(closes)


class TestCircuitBreakerScreener:
    def setup_method(self) -> None:
        self.hub = FakeMarketHub()
        self.hub.set_candles("BTCUSDT", _btc_like_candles())
        self.hub.set_candles("DOGEUSDT", _doge_like_candles())
        self.screener = CircuitBreakerScreener(self.hub)

    @pytest.mark.asyncio
    async def test_screen_returns_per_symbol_threshold(self) -> None:
        results = await self.screener.screen(
            ["BTCUSDT", "DOGEUSDT"],
            config=ScreenerConfig(
                min_continuation_rate=Decimal("0.90"),
                continuation_window=5,
                min_samples=3,
            ),
        )
        assert "BTCUSDT" in results
        assert "DOGEUSDT" in results
        btc = results["BTCUSDT"]
        doge = results["DOGEUSDT"]
        # BTC should have a lower threshold than DOGE (less volatile)
        assert btc.threshold_pct < doge.threshold_pct
        assert btc.candle_count > 0
        assert doge.candle_count > 0

    @pytest.mark.asyncio
    async def test_screen_different_thresholds_per_symbol(self) -> None:
        # BTC has 4% drops that continue; DOGE has only 8% drops that continue.
        # DOGE's threshold should be strictly higher than BTC's.
        results = await self.screener.screen(
            ["BTCUSDT", "DOGEUSDT"],
            config=ScreenerConfig(
                min_continuation_rate=Decimal("0.90"),
                continuation_window=5,
                min_samples=3,
            ),
        )
        btc = results["BTCUSDT"]
        doge = results["DOGEUSDT"]
        # BTC: 4% drops continue -> threshold 4.0
        assert btc.threshold_pct == Decimal("4.0")
        # DOGE: threshold must be higher than BTC
        assert doge.threshold_pct > btc.threshold_pct

    @pytest.mark.asyncio
    async def test_screen_handles_fetch_failure_with_fallback(self) -> None:
        self.hub.fail_symbol("ETHUSDT")
        results = await self.screener.screen(
            ["ETHUSDT"],
            config=ScreenerConfig(min_continuation_rate=Decimal("0.90")),
        )
        eth = results["ETHUSDT"]
        assert eth.used_fallback is True
        assert eth.candle_count == 0
        # Fallback for 0.90 is 5.0%
        assert eth.threshold_pct == Decimal("5.0")

    @pytest.mark.asyncio
    async def test_screen_handles_empty_candle_list(self) -> None:
        self.hub.set_candles("EMPTYUSDT", [])
        results = await self.screener.screen(
            ["EMPTYUSDT"],
            config=ScreenerConfig(min_continuation_rate=Decimal("0.80")),
        )
        empty = results["EMPTYUSDT"]
        assert empty.used_fallback is True
        assert empty.candle_count == 0
        assert empty.threshold_pct == Decimal("4.0")  # fallback for 0.80

    @pytest.mark.asyncio
    async def test_screen_trims_to_lookback_days(self) -> None:
        # Provide 500 candles; lookback=365 should trim to 365.
        closes = [Decimal("100")] * 500
        self.hub.set_candles("LONGUSDT", _candles_from_closes(closes))
        results = await self.screener.screen(
            ["LONGUSDT"],
            config=ScreenerConfig(
                lookback_days=365,
                min_continuation_rate=Decimal("0.80"),
            ),
        )
        assert results["LONGUSDT"].candle_count == 365

    @pytest.mark.asyncio
    async def test_screen_one_single_symbol(self) -> None:
        result = await self.screener.screen_one(
            "BTCUSDT",
            config=ScreenerConfig(
                min_continuation_rate=Decimal("0.90"),
                continuation_window=5,
                min_samples=3,
            ),
        )
        assert result.symbol == "BTCUSDT"
        assert result.threshold_pct == Decimal("4.0")

    @pytest.mark.asyncio
    async def test_screen_result_contains_full_metadata(self) -> None:
        results = await self.screener.screen(
            ["BTCUSDT"],
            config=ScreenerConfig(
                min_continuation_rate=Decimal("0.90"),
                continuation_window=5,
                min_samples=3,
            ),
        )
        btc = results["BTCUSDT"]
        assert btc.exchange == "binance"
        assert btc.min_continuation_rate == Decimal("0.90")
        assert btc.continuation_window == 5
        assert btc.min_future_drop_pct == Decimal("9.0")
        assert btc.candle_count > 0
        assert btc.used_fallback is False

    @pytest.mark.asyncio
    async def test_screen_concurrency_does_not_corrupt_results(self) -> None:
        # Screen 5 symbols all with the same BTC-like data.
        for i in range(5):
            self.hub.set_candles(f"COIN{i}USDT", _btc_like_candles())
        results = await self.screener.screen(
            [f"COIN{i}USDT" for i in range(5)],
            config=ScreenerConfig(
                min_continuation_rate=Decimal("0.90"),
                continuation_window=5,
                min_samples=3,
                max_concurrency=2,
            ),
        )
        # All should have the same threshold (4.0%) since data is identical.
        for i in range(5):
            assert results[f"COIN{i}USDT"].threshold_pct == Decimal("4.0")

    @pytest.mark.asyncio
    async def test_screen_result_str_representation(self) -> None:
        result = await self.screener.screen_one(
            "BTCUSDT",
            config=ScreenerConfig(
                min_continuation_rate=Decimal("0.90"),
                continuation_window=5,
                min_samples=3,
            ),
        )
        s = str(result)
        assert "BTCUSDT" in s
        assert "4.0%" in s
        assert "future>=9" in s
