"""Admin endpoints — manage coin groups, MM presets, strategy modes.

All endpoints require admin role.
Admins can create, update, delete, and toggle built-in and custom resources.
"""

from decimal import Decimal
from typing import Any
from uuid import UUID

from api.v1.endpoints.users import require_admin
from database.base import get_db
from fastapi import APIRouter, Depends, HTTPException, Query, status
from models.coin_group import CoinGroup
from models.mm_preset import MMPreset
from pydantic import BaseModel, ConfigDict, Field
from repositories.breaker_threshold_repository import BreakerThresholdRepository
from repositories.coin_group_repository import CoinGroupRepository
from repositories.mm_preset_repository import MMPresetRepository
from schemas.auth import UserResponse
from services.averaging_template import get_default_averaging_summary, get_default_averaging_template
from services.breaker_screening_store import BreakerScreeningStore
from services.circuit_breaker_screener import ScreenerConfig
from services.mm_calculator import BUILTIN_PRESETS
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


def _get_market_hub():
    """Return the singleton MarketHub instance (lazy import to avoid circulars)."""
    from main import market_hub

    if market_hub is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Market Hub is not initialized",
        )
    return market_hub


# ─── Coin Group Admin ───────────────────────────────────────────────

class CoinGroupUpdate(BaseModel):
    name: str | None = Field(None, max_length=50)
    description: str | None = Field(None, max_length=200)
    max_coins: int | None = Field(None, ge=1)
    coins: list[str] | None = None
    is_active: bool | None = None


class CoinGroupCreate(BaseModel):
    name: str = Field(..., max_length=50)
    description: str | None = None
    max_coins: int = Field(..., ge=1)
    coins: list[str] = []
    is_builtin: bool = False


