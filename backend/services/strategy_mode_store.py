"""Strategy mode store — DB-backed strategy mode definitions with fallback.

This module is the single source of truth for strategy mode configuration
at runtime. It replaces the former hardcoded ``STRATEGY_MODES_CONFIG``
list in ``api.v1.endpoints.admin``.

Behaviour:
  * Reads pull from the ``strategy_modes`` table (seeded by Alembic
    migration 0012). If the table is empty or the DB is unreachable,
    we fall back to ``DEFAULT_STRATEGY_MODES`` so the API still works
    before/without migration.
  * A small in-process cache avoids hitting the DB on every
    ``grid-spacing`` request. The cache is invalidated whenever an
    admin writes through ``update_strategy_mode``.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.base import get_db, get_engine
from models.strategy_mode import StrategyMode

logger = logging.getLogger(__name__)


# Must stay in sync with Alembic migration 0012 and the former
# STRATEGY_MODES_CONFIG in api.v1.endpoints.admin.
DEFAULT_STRATEGY_MODES: list[dict[str, Any]] = [
    {"mode": "A", "label": "Hyper",       "tp_range_min": 0.0, "tp_range_max": 0.3, "risk_level": "Very Aggressive",
     "description": "Tightest grid (0.3% spacing). Maximum trade frequency — many small profits, fast capital rotation. Best for ranging markets. TP 0.75% per level."},
    {"mode": "B", "label": "Aggressive",  "tp_range_min": 0.0, "tp_range_max": 0.6, "risk_level": "Aggressive",
     "description": "Tight grid (0.6% spacing). High trade frequency with moderate profit per level. Good for normal volatility. TP 1.5% per level."},
    {"mode": "C", "label": "Balanced",    "tp_range_min": 0.0, "tp_range_max": 0.9, "risk_level": "Balanced",
     "description": "Moderate grid (0.9% spacing). Balanced trade frequency and profit. General-purpose mode. TP 2.25% per level."},
]


# ─── In-process cache ────────────────────────────────────────────────
_cache: list[dict[str, Any]] | None = None
_cache_lock = asyncio.Lock()


def _row_to_dict(sm: StrategyMode) -> dict[str, Any]:
    return {
        "mode": sm.mode,
        "label": sm.label,
        "tp_range_min": float(sm.tp_range_min),
        "tp_range_max": float(sm.tp_range_max),
        "risk_level": sm.risk_level,
        "description": sm.description,
        "is_active": sm.is_active,
        "sort_order": sm.sort_order,
    }


async def _load_from_db(session: AsyncSession) -> list[dict[str, Any]]:
    result = await session.execute(
        select(StrategyMode)
        .where(StrategyMode.is_active == True)  # noqa: E712
        .order_by(StrategyMode.sort_order, StrategyMode.mode)
    )
    rows = list(result.scalars().all())
    if not rows:
        # Table exists but is empty (e.g. migration not yet run on this
        # env). Fall back to defaults so the API still responds.
        return list(DEFAULT_STRATEGY_MODES)
    return [_row_to_dict(r) for r in rows]


async def load_strategy_modes() -> list[dict[str, Any]]:
    """Return all strategy modes, preferring the DB, falling back to defaults.

    Uses an in-process cache to avoid a DB round-trip on every call.
    The cache is invalidated by ``update_strategy_mode``.
    """
    global _cache
    if _cache is not None:
        return _cache

    async with _cache_lock:
        if _cache is not None:
            return _cache
        try:
            factory = get_engine()
            # Use a fresh short-lived session independent of any request
            # so this works from background tasks too.
            from sqlalchemy.ext.asyncio import async_sessionmaker

            session_factory = async_sessionmaker(factory, expire_on_commit=False)
            async with session_factory() as session:
                _cache = await _load_from_db(session)
        except Exception as exc:  # noqa: BLE001
            logger.warning("strategy_mode_store: DB load failed, using defaults: %s", exc)
            _cache = list(DEFAULT_STRATEGY_MODES)
        return _cache


async def get_strategy_modes() -> list[dict[str, Any]]:
    """Public alias for ``load_strategy_modes``."""
    return await load_strategy_modes()


async def get_tp_range_max(mode: str) -> float:
    """Return ``tp_range_max`` for the given mode code (case-insensitive)."""
    modes = await load_strategy_modes()
    mode_upper = mode.upper()
    for sm in modes:
        if sm["mode"] == mode_upper:
            return float(sm["tp_range_max"])
    raise ValueError(f"Strategy mode {mode_upper} not found")


async def update_strategy_mode(
    mode: str,
    *,
    label: str | None = None,
    tp_range_min: float | None = None,
    tp_range_max: float | None = None,
    risk_level: str | None = None,
    description: str | None = None,
) -> dict[str, Any] | None:
    """Persist updated fields for a strategy mode and invalidate the cache.

    Returns the updated mode dict, or ``None`` if the mode was not found.
    """
    mode_upper = mode.upper()

    # Use the request-scoped session via get_db dependency is not possible
    # here (we're not inside a request), so create a short-lived session.
    factory = get_engine()
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(factory, expire_on_commit=False)
    async with session_factory() as session:
        result = await session.execute(
            select(StrategyMode).where(StrategyMode.mode == mode_upper)
        )
        sm = result.scalar_one_or_none()
        if sm is None:
            return None

        if label is not None:
            sm.label = label
        if tp_range_min is not None:
            sm.tp_range_min = tp_range_min
        if tp_range_max is not None:
            sm.tp_range_max = tp_range_max
        if risk_level is not None:
            sm.risk_level = risk_level
        if description is not None:
            sm.description = description

        await session.commit()
        await session.refresh(sm)
        updated = _row_to_dict(sm)

    # Invalidate cache so subsequent reads see the new value.
    global _cache
    _cache = None
    return updated


async def update_strategy_mode_with_session(
    session: AsyncSession,
    mode: str,
    *,
    label: str | None = None,
    tp_range_min: float | None = None,
    tp_range_max: float | None = None,
    risk_level: str | None = None,
    description: str | None = None,
) -> dict[str, Any] | None:
    """Persist updated fields using the caller's session (used by admin endpoint)."""
    mode_upper = mode.upper()
    result = await session.execute(
        select(StrategyMode).where(StrategyMode.mode == mode_upper)
    )
    sm = result.scalar_one_or_none()
    if sm is None:
        return None

    if label is not None:
        sm.label = label
    if tp_range_min is not None:
        sm.tp_range_min = tp_range_min
    if tp_range_max is not None:
        sm.tp_range_max = tp_range_max
    if risk_level is not None:
        sm.risk_level = risk_level
    if description is not None:
        sm.description = description

    await session.flush()
    await session.refresh(sm)
    updated = _row_to_dict(sm)

    # Invalidate cache so subsequent reads see the new value.
    global _cache
    _cache = None
    return updated


def invalidate_cache() -> None:
    """Drop the in-process cache (next read reloads from DB)."""
    global _cache
    _cache = None
