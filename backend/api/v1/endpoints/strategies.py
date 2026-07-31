"""Strategies endpoints — list available trading strategies."""

from typing import Any

from api.dependencies import get_current_user_token
from core.exceptions import SymbolNotSupported
from database.base import get_db
from fastapi import APIRouter, Depends, HTTPException, Query, status
from models.strategy import Strategy
from pydantic import BaseModel
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


@router.get("/modes", response_model=list[dict[str, Any]])
async def list_strategy_modes(
    current_user: dict = Depends(get_current_user_token),
):
    """List all strategy modes with TP range for grid auto-calculation.

    Returns mode, label, tp_range_min/max, and risk_level.
    The tp_range_max is the take-profit target per grid level. Grid spacing
    is auto-calculated from ATR(14) + adaptive factor via the
    ``/api/v1/grid-spacing/{symbol}`` endpoint — it is no longer a fixed
    value per mode.
    """
    from services.strategy_mode_store import get_strategy_modes
    return await get_strategy_modes()


class GridSpacingResponse(BaseModel):
    """Auto-calculated grid spacing for a symbol + mode combination."""

    symbol: str
    exchange: str
    mode: str
    tp_range_pct: float
    atr_pct: float
    avg_atr_pct: float
    adaptive_factor: float
    spacing_pct: float
    used_fallback: bool
    candle_count: int


def _get_market_hub():
    """Return the singleton MarketHub instance."""
    from main import market_hub

    if market_hub is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Market Hub is not initialized",
        )
    return market_hub


async def _tp_range_for_mode(mode: str) -> float:
    """Look up tp_range_max for a strategy mode (DB-backed with cache)."""
    from services.strategy_mode_store import get_tp_range_max

    try:
        return await get_tp_range_max(mode)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy mode {mode.upper()} not found",
        )


@router.get("/grid-spacing/{symbol}", response_model=GridSpacingResponse)
async def get_grid_spacing(
    symbol: str,
    mode: str = Query(..., description="Strategy mode (A, B, C, D, U)."),
    exchange: str = Query("binance", description="Exchange name."),
    current_user: dict = Depends(get_current_user_token),
) -> GridSpacingResponse:
    """Auto-calculate grid spacing from ATR(14) + adaptive factor.

    Fetches daily candles for the symbol, computes ATR(14) and an adaptive
    factor based on current vs average volatility, then returns:

        spacing_pct = max(tp_range_pct, atr_pct × adaptive_factor)

    The frontend uses ``spacing_pct`` to auto-calculate grid_count:
        grid_count = (upper - lower) / (midpoint × spacing_pct / 100)
    """
    from services.atr_calculator import calculate_spacing

    tp_range = await _tp_range_for_mode(mode)
    hub = _get_market_hub()

    # Coin groups store base symbols (BTC, ETH) but the market hub trades
    # XXXUSDT pairs, so normalize the incoming symbol to a full trading pair
    # before fetching candles (mirrors the convention in main.py breaker
    # screening). Accept already-qualified symbols like "BTCUSDT" as-is.
    pair = symbol.upper()
    if not pair.endswith("USDT"):
        pair = pair + "USDT"

    try:
        candles = await hub.get_candles(exchange, pair, "1d")
    except SymbolNotSupported:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Symbol {pair} not found on {exchange}",
        )

    result = calculate_spacing(tp_range, candles)

    return GridSpacingResponse(
        symbol=pair,
        exchange=exchange.lower(),
        mode=mode.upper(),
        tp_range_pct=result.tp_range_pct,
        atr_pct=result.atr_pct,
        avg_atr_pct=result.avg_atr_pct,
        adaptive_factor=result.adaptive_factor,
        spacing_pct=result.spacing_pct,
        used_fallback=result.used_fallback,
        candle_count=result.candle_count,
    )
