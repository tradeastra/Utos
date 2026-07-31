"""
CircuitBreakerScreener — batch-screen multiple symbols to derive a per-symbol
critical drop threshold for the daily drop circuit breaker.

For each symbol in a coin group, the screener:
  1. Fetches ``lookback_days`` daily candles from the market hub.
  2. Runs ``DailyDropAnalyzer`` to find the critical drop threshold unique to
     that symbol's historical volatility and continuation behaviour.
  3. Returns a ``{symbol: BreakerScreeningResult}`` map so the caller can
     install a ``CircuitBreakerState`` per grid instance with the right
     threshold.

Why per-symbol screening matters:
  - BTC might have a 4% threshold (low volatility; a 4% drop is significant).
  - A small altcoin might have a 9% threshold (high volatility; 4% is normal).
  Using a single hardcoded threshold would either over-trigger on volatile
  coins (bot never runs) or under-trigger on stable coins (no protection).

The screener fetches candles for all symbols concurrently, so screening a
coin group of 20 symbols takes roughly the same wall-clock time as fetching
one symbol's candles.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from decimal import Decimal

from core.domain_types import Candle
from core.logging import get_logger
from market.base import IMarketHub
from services.daily_drop_analyzer import (
    DEFAULT_CONTINUATION_WINDOW,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_MIN_CONTINUATION_RATE,
    DEFAULT_MIN_FUTURE_DROP_PCT,
    DEFAULT_MIN_SAMPLES,
    TIER_CONFIGS,
    DailyDropAnalyzer,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class BreakerScreeningResult:
    """Result of screening a single symbol for its critical drop threshold."""

    symbol: str
    exchange: str
    threshold_pct: Decimal
    min_continuation_rate: Decimal
    continuation_window: int
    min_future_drop_pct: Decimal
    candle_count: int
    used_fallback: bool

    def __str__(self) -> str:
        tag = "fallback" if self.used_fallback else "data-driven"
        return (
            f"{self.symbol}: {self.threshold_pct}% ({tag}, "
            f"{self.candle_count} candles, rate>={self.min_continuation_rate}, "
            f"window={self.continuation_window}d, future>={self.min_future_drop_pct}%)"
        )


@dataclass
class ScreenerConfig:
    """Configuration for the circuit breaker screener.

    For the 3 standard tiers (Protective/Balanced/Fearless), use
    ``ScreenerConfig.for_tier(rate)`` which auto-fills window and
    future_drop from ``TIER_CONFIGS``.
    """

    exchange: str = "binance"
    interval: str = "1d"
    lookback_days: int = DEFAULT_LOOKBACK_DAYS
    min_continuation_rate: Decimal = DEFAULT_MIN_CONTINUATION_RATE
    min_samples: int = DEFAULT_MIN_SAMPLES
    continuation_window: int = DEFAULT_CONTINUATION_WINDOW
    min_future_drop_pct: Decimal = DEFAULT_MIN_FUTURE_DROP_PCT
    # Cap concurrent candle fetches to avoid rate-limiting the exchange.
    max_concurrency: int = 5

    @classmethod
    def for_tier(cls, rate: Decimal, **overrides) -> "ScreenerConfig":
        """Build config for a standard tier (0.70/0.80/0.90).

        Auto-fills ``continuation_window`` and ``min_future_drop_pct`` from
        ``TIER_CONFIGS``. Pass overrides for exchange/lookback/etc.
        """
        window, future_drop = TIER_CONFIGS.get(
            rate, (DEFAULT_CONTINUATION_WINDOW, DEFAULT_MIN_FUTURE_DROP_PCT)
        )
        return cls(
            min_continuation_rate=rate,
            continuation_window=window,
            min_future_drop_pct=future_drop,
            **overrides,
        )


class CircuitBreakerScreener:
    """Screen multiple symbols and derive a per-symbol critical drop threshold.

    The screener is a thin orchestration layer over ``DailyDropAnalyzer`` and
    ``IMarketHub``. It does not install breakers itself — the caller (e.g. the
    grid engine or a startup hook) is responsible for taking the results and
    calling ``GridEngine.configure_circuit_breaker`` per instance.

    Usage::

        screener = CircuitBreakerScreener(market_hub)
        results = await screener.screen(
            symbols=["BTCUSDT", "ETHUSDT", "DOGEUSDT"],
            config=ScreenerConfig(min_continuation_rate=Decimal("0.90")),
        )
        for symbol, result in results.items():
            grid_engine.configure_circuit_breaker(
                instance_id=...,
                critical_threshold=result.threshold_pct,
                min_continuation_rate=result.min_continuation_rate,
            )
    """

    def __init__(
        self,
        market_hub: IMarketHub,
        analyzer: DailyDropAnalyzer | None = None,
    ) -> None:
        self._hub = market_hub
        self._analyzer = analyzer or DailyDropAnalyzer()

    async def screen(
        self,
        symbols: list[str],
        config: ScreenerConfig | None = None,
    ) -> dict[str, BreakerScreeningResult]:
        """Screen a list of symbols and return per-symbol thresholds.

        Args:
            symbols: List of trading symbols (e.g. ``["BTCUSDT", "ETHUSDT"]``).
            config: Screener configuration. Defaults to ``ScreenerConfig()``.

        Returns:
            Map of ``{symbol: BreakerScreeningResult}``. Symbols that fail to
            fetch candles are still included with a fallback threshold and
            ``used_fallback=True``.
        """
        cfg = config or ScreenerConfig()
        # Bound concurrency to avoid hammering the exchange.
        sem = asyncio.Semaphore(max(1, cfg.max_concurrency))

        async def _screen_one(symbol: str) -> tuple[str, BreakerScreeningResult]:
            async with sem:
                return symbol, await self._screen_symbol(symbol, cfg)

        pairs = await asyncio.gather(
            *(_screen_one(s) for s in symbols),
            return_exceptions=False,
        )
        return dict(pairs)

    async def screen_one(
        self,
        symbol: str,
        config: ScreenerConfig | None = None,
    ) -> BreakerScreeningResult:
        """Screen a single symbol. Convenience wrapper around ``screen``."""
        cfg = config or ScreenerConfig()
        return await self._screen_symbol(symbol, cfg)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _screen_symbol(
        self,
        symbol: str,
        cfg: ScreenerConfig,
    ) -> BreakerScreeningResult:
        """Fetch daily candles for one symbol and run the analyzer."""
        candles: list[Candle] = []
        fetch_error: Exception | None = None
        try:
            candles = await self._hub.get_candles(
                cfg.exchange, symbol.upper(), cfg.interval
            )
        except Exception as exc:  # noqa: BLE001 — log and fallback
            fetch_error = exc
            logger.warning(
                "Failed to fetch candles for breaker screening",
                extra={
                    "symbol": symbol,
                    "exchange": cfg.exchange,
                    "error": str(exc),
                },
            )

        if fetch_error is not None or not candles:
            # Use the analyzer's fallback by passing empty data.
            fallback_threshold = self._analyzer._fallback(cfg.min_continuation_rate)
            logger.info(
                "Using fallback threshold (no candles)",
                extra={
                    "symbol": symbol,
                    "threshold": str(fallback_threshold),
                },
            )
            return BreakerScreeningResult(
                symbol=symbol.upper(),
                exchange=cfg.exchange,
                threshold_pct=fallback_threshold,
                min_continuation_rate=cfg.min_continuation_rate,
                continuation_window=cfg.continuation_window,
                min_future_drop_pct=cfg.min_future_drop_pct,
                candle_count=0,
                used_fallback=True,
            )

        # Trim to the requested lookback window (most recent N candles).
        # The market hub may return more or fewer than lookback_days.
        if len(candles) > cfg.lookback_days:
            candles = candles[-cfg.lookback_days:]

        result = self._analyzer.analyze_detailed(
            candles,
            min_continuation_rate=cfg.min_continuation_rate,
            min_samples=cfg.min_samples,
            continuation_window=cfg.continuation_window,
            min_future_drop_pct=cfg.min_future_drop_pct,
        )

        logger.info(
            "Breaker screening complete",
            extra={
                "symbol": symbol,
                "threshold": str(result.threshold_pct),
                "candles": len(candles),
                "used_fallback": result.used_fallback,
                "drop_events": result.drop_events,
                "continued_events": result.continued_events,
            },
        )
        return BreakerScreeningResult(
            symbol=symbol.upper(),
            exchange=cfg.exchange,
            threshold_pct=result.threshold_pct,
            min_continuation_rate=cfg.min_continuation_rate,
            continuation_window=cfg.continuation_window,
            min_future_drop_pct=cfg.min_future_drop_pct,
            candle_count=len(candles),
            used_fallback=result.used_fallback,
        )
