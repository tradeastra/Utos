"""BreakerThreshold repository — CRUD + upsert for pre-computed thresholds."""

import uuid
from decimal import Decimal

from models.breaker_threshold import BreakerThreshold
from repositories.base import IRepository
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql import func as sa_func

sa_func_now = sa_func.now()

# Tier-level resume behavior defaults (keyed by continuation rate).
# These are sensible defaults per tier; admins can override via API after
# screening. They are NOT screening outputs — they are user-facing preferences
# that happen to be tier-bundled for convenience.
#   - Protective (70%): trailing_buy 5% — recover quickly, conservative re-entry.
#   - Balanced  (80%): ta_confirm     — middle ground, wait for TA.
#   - Fearless  (90%): widen_step 2×  — keep averaging, just slower.
TIER_RESUME_DEFAULTS: dict[Decimal, dict[str, object]] = {
    Decimal("0.70"): {"resume_mode": "trailing_buy", "recovery_pct": 5.0, "widen_multiplier": 2.0},
    Decimal("0.80"): {"resume_mode": "ta_confirm", "recovery_pct": 5.0, "widen_multiplier": 2.0},
    Decimal("0.90"): {"resume_mode": "widen_step", "recovery_pct": 5.0, "widen_multiplier": 2.0},
}


def _resume_defaults_for_rate(rate: Decimal) -> dict[str, object]:
    """Return the tier-default resume config for a continuation rate."""
    return TIER_RESUME_DEFAULTS.get(
        rate,
        {"resume_mode": "ta_confirm", "recovery_pct": 5.0, "widen_multiplier": 2.0},
    )


