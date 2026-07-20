"""Strategies endpoints — list available trading strategies."""

from typing import Any

from api.dependencies import get_current_user_token
from database.base import get_db
from fastapi import APIRouter, Depends
from models.strategy import Strategy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


async def _ensure_default_strategies(db: AsyncSession):
    """Seed default strategies if none exist."""
    result = await db.execute(select(Strategy))
    if result.scalars().first():
        return

    defaults = [
        Strategy(
            name="Smart Grid",
            type="smart_grid",
            description="Adaptive grid trading with dynamic spacing",
            min_investment=10.0,
            max_investment=100000.0,
            is_active=True,
        ),
        Strategy(
            name="Adaptive Grid",
            type="adaptive_grid",
            description="Grid that adjusts to volatility",
            min_investment=50.0,
            max_investment=100000.0,
            is_active=True,
        ),
        Strategy(
            name="Infinity Grid",
            type="infinity_grid",
            description="Grid without upper bound for uptrend markets",
            min_investment=100.0,
            max_investment=100000.0,
            is_active=True,
        ),
    ]
    for s in defaults:
        db.add(s)
    await db.commit()


@router.get("/", response_model=list[dict[str, Any]])
async def list_strategies(
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    """List all active strategies (seeds defaults if empty)."""
    await _ensure_default_strategies(db)
    result = await db.execute(
        select(Strategy).where(Strategy.is_active == True)  # noqa: E712
    )
    strategies = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "type": s.type,
            "description": s.description,
            "min_investment": float(s.min_investment),
            "max_investment": float(s.max_investment) if s.max_investment else None,
        }
        for s in strategies
    ]
