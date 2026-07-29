"""
BreakerScreeningStore — the app's "source of truth" for circuit breaker
thresholds across all supported trading pairs.

This service bridges the CircuitBreakerScreener (which analyzes historical
candles) and the BreakerThresholdRepository (which persists results). It
provides two main operations:

  1. ``rescreen_all()`` — fetch candles for every symbol in a coin group (or
     an explicit list), run DailyDropAnalyzer per symbol, and upsert the
     results into the database. Intended to run on app startup and
     periodically (e.g. daily) as a background task.

  2. ``get_threshold(symbol, rate)`` — read a pre-computed threshold from the
     database. Called by the grid engine when a user applies a strategy /
     starts a trading instance. If no row exists yet, falls back to the
     analyzer's conservative default (so the bot is never unprotected).

Architecture::

    ┌──────────────────────────────────────────────────────────┐
    │                  BreakerScreeningStore                    │
    │                                                          │
    │  rescreen_all(symbols)          get_threshold(symbol)     │
    │       ↓                              ↓                    │
    │  CircuitBreakerScreener        BreakerThresholdRepository │
    │       ↓                              ↓                    │
    │  DailyDropAnalyzer              breaker_thresholds table  │
    │       ↓                              ↑                    │
    │  MarketHub (candles)            ──────┘                   │
    └──────────────────────────────────────────────────────────┘

Why a store instead of screening on-demand?
  - Screening 50 symbols fetches 50 × 365 candles — slow and rate-limit-heavy.
  - Users start/stop instances frequently; re-screening each time is wasteful.
  - A nightly background re-screen keeps thresholds fresh without blocking
    user-facing operations.
  - All users share the same thresholds (they're per-symbol, not per-user),
    so caching in the DB is efficient.
"""

from __future__ import annotations

from decimal import Decimal