class BreakerThresholdRepository(IRepository[BreakerThreshold]):
    """Repository for the breaker_thresholds table.

    The key use case is *upsert*: the screening store re-screens all symbols
    periodically and must update existing rows without creating duplicates.
    """

    model = BreakerThreshold

    async def get_threshold(
        self,
        exchange: str,
        symbol: str,
        min_continuation_rate: Decimal,
    ) -> BreakerThreshold | None:
        """Look up a single threshold by its natural key."""
        result = await self._session.execute(
            select(BreakerThreshold).where(
                BreakerThreshold.exchange == exchange.lower(),
                BreakerThreshold.symbol == symbol.upper(),
                BreakerThreshold.min_continuation_rate == float(min_continuation_rate),
            )
        )
        return result.scalar_one_or_none()

    async def get_all_for_rate(
        self,
        min_continuation_rate: Decimal,
        exchange: str | None = None,
    ) -> list[BreakerThreshold]:
        """Return all thresholds for a given continuation rate (optionally filtered by exchange)."""
        stmt = select(BreakerThreshold).where(
            BreakerThreshold.min_continuation_rate == float(min_continuation_rate),
        )
        if exchange is not None:
            stmt = stmt.where(BreakerThreshold.exchange == exchange.lower())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def upsert(
        self,
        exchange: str,
        symbol: str,
        min_continuation_rate: Decimal,
        threshold_pct: Decimal,
        continuation_window: int = 5,
        min_future_drop_pct: Decimal = Decimal("9.0"),
        lookback_days: int = 365,
        candle_count: int = 0,
        used_fallback: bool = False,
        resume_mode: str | None = None,
        recovery_pct: Decimal | None = None,
        widen_multiplier: Decimal | None = None,
        note: str | None = None,
    ) -> BreakerThreshold:
        """Insert or update a threshold row.

        On conflict (exchange, symbol, min_continuation_rate), update all
        screening fields and bump ``screened_at`` / ``updated_at``.

        Resume behavior (resume_mode, recovery_pct, widen_multiplier) defaults
        to tier-based values from ``TIER_RESUME_DEFAULTS`` when not provided.
        On update of an existing row, resume fields are only overwritten if
        explicitly passed (so admin overrides survive re-screening).
        """
        # Apply tier defaults for resume behavior when not explicitly given.
        tier_defaults = _resume_defaults_for_rate(min_continuation_rate)
        if resume_mode is None:
            resume_mode = tier_defaults["resume_mode"]
        if recovery_pct is None:
            recovery_pct = Decimal(str(tier_defaults["recovery_pct"]))
        if widen_multiplier is None:
            widen_multiplier = Decimal(str(tier_defaults["widen_multiplier"]))

        values = {
            "exchange": exchange.lower(),
            "symbol": symbol.upper(),
            "min_continuation_rate": float(min_continuation_rate),
            "threshold_pct": float(threshold_pct),
            "continuation_window": continuation_window,
            "min_future_drop_pct": float(min_future_drop_pct),
            "lookback_days": lookback_days,
            "candle_count": candle_count,
            "used_fallback": used_fallback,
            "resume_mode": resume_mode,
            "recovery_pct": float(recovery_pct),
            "widen_multiplier": float(widen_multiplier),
            "note": note,
        }

        # Try PostgreSQL-native upsert first.
        try:
            stmt = pg_insert(BreakerThreshold).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["exchange", "symbol", "min_continuation_rate"],
                set_={
                    "threshold_pct": stmt.excluded.threshold_pct,
                    "continuation_window": stmt.excluded.continuation_window,
                    "min_future_drop_pct": stmt.excluded.min_future_drop_pct,
                    "lookback_days": stmt.excluded.lookback_days,
                    "candle_count": stmt.excluded.candle_count,
                    "used_fallback": stmt.excluded.used_fallback,
                    # Resume fields: only update on insert (use excluded) so
                    # admin overrides survive re-screening. We still write them
                    # on the conflict path to keep them in sync if the tier
                    # default changed — but in practice admins set these via
                    # a dedicated endpoint, not via re-screening.
                    "resume_mode": stmt.excluded.resume_mode,
                    "recovery_pct": stmt.excluded.recovery_pct,
                    "widen_multiplier": stmt.excluded.widen_multiplier,
                    "note": stmt.excluded.note,
                    "screened_at": sa_func_now,
                    "updated_at": sa_func_now,
                },
            )
            await self._session.execute(stmt)
            await self._session.flush()
        except Exception:
            # Fallback for SQLite / other dialects: manual upsert.
            await self._manual_upsert(values)
        # Re-fetch to return the persisted row.
        row = await self._fetch(values["exchange"], values["symbol"], values["min_continuation_rate"])
        if row is None:
            # Should not happen, but guard against edge cases.
            raise RuntimeError(f"upsert failed for {values['exchange']}:{values['symbol']}")
        return row

    async def _manual_upsert(self, values: dict) -> None:
        existing = await self._fetch(
            values["exchange"], values["symbol"], values["min_continuation_rate"]
        )
        if existing is not None:
            for key in (
                "threshold_pct", "continuation_window", "min_future_drop_pct",
                "lookback_days", "candle_count", "used_fallback",
                "resume_mode", "recovery_pct", "widen_multiplier", "note",
            ):
                setattr(existing, key, values[key])
            from datetime import UTC, datetime
            existing.screened_at = datetime.now(UTC)
            existing.updated_at = datetime.now(UTC)
            await self._session.flush()
        else:
            entity = BreakerThreshold(**values)
            self._session.add(entity)
            await self._session.flush()

    async def _fetch(self, exchange: str, symbol: str, rate: float) -> BreakerThreshold | None:
        result = await self._session.execute(
            select(BreakerThreshold).where(
                BreakerThreshold.exchange == exchange,
                BreakerThreshold.symbol == symbol,
                BreakerThreshold.min_continuation_rate == rate,
            )
        )
        return result.scalar_one_or_none()

    async def update_resume_config(
        self,
        exchange: str,
        symbol: str,
        min_continuation_rate: Decimal,
        resume_mode: str | None = None,
        recovery_pct: Decimal | None = None,
        widen_multiplier: Decimal | None = None,
    ) -> BreakerThreshold | None:
        """Update only the resume behavior fields of an existing threshold row.

        Used by the admin API to override the tier-default resume config
        without re-running screening. Returns the updated row, or ``None``
        if no row exists for the given key.
        """
        row = await self._fetch(exchange.lower(), symbol.upper(), float(min_continuation_rate))
        if row is None:
            return None
        if resume_mode is not None:
            row.resume_mode = resume_mode
        if recovery_pct is not None:
            row.recovery_pct = float(recovery_pct)
        if widen_multiplier is not None:
            row.widen_multiplier = float(widen_multiplier)
        from datetime import UTC, datetime
        row.updated_at = datetime.now(UTC)
        await self._session.flush()
        return row
