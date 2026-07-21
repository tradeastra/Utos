"""Admin endpoints — manage coin groups, MM presets, strategy modes.

All endpoints require admin role.
Admins can create, update, delete, and toggle built-in and custom resources.
"""

from decimal import Decimal
from typing import Any
from uuid import UUID

from api.v1.endpoints.users import require_admin
from database.base import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models.coin_group import CoinGroup
from models.mm_preset import MMPreset
from pydantic import BaseModel, ConfigDict, Field
from repositories.coin_group_repository import CoinGroupRepository
from repositories.mm_preset_repository import MMPresetRepository
from schemas.auth import UserResponse
from services.averaging_template import get_default_averaging_summary, get_default_averaging_template
from services.mm_calculator import BUILTIN_PRESETS
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


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

STRATEGY_MODES_CONFIG = [
    {"mode": "A", "label": "Super Bearish", "daily_range_min": 0.5, "daily_range_max": 1.5, "risk_level": "Low"},
    {"mode": "B", "label": "Conventional", "daily_range_min": 1.0, "daily_range_max": 3.0, "risk_level": "Medium"},
    {"mode": "C", "label": "Aggressive", "daily_range_min": 2.0, "daily_range_max": 5.0, "risk_level": "High"},
    {"mode": "D", "label": "Very Aggressive", "daily_range_min": 3.0, "daily_range_max": 8.0, "risk_level": "Very High"},
    {"mode": "U", "label": "Ultimate", "daily_range_min": 5.0, "daily_range_max": 15.0, "risk_level": "Extreme"},
]


class StrategyModeUpdate(BaseModel):
    label: str | None = Field(None, max_length=50)
    daily_range_min: float | None = Field(None, ge=0)
    daily_range_max: float | None = Field(None, ge=0)
    risk_level: str | None = Field(None, max_length=20)


@router.get("/strategy-modes", response_model=list[dict])
async def admin_list_strategy_modes(
    admin: UserResponse = Depends(require_admin),
) -> list[dict[str, Any]]:
    """List all strategy modes with their configuration."""
    return STRATEGY_MODES_CONFIG


@router.put("/strategy-modes/{mode}", response_model=dict)
async def admin_update_strategy_mode(
    mode: str,
    data: StrategyModeUpdate,
    admin: UserResponse = Depends(require_admin),
) -> dict[str, Any]:
    """Update strategy mode configuration (in-memory, persisted via config in future)."""
    mode = mode.upper()
    for sm in STRATEGY_MODES_CONFIG:
        if sm["mode"] == mode:
            if data.label is not None:
                sm["label"] = data.label
            if data.daily_range_min is not None:
                sm["daily_range_min"] = data.daily_range_min
            if data.daily_range_max is not None:
                sm["daily_range_max"] = data.daily_range_max
            if data.risk_level is not None:
                sm["risk_level"] = data.risk_level
            return sm
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Strategy mode {mode} not found")


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