@router.get("/coin-groups", response_model=list[dict])
async def admin_list_coin_groups(
    admin: UserResponse = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List ALL coin groups (including inactive)."""
    repo = CoinGroupRepository(db)
    all_groups = await repo.get_all(limit=500)
    return [
        {
            "id": str(g.id),
            "name": g.name,
            "description": g.description,
            "max_coins": g.max_coins,
            "coins": g.coins or [],
            "is_builtin": g.is_builtin,
            "is_active": g.is_active,
            "user_id": str(g.user_id) if g.user_id else None,
        }
        for g in all_groups
    ]


@router.post("/coin-groups", response_model=dict, status_code=status.HTTP_201_CREATED)
async def admin_create_coin_group(
    data: CoinGroupCreate,
    admin: UserResponse = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a coin group (admin can create built-in groups too)."""
    repo = CoinGroupRepository(db)
    group = await repo.create(
        name=data.name,
        description=data.description,
        max_coins=data.max_coins,
        coins=[c.upper() for c in data.coins],
        is_builtin=data.is_builtin,
        is_active=True,
        user_id=None if data.is_builtin else admin.id,
    )
    return {
        "id": str(group.id),
        "name": group.name,
        "max_coins": group.max_coins,
        "coins": group.coins or [],
        "is_builtin": group.is_builtin,
        "is_active": group.is_active,
    }


@router.put("/coin-groups/{group_id}", response_model=dict)
async def admin_update_coin_group(
    group_id: str,
    data: CoinGroupUpdate,
    admin: UserResponse = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update any coin group (including built-in)."""
    repo = CoinGroupRepository(db)
    group = await repo.get_by_id(UUID(group_id))
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coin group not found")

    update_data = data.model_dump(exclude_none=True)
    if "coins" in update_data and update_data["coins"] is not None:
        update_data["coins"] = [c.upper() for c in update_data["coins"]]

    group = await repo.update(group, **update_data)
    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "max_coins": group.max_coins,
        "coins": group.coins or [],
        "is_builtin": group.is_builtin,
        "is_active": group.is_active,
    }


@router.delete("/coin-groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_coin_group(
    group_id: str,
    admin: UserResponse = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete any coin group (including built-in)."""
    repo = CoinGroupRepository(db)
    group = await repo.get_by_id(UUID(group_id))
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coin group not found")
    await repo.delete(group)


# ─── MM Preset Admin ────────────────────────────────────────────────

class MMPresetUpdate(BaseModel):
    name: str | None = Field(None, max_length=50)
    steps: int | None = Field(None, ge=1, le=200)
    min_capital: float | None = Field(None, gt=0)
    max_capital: float | None = Field(None, gt=0)
    description: str | None = None
    allowed_coin_groups: list[str] | None = None
    is_active: bool | None = None


class MMPresetCreate(BaseModel):
    name: str = Field(..., max_length=50)
    preset_type: str = Field(..., description="mm30, mm50, mm70, or custom")
    steps: int = Field(..., ge=1, le=200)
    min_capital: float = Field(..., gt=0)
    max_capital: float | None = None
    description: str | None = None
    allowed_coin_groups: list[str] | None = None
    is_builtin: bool = False


@router.get("/mm-presets", response_model=list[dict])
async def admin_list_mm_presets(
    admin: UserResponse = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List ALL MM presets (including inactive)."""
    repo = MMPresetRepository(db)
    all_presets = await repo.get_all(limit=500)
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "preset_type": p.preset_type,
            "steps": p.steps,
            "min_capital": str(p.min_capital),
            "max_capital": str(p.max_capital) if p.max_capital else None,
            "description": p.description,
            "allowed_coin_groups": p.allowed_coin_groups or [],
            "is_builtin": p.is_builtin,
            "is_active": p.is_active,
            "user_id": str(p.user_id) if p.user_id else None,
        }
        for p in all_presets
    ]


@router.post("/mm-presets", response_model=dict, status_code=status.HTTP_201_CREATED)
async def admin_create_mm_preset(
    data: MMPresetCreate,
    admin: UserResponse = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create an MM preset (admin can create built-in presets too)."""
    repo = MMPresetRepository(db)
    preset = await repo.create(
        name=data.name,
        preset_type=data.preset_type,
        steps=data.steps,
        min_capital=Decimal(str(data.min_capital)),
        max_capital=Decimal(str(data.max_capital)) if data.max_capital else None,
        description=data.description,
        allowed_coin_groups=data.allowed_coin_groups,
        is_builtin=data.is_builtin,
        is_active=True,
        user_id=None if data.is_builtin else admin.id,
    )
    return {
        "id": str(preset.id),
        "name": preset.name,
        "preset_type": preset.preset_type,
        "steps": preset.steps,
        "min_capital": str(preset.min_capital),
        "max_capital": str(preset.max_capital) if preset.max_capital else None,
        "is_builtin": preset.is_builtin,
        "is_active": preset.is_active,
    }


@router.put("/mm-presets/{preset_id}", response_model=dict)
async def admin_update_mm_preset(
    preset_id: str,
    data: MMPresetUpdate,
    admin: UserResponse = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update any MM preset (including built-in)."""
    repo = MMPresetRepository(db)
    preset = await repo.get_by_id(UUID(preset_id))
    if preset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MM preset not found")

    update_data = data.model_dump(exclude_none=True)
    if "min_capital" in update_data and update_data["min_capital"] is not None:
        update_data["min_capital"] = Decimal(str(update_data["min_capital"]))
    if "max_capital" in update_data and update_data["max_capital"] is not None:
        update_data["max_capital"] = Decimal(str(update_data["max_capital"]))

    preset = await repo.update(preset, **update_data)
    return {
        "id": str(preset.id),
        "name": preset.name,
        "preset_type": preset.preset_type,
        "steps": preset.steps,
        "min_capital": str(preset.min_capital),
        "max_capital": str(preset.max_capital) if preset.max_capital else None,
        "description": preset.description,
        "allowed_coin_groups": preset.allowed_coin_groups or [],
        "is_builtin": preset.is_builtin,
        "is_active": preset.is_active,
    }


@router.delete("/mm-presets/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_mm_preset(
    preset_id: str,
    admin: UserResponse = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete any MM preset (including built-in)."""
    repo = MMPresetRepository(db)
    preset = await repo.get_by_id(UUID(preset_id))
    if preset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MM preset not found")
    await repo.delete(preset)


# ─── Strategy Mode Admin ────────────────────────────────────────────

# Strategy modes are now persisted in the ``strategy_modes`` table and
# accessed through ``services.strategy_mode_store``. The store falls back
# to ``DEFAULT_STRATEGY_MODES`` if the table is empty or missing (e.g.
# before migration 0012 has been applied).
from services.strategy_mode_store import (  # noqa: E402
    DEFAULT_STRATEGY_MODES as STRATEGY_MODES_CONFIG,
    get_strategy_modes as _get_strategy_modes,
    update_strategy_mode_with_session as _update_strategy_mode_with_session,
)


class StrategyModeUpdate(BaseModel):
    label: str | None = Field(None, max_length=50)
    tp_range_min: float | None = Field(None, ge=0)
    tp_range_max: float | None = Field(None, ge=0)
    risk_level: str | None = Field(None, max_length=20)


@router.get("/strategy-modes", response_model=list[dict])
async def admin_list_strategy_modes(
    admin: UserResponse = Depends(require_admin),
) -> list[dict[str, Any]]:
    """List all strategy modes with their configuration (DB-backed)."""
    return await _get_strategy_modes()


@router.put("/strategy-modes/{mode}", response_model=dict)
async def admin_update_strategy_mode(
    mode: str,
    data: StrategyModeUpdate,
    admin: UserResponse = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Update strategy mode configuration (persisted to the ``strategy_modes`` table)."""
    updated = await _update_strategy_mode_with_session(
        db,
        mode,
        label=data.label,
        tp_range_min=data.tp_range_min,
        tp_range_max=data.tp_range_max,
        risk_level=data.risk_level,
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy mode {mode.upper()} not found",
        )
    return updated


# ─── Averaging Config Admin ─────────────────────────────────────────

class AveragingStepAdmin(BaseModel):
    step_number: int = Field(..., ge=0, le=200)
    drop_rate: float = Field(..., ge=0, le=100)
    multiple_buy_amount: float = Field(1.0, gt=0)
    take_profit: float = Field(..., gt=0, le=100)


class AveragingTemplateUpdate(BaseModel):
    steps: list[AveragingStepAdmin] = Field(..., min_length=1, max_length=200)


@router.get("/averaging-config/template", response_model=dict)
async def admin_get_averaging_template(
    admin: UserResponse = Depends(require_admin),
) -> dict[str, Any]:
    """Get the default averaging template with full step details."""
    template = get_default_averaging_template()
    summary = get_default_averaging_summary()
    return {
        "summary": summary,
        "steps": [
            {
                "step_number": s["step_number"],
                "drop_rate": str(s["drop_rate"]),
                "multiple_buy_amount": str(s["multiple_buy_amount"]),
                "take_profit": str(s["take_profit"]),
            }
            for s in template
        ],
    }

@router.put("/averaging-config/template", response_model=dict)
async def admin_update_averaging_template(
    data: AveragingTemplateUpdate,
    admin: UserResponse = Depends(require_admin),
) -> dict[str, Any]:
    """Update the default averaging template (in-memory, persisted via config in future)."""
    from services.averaging_template import DEFAULT_DROP_RATES, DEFAULT_TAKE_PROFITS, DEFAULT_MULTIPLIERS

    new_drop_rates = []
    new_take_profits = []
    new_multipliers = []
    for step in sorted(data.steps, key=lambda s: s.step_number):
        new_drop_rates.append(step.drop_rate)
        new_take_profits.append(step.take_profit)
        new_multipliers.append(step.multiple_buy_amount)

    DEFAULT_DROP_RATES[:] = new_drop_rates
    DEFAULT_TAKE_PROFITS[:] = new_take_profits
    DEFAULT_MULTIPLIERS[:] = new_multipliers

    return {
        "total_steps": len(new_drop_rates),
        "drop_rates": new_drop_rates,
        "take_profits": new_take_profits,
        "multipliers": new_multipliers,
    }


# ─── Technical Analysis Admin ──────────────────────────────────────

@router.get("/technical-analysis/indicators", response_model=list[dict])
async def admin_list_indicators(
    admin: UserResponse = Depends(require_admin),
) -> list[dict[str, Any]]:
    """List all available TA indicators with descriptions and default params."""
    from services.ta_engine import get_indicator_descriptions
    return get_indicator_descriptions()

@router.get("/technical-analysis/templates", response_model=list[dict])
async def admin_list_ta_templates(
    admin: UserResponse = Depends(require_admin),
) -> list[dict[str, Any]]:
    """List predefined TA config templates."""
    return [
        {
            "name": "Conservative",
            "description": "RSI + Bollinger Bands (AND) — strict oversold filter",
            "configs": [
                {"indicator": "rsi", "time_frame": "1h", "operator": "and", "params": {"period": 14, "oversold": 25}, "enabled": True, "priority": 0},
                {"indicator": "bollinger_bands", "time_frame": "1h", "operator": "and", "params": {"period": 20, "std_dev": 2}, "enabled": True, "priority": 1},
            ],
        },
        {
            "name": "Balanced",
            "description": "RSI OR MACD — either oversold or bullish crossover",
            "configs": [
                {"indicator": "rsi", "time_frame": "1h", "operator": "or", "params": {"period": 14, "oversold": 35}, "enabled": True, "priority": 0},
                {"indicator": "macd", "time_frame": "1h", "operator": "or", "params": {"fast_period": 12, "slow_period": 26, "signal_period": 9}, "enabled": True, "priority": 1},
            ],
        },
        {
            "name": "Trend Following",
            "description": "EMA Crossover + ATR volatility filter",
            "configs": [
                {"indicator": "ema_crossover", "time_frame": "4h", "operator": "and", "params": {"fast_period": 9, "slow_period": 21}, "enabled": True, "priority": 0},
                {"indicator": "atr", "time_frame": "1h", "operator": "and", "params": {"period": 14, "max_multiplier": 3.0}, "enabled": True, "priority": 1},
            ],
        },
        {
            "name": "Fibonacci + Stochastic",
            "description": "Fibonacci retracement near support AND Stochastic oversold",
            "configs": [
                {"indicator": "fibonacci_retracement", "time_frame": "1d", "operator": "and", "params": {"lookback": 100, "tolerance": 0.02}, "enabled": True, "priority": 0},
                {"indicator": "stochastic", "time_frame": "1h", "operator": "and", "params": {"k_period": 14, "d_period": 3, "oversold": 20}, "enabled": True, "priority": 1},
            ],
        },
    ]


# ─── Circuit Breaker Thresholds Admin ────────────────────────────────
#
# These endpoints let a superadmin validate the pre-computed breaker
# thresholds that the BreakerScreeningStore persists for every trading
# pair. The admin can:
#   - list all thresholds (optionally filtered by continuation rate)
#   - inspect a single symbol's threshold
#   - trigger a manual re-screen (useful after market regime shifts or
#     when thresholds look stale)
#   - see screening health metadata (when last screened, fallback usage,
#     candle counts) so they can judge whether the data is trustworthy.

class BreakerRescreenRequest(BaseModel):
    """Body for triggering a manual re-screen of breaker thresholds."""
    symbols: list[str] = Field(
        default_factory=list,
        description="Symbols to re-screen. Empty = screen all coins in every active coin group.",
    )
    rates: list[float] = Field(
        default=[0.70, 0.80, 0.90],
        description="Continuation rates to screen for (0.70 / 0.80 / 0.90).",
    )
    lookback_days: int = Field(365, ge=30, le=1000)
    continuation_window: int = Field(5, ge=1, le=30)
    min_future_drop_pct: float = Field(3.0, ge=0.0, le=50.0)


def _threshold_to_dict(t) -> dict[str, Any]:
    """Serialize a BreakerThreshold row to a JSON-friendly dict."""
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


@router.get("/breaker-thresholds", response_model=list[dict])
async def admin_list_breaker_thresholds(
    rate: float | None = Query(None, description="Filter by continuation rate (e.g. 0.90)."),
    exchange: str | None = Query(None, description="Filter by exchange (e.g. binance)."),
    admin: UserResponse = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all pre-computed breaker thresholds.

    Optional filters:
      - ``rate``: only thresholds for a given continuation rate.
      - ``exchange``: only thresholds for a given exchange.

    The response includes screening metadata (``screened_at``,
    ``used_fallback``, ``candle_count``) so admins can judge data freshness
    and validity at a glance.
    """
    repo = BreakerThresholdRepository(db)
    if rate is not None:
        rows = await repo.get_all_for_rate(Decimal(str(rate)), exchange=exchange)
    else:
        # No rate filter — return everything (paginated implicitly by DB size).
        from sqlalchemy import select
        from models.breaker_threshold import BreakerThreshold
        stmt = select(BreakerThreshold)
        if exchange is not None:
            stmt = stmt.where(BreakerThreshold.exchange == exchange.lower())
        stmt = stmt.order_by(BreakerThreshold.symbol, BreakerThreshold.min_continuation_rate)
        result = await db.execute(stmt)
        rows = list(result.scalars().all())
    return [_threshold_to_dict(t) for t in rows]


@router.get("/breaker-thresholds/{symbol}", response_model=dict | list)
async def admin_get_breaker_threshold(
    symbol: str,
    rate: float | None = Query(None, description="Specific continuation rate. Omit for all rates."),
    exchange: str = Query("binance", description="Exchange name."),
    admin: UserResponse = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any] | list[dict[str, Any]]:
    """Get breaker threshold(s) for a single symbol.

    If ``rate`` is provided, returns a single threshold dict (or 404).
    Otherwise returns a list of all rates for that symbol.
    """
    repo = BreakerThresholdRepository(db)
    if rate is not None:
        row = await repo.get_threshold(exchange, symbol.upper(), Decimal(str(rate)))
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No breaker threshold for {symbol} at rate {rate}",
            )
        return _threshold_to_dict(row)
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
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No breaker thresholds found for {symbol}",
        )
    return [_threshold_to_dict(t) for t in rows]


@router.get("/breaker-thresholds/health/summary", response_model=dict)
async def admin_breaker_health_summary(
    admin: UserResponse = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Aggregate health summary for breaker thresholds.

    Helps a superadmin quickly answer "is the breaker data valid?":
      - total rows, rows per rate
      - how many used the fallback (i.e. no real historical data)
      - oldest / newest ``screened_at`` (staleness check)
      - symbols missing thresholds (gaps in coverage)
    """
    from sqlalchemy import Integer, func, select
    from models.breaker_threshold import BreakerThreshold

    # Total count
    total = (await db.execute(select(func.count()).select_from(BreakerThreshold))).scalar_one()

    # Count per rate
    rate_rows = await db.execute(
        select(
            BreakerThreshold.min_continuation_rate,
            func.count(),
            func.sum(BreakerThreshold.used_fallback.cast(Integer)),
        ).group_by(BreakerThreshold.min_continuation_rate)
    )
    per_rate = {
        float(r): {"count": int(c), "fallback_count": int(fb or 0)}
        for r, c, fb in rate_rows.all()
    }

    # Oldest / newest screened_at
    oldest = (
        await db.execute(select(func.min(BreakerThreshold.screened_at)))
    ).scalar_one_or_none()
    newest = (
        await db.execute(select(func.max(BreakerThreshold.screened_at)))
    ).scalar_one_or_none()

    # Distinct symbols screened
    distinct_symbols = (
        await db.execute(
            select(func.count(func.distinct(BreakerThreshold.symbol)))
        )
    ).scalar_one()

    return {
        "total_rows": int(total),
        "distinct_symbols": int(distinct_symbols),
        "per_rate": per_rate,
        "oldest_screened_at": oldest.isoformat() if oldest else None,
        "newest_screened_at": newest.isoformat() if newest else None,
        "fallback_total": sum(r["fallback_count"] for r in per_rate.values()),
    }


@router.post("/breaker-thresholds/rescreen", response_model=dict)
async def admin_rescreen_breaker_thresholds(
    data: BreakerRescreenRequest,
    admin: UserResponse = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Trigger a manual re-screen of breaker thresholds.

    This fetches historical candles for the requested symbols and
    re-computes thresholds, upserting them into the database. Use this
    when:
      - thresholds look stale (``screened_at`` is days old)
      - market regime shifted and thresholds may no longer be accurate
      - new symbols were added to coin groups and need screening
      - validating that the screening pipeline still works end-to-end

    If ``symbols`` is empty, all coins from every active coin group are
    screened.
    """
    hub = _get_market_hub()
    store = BreakerScreeningStore(hub)

    # Resolve symbols: explicit list, or all coins from active groups.
    symbols = [s.upper() for s in data.symbols]
    if not symbols:
        cg_repo = CoinGroupRepository(db)
        groups = await cg_repo.get_all(limit=500)
        for g in groups:
            if not g.is_active:
                continue
            for c in (g.coins or []):
                if c.upper() not in symbols:
                    symbols.append(c.upper())
    if not symbols:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No symbols to screen (no explicit list and no active coin groups).",
        )

    rates = [Decimal(str(r)) for r in data.rates]
    base_config = ScreenerConfig(
        lookback_days=data.lookback_days,
        continuation_window=data.continuation_window,
        min_future_drop_pct=Decimal(str(data.min_future_drop_pct)),
    )

    all_results = await store.rescreen_for_rates(
        db=db, symbols=symbols, rates=rates, base_config=base_config,
    )

    # Build a summary for the response (counts + fallback flags).
    summary: dict[str, Any] = {
        "screened_symbols": len(symbols),
        "rates": [float(r) for r in rates],
        "results": {},
    }
    for rate, results in all_results.items():
        rate_key = float(rate)
        summary["results"][str(rate_key)] = {
            "symbol_count": len(results),
            "fallback_count": sum(1 for r in results.values() if r.used_fallback),
            "data_driven_count": sum(1 for r in results.values() if not r.used_fallback),
            "symbols": sorted(results.keys()),
        }
    return summary


# ---------------------------------------------------------------------------
# Breaker resume config — admin override of post-trigger behavior.
# ---------------------------------------------------------------------------
# These endpoints let a superadmin override the tier-default resume behavior
# (resume_mode / recovery_pct / widen_multiplier) for a specific symbol+rate
# without re-running screening. Useful when an admin wants, e.g., all 90%
# thresholds to use trailing_buy instead of widen_step.

class BreakerResumeConfigRequest(BaseModel):
    """Body for updating the resume behavior of a breaker threshold row."""
    resume_mode: str | None = Field(
        None,
        description="One of: ta_confirm, widen_step, trailing_buy. "
                    "If omitted, the field is left unchanged.",
    )
    recovery_pct: float | None = Field(
        None, ge=0.0, le=50.0,
        description="For trailing_buy mode — % recovery from the intraday "
                    "low required before buys resume (e.g. 5.0 = 5%).",
    )
    widen_multiplier: float | None = Field(
        None, ge=1.0, le=10.0,
        description="For widen_step mode — grid step multiplier while the "
                    "breaker is active (e.g. 2.0 = 2× wider spacing).",
    )


@router.patch("/breaker-thresholds/{symbol}/resume-config", response_model=dict)
async def admin_update_breaker_resume_config(
    symbol: str,
    data: BreakerResumeConfigRequest,
    rate: float = Query(..., description="Continuation rate (e.g. 0.90)."),
    exchange: str = Query("binance", description="Exchange name."),
    admin: UserResponse = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Override the resume behavior for a symbol's breaker threshold.

    Updates only the resume fields (resume_mode, recovery_pct, widen_multiplier)
    without re-running screening. The threshold itself is unchanged.

    Returns the updated threshold row, or 404 if no row exists for the
    given symbol + rate + exchange.
    """
    # Validate resume_mode if provided.
    valid_modes = {"ta_confirm", "widen_step", "trailing_buy"}
    if data.resume_mode is not None and data.resume_mode not in valid_modes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid resume_mode '{data.resume_mode}'. "
                   f"Must be one of: {sorted(valid_modes)}",
        )

    repo = BreakerThresholdRepository(db)
    row = await repo.update_resume_config(
        exchange=exchange,
        symbol=symbol.upper(),
        min_continuation_rate=Decimal(str(rate)),
        resume_mode=data.resume_mode,
        recovery_pct=Decimal(str(data.recovery_pct)) if data.recovery_pct is not None else None,
        widen_multiplier=Decimal(str(data.widen_multiplier)) if data.widen_multiplier is not None else None,
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No breaker threshold for {symbol.upper()} at rate {rate} on {exchange}.",
        )
    await db.commit()
    return _threshold_to_dict(row)