from core.logging import get_logger
from market.base import IMarketHub
from repositories.breaker_threshold_repository import BreakerThresholdRepository
from services.circuit_breaker_screener import (
    BreakerScreeningResult,
    CircuitBreakerScreener,
    ScreenerConfig,
)
from services.daily_drop_analyzer import DailyDropAnalyzer, TIER_CONFIGS
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class BreakerScreeningStore:
    """Persistent store of per-symbol circuit breaker thresholds.

    Usage::

        store = BreakerScreeningStore(market_hub)

        # Background task (startup / nightly):
        await store.rescreen_all(
            db=session,
            symbols=["BTCUSDT", "ETHUSDT", ...],
            config=ScreenerConfig(min_continuation_rate=Decimal("0.90")),
        )

        # When user applies a strategy:
        threshold = await store.get_threshold(
            db=session, symbol="BTCUSDT",
            min_continuation_rate=Decimal("0.90"),
        )
        grid_engine.configure_circuit_breaker(
            instance_id=..., critical_threshold=threshold,
        )
    """

    def __init__(
        self,
        market_hub: IMarketHub,
        screener: CircuitBreakerScreener | None = None,
    ) -> None:
        self._hub = market_hub
        self._screener = screener or CircuitBreakerScreener(market_hub)
        self._analyzer = DailyDropAnalyzer()

    async def rescreen_all(
        self,
        db: AsyncSession,
        symbols: list[str],
        config: ScreenerConfig | None = None,
    ) -> dict[str, BreakerScreeningResult]:
        """Screen all symbols and persist results to the database.

        Args:
            db: Async database session (for upserting results).
            symbols: List of trading symbols to screen.
            config: Screener configuration. Defaults to ``ScreenerConfig()``.

        Returns:
            Map of ``{symbol: BreakerScreeningResult}`` (same as
            ``CircuitBreakerScreener.screen``).
        """
        cfg = config or ScreenerConfig()
        results = await self._screener.screen(symbols, config=cfg)

        repo = BreakerThresholdRepository(db)
        for symbol, result in results.items():
            await repo.upsert(
                exchange=result.exchange,
                symbol=result.symbol,
                min_continuation_rate=result.min_continuation_rate,
                threshold_pct=result.threshold_pct,
                continuation_window=result.continuation_window,
                min_future_drop_pct=result.min_future_drop_pct,
                lookback_days=cfg.lookback_days,
                candle_count=result.candle_count,
                used_fallback=result.used_fallback,
            )
        await db.commit()

        logger.info(
            "Breaker screening store: rescreened all symbols",
            extra={
                "symbol_count": len(results),
                "exchange": cfg.exchange,
                "min_continuation_rate": str(cfg.min_continuation_rate),
                "fallback_count": sum(1 for r in results.values() if r.used_fallback),
            },
        )
        return results

    async def rescreen_for_rates(
        self,
        db: AsyncSession,
        symbols: list[str],
        rates: list[Decimal],
        base_config: ScreenerConfig | None = None,
    ) -> dict[Decimal, dict[str, BreakerScreeningResult]]:
        """Screen all symbols for multiple continuation rates.

        Since users can pick 70% / 80% / 90%, we pre-compute thresholds for
        all three rates so the store has every variant ready.

        Args:
            db: Async database session.
            symbols: List of trading symbols.
            rates: List of continuation rates (e.g. [0.70, 0.80, 0.90]).
            base_config: Base screener config; ``min_continuation_rate`` will
                be overridden per rate.

        Returns:
            ``{rate: {symbol: BreakerScreeningResult}}``.
        """
        base = base_config or ScreenerConfig()
        all_results: dict[Decimal, dict[str, BreakerScreeningResult]] = {}
        for rate in rates:
            # Use tier-specific window + future_drop from TIER_CONFIGS,
            # but allow base_config overrides (e.g. exchange, lookback).
            window, future_drop = TIER_CONFIGS.get(
                rate, (base.continuation_window, base.min_future_drop_pct)
            )
            cfg = ScreenerConfig(
                exchange=base.exchange,
                interval=base.interval,
                lookback_days=base.lookback_days,
                min_continuation_rate=rate,
                min_samples=base.min_samples,
                continuation_window=window,
                min_future_drop_pct=future_drop,
                max_concurrency=base.max_concurrency,
            )
            results = await self.rescreen_all(db, symbols, config=cfg)
            all_results[rate] = results
        return all_results

    async def get_threshold(
        self,
        db: AsyncSession,
        symbol: str,
        min_continuation_rate: Decimal,
        exchange: str = "binance",
    ) -> Decimal:
        """Read a pre-computed threshold from the database.

        If no row exists (e.g. screening hasn't run yet), returns the
        analyzer's conservative fallback so the bot is never unprotected.

        Args:
            db: Async database session.
            symbol: Trading symbol (e.g. "BTCUSDT").
            min_continuation_rate: Continuation rate (0.70 / 0.80 / 0.90).
            exchange: Exchange name.

        Returns:
            Critical drop threshold as a positive Decimal percentage.
        """
        repo = BreakerThresholdRepository(db)
        row = await repo.get_threshold(exchange, symbol, min_continuation_rate)
        if row is not None:
            logger.info(
                "Breaker threshold loaded from store",
                extra={
                    "symbol": symbol,
                    "threshold": str(row.threshold_pct),
                    "used_fallback": row.used_fallback,
                    "screened_at": str(row.screened_at),
                },
            )
            return Decimal(str(row.threshold_pct))

        # No row — use analyzer fallback (never leave the bot unprotected).
        fallback = self._analyzer._fallback(min_continuation_rate)
        logger.warning(
            "No breaker threshold in store; using fallback",
            extra={
                "symbol": symbol,
                "fallback": str(fallback),
                "min_continuation_rate": str(min_continuation_rate),
            },
        )
        return fallback

    async def get_all_thresholds(
        self,
        db: AsyncSession,
        min_continuation_rate: Decimal,
        exchange: str | None = None,
    ) -> dict[str, Decimal]:
        """Return all cached thresholds for a given continuation rate.

        Useful for the UI to display the screening results table.

        Returns:
            ``{symbol: threshold_pct}`` map.
        """
        repo = BreakerThresholdRepository(db)
        rows = await repo.get_all_for_rate(min_continuation_rate, exchange=exchange)
        return {row.symbol: Decimal(str(row.threshold_pct)) for row in rows}

    async def get_breaker_config(
        self,
        db: AsyncSession,
        symbol: str,
        min_continuation_rate: Decimal,
        exchange: str = "binance",
    ) -> dict[str, object]:
        """Read the full breaker config (threshold + resume behavior) from DB.

        Returns a dict suitable for passing as kwargs to
        ``GridEngine.configure_circuit_breaker``::

            cfg = await store.get_breaker_config(db, "BTCUSDT", Decimal("0.90"))
            grid_engine.configure_circuit_breaker(
                instance_id=..., critical_threshold=cfg["critical_threshold"],
                resume_mode=cfg["resume_mode"], ...
            )

        If no row exists, returns fallback threshold + legacy defaults
        (ta_confirm / 5% / 2×) so the bot is never unprotected.

        Returns:
            Dict with keys: ``critical_threshold`` (Decimal), ``resume_mode``
            (str), ``recovery_pct`` (Decimal), ``widen_multiplier`` (Decimal),
            ``min_continuation_rate`` (Decimal), ``used_fallback`` (bool).
        """
        from engine.grid.circuit_breaker import (
            DEFAULT_RECOVERY_PCT,
            DEFAULT_WIDEN_MULTIPLIER,
            BreakerResumeMode,
        )

        repo = BreakerThresholdRepository(db)
        row = await repo.get_threshold(exchange, symbol, min_continuation_rate)
        if row is not None:
            # Validate resume_mode against the enum; fall back to default
            # if the stored value is unknown (e.g. from a future/old schema).
            try:
                mode = BreakerResumeMode(row.resume_mode)
            except ValueError:
                mode = BreakerResumeMode.TA_CONFIRM
            return {
                "critical_threshold": Decimal(str(row.threshold_pct)),
                "resume_mode": mode,
                "recovery_pct": Decimal(str(row.recovery_pct)),
                "widen_multiplier": Decimal(str(row.widen_multiplier)),
                "min_continuation_rate": Decimal(str(row.min_continuation_rate)),
                "used_fallback": bool(row.used_fallback),
            }

        # No row — use analyzer fallback + legacy defaults.
        fallback = self._analyzer._fallback(min_continuation_rate)
        logger.warning(
            "No breaker threshold in store; using fallback config",
            extra={
                "symbol": symbol,
                "fallback": str(fallback),
                "min_continuation_rate": str(min_continuation_rate),
            },
        )
        return {
            "critical_threshold": fallback,
            "resume_mode": BreakerResumeMode.TA_CONFIRM,
            "recovery_pct": DEFAULT_RECOVERY_PCT,
            "widen_multiplier": DEFAULT_WIDEN_MULTIPLIER,
            "min_continuation_rate": min_continuation_rate,
            "used_fallback": True,
        }

    async def setup_breaker_for_instance(
        self,
        db: AsyncSession,
        grid_engine,
        instance_id: str,
        symbol: str,
        min_continuation_rate: Decimal,
        exchange: str = "binance",
        day_open_price: Decimal | None = None,
    ) -> dict[str, object]:
        """Read the full breaker config from DB and install it on the grid engine.

        Convenience wrapper that combines ``get_breaker_config`` +
        ``GridEngine.configure_circuit_breaker``. Use this when activating a
        trading instance so the breaker is configured with the correct
        threshold AND resume behavior (resume_mode / recovery_pct /
        widen_multiplier) in one call.

        Args:
            db: Async database session.
            grid_engine: The GridEngine instance to configure.
            instance_id: Trading instance id (used as the breaker key).
            symbol: Trading symbol (e.g. "BTCUSDT").
            min_continuation_rate: Continuation rate (0.70 / 0.80 / 0.90).
            exchange: Exchange name.
            day_open_price: Optional price at the start of the current UTC day.
                If None, the next price update will seed it.

        Returns:
            The config dict from ``get_breaker_config`` (for logging/audit).
        """
        cfg = await self.get_breaker_config(
            db=db,
            symbol=symbol,
            min_continuation_rate=min_continuation_rate,
            exchange=exchange,
        )
        grid_engine.configure_circuit_breaker(
            instance_id=instance_id,
            critical_threshold=cfg["critical_threshold"],
            min_continuation_rate=cfg["min_continuation_rate"],
            resume_mode=cfg["resume_mode"],
            recovery_pct=cfg["recovery_pct"],
            widen_multiplier=cfg["widen_multiplier"],
            day_open_price=day_open_price,
        )
        logger.info(
            "Breaker configured for instance",
            extra={
                "instance_id": instance_id,
                "symbol": symbol,
                "critical_threshold": str(cfg["critical_threshold"]),
                "resume_mode": cfg["resume_mode"].value,
                "recovery_pct": str(cfg["recovery_pct"]),
                "widen_multiplier": str(cfg["widen_multiplier"]),
                "used_fallback": cfg["used_fallback"],
            },
        )
        return cfg
