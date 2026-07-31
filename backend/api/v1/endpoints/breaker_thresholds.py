"""Breaker thresholds endpoints — user-facing, read-only.

Any authenticated user can read pre-computed circuit breaker thresholds
for a symbol. This is used by the setup wizard to show the threshold
preview table when a user picks a symbol and continuation rate.

Admin-only operations (list all, re-screen, health summary) live under
``/api/v1/admin/breaker-thresholds``.
"""

from typing import Any

from api.v1.endpoints.users import get_current_user_from_token
from database.base import get_db
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from repositories.breaker_threshold_repository import BreakerThresholdRepository
from schemas.auth import UserResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


def _threshold_to_dict(t) -> dict[str, Any]:
    return {
        "id": str(t.id),
        "exchange": t.exchange,
        "symbol": t.symbol,
        "min_continuation_rate": float(t.min_continuation_rate),
        "threshold_pct": float(t.threshold_pct),
        "continuation_window": t.continuation_window,
        "min_future_drop_pct": float(t.min_future_drop_pct),
        "lookback_days": t.lookback_days,
        "candle_count": t.candle_count,
        "used_fallback": t.used_fallback,
        "resume_mode": t.resume_mode,
        "recovery_pct": float(t.recovery_pct),
        "widen_multiplier": float(t.widen_multiplier),
        "note": t.note,
        "screened_at": t.screened_at.isoformat() if t.screened_at else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


@router.get("/{symbol}", response_model=list[dict])
async def get_breaker_thresholds(
    symbol: str,
    rate: float | None = Query(None, description="Filter by continuation rate (e.g. 0.90)."),
    exchange: str = Query("binance", description="Exchange name."),
    user: UserResponse = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get pre-computed breaker threshold(s) for a symbol.

    Returns all rates for the symbol, or a single-rate list if ``rate``
    is provided. Any authenticated user can call this — thresholds are
    shared across all users (they're per-symbol, not per-user).
    """
    repo = BreakerThresholdRepository(db)
    if rate is not None:
        row = await repo.get_threshold(exchange, symbol.upper(), rate)
        if row is None:
            return []
        return [_threshold_to_dict(row)]
    # All rates for this symbol.
    from sqlalchemy import select
    from models.breaker_threshold import BreakerThreshold
    stmt = (
        select(BreakerThreshold)
        .where(
            BreakerThreshold.exchange == exchange.lower(),
            BreakerThreshold.symbol == symbol.upper(),
        )
        .order_by(BreakerThreshold.min_continuation_rate)
    )
    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    return [_threshold_to_dict(t) for t in rows]
