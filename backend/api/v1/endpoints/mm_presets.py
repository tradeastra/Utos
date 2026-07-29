"""MM Presets endpoints — list, calculate, create custom."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from api.v1.endpoints.users import get_current_user_from_token
from core.exceptions import ValidationError
from database.base import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models.mm_preset import MMPreset
from pydantic import BaseModel, ConfigDict, Field
from repositories.coin_group_repository import CoinGroupRepository
from repositories.mm_preset_repository import MMPresetRepository
from schemas.auth import UserResponse
from services.mm_calculator import BUILTIN_PRESETS, MMCalculator
from services.saas.license import _DEFAULT_LIMITS
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
_mm_calc = MMCalculator()


async def _ensure_builtin_coin_groups(db: AsyncSession) -> None:
    """Seed built-in coin groups if none exist (needed for name lookup in /calculate)."""
    from api.v1.endpoints.coin_groups import _ensure_builtin_groups

    await _ensure_builtin_groups(db)


async def _ensure_builtin_presets(db: AsyncSession):
    """Seed built-in MM presets if missing, and sync their fields with the
    source of truth in services.mm_calculator.BUILTIN_PRESETS.

    Self-healing: if a built-in row already exists but its description /
    allowed_coin_groups / steps / min_capital drifted from BUILTIN_PRESETS
    (e.g. because a rename migration forgot to update the description),
    the row is updated in place. This prevents stale labels like
    "3 Kings / 5 Kings" from persisting in the DB.
    """
    repo = MMPresetRepository(db)
    existing = await repo.get_builtin_presets()
    existing_by_type = {p.preset_type: p for p in existing}

    for key, p in BUILTIN_PRESETS.items():
        row = existing_by_type.get(key)
        if row is None:
            db.add(MMPreset(
                name=p["name"],
                preset_type=key,
                steps=p["steps"],
                min_capital=p["min_capital"],
                max_capital=p["max_capital"],
                description=p["description"],
                allowed_coin_groups=p["allowed_coin_groups"],
                is_builtin=True,
                is_active=True,
                user_id=None,
            ))
            continue
        # Sync drifted fields on existing built-in rows.
        drifted = (
            row.description != p["description"]
            or row.allowed_coin_groups != p["allowed_coin_groups"]
            or row.steps != p["steps"]
            or row.name != p["name"]
        )
        # min_capital is Numeric; compare as Decimal to avoid float noise.
        if str(row.min_capital) != str(p["min_capital"]):
            drifted = True
        if drifted:
            row.name = p["name"]
            row.steps = p["steps"]
            row.min_capital = p["min_capital"]
            row.max_capital = p["max_capital"]
            row.description = p["description"]
            row.allowed_coin_groups = p["allowed_coin_groups"]

    await db.commit()


class MMPresetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    preset_type: str
    steps: int
    min_capital: str
    max_capital: str | None = None
    description: str | None = None
    allowed_coin_groups: list[str] | None = None
    is_builtin: bool = False
    is_active: bool = True


class MMCalculationRequest(BaseModel):
    preset_type: str = Field(..., description="mm30, mm50, mm70, or custom")
    capital: float = Field(..., gt=0, description="Total capital to allocate")
    coin_group_name: str = Field(..., description="Coin group name — required to derive max_coins for the per-coin DCA allocation")
    custom_steps: int | None = Field(None, ge=1, le=200, description="Steps for custom preset")


class MMCalculationResponse(BaseModel):
    buy_amount: str
    max_coins: int
    steps: int
    capital: str
    preset_type: str
    min_volume_filter: str


class MMPresetCreate(BaseModel):
    name: str = Field(..., max_length=50)
    steps: int = Field(..., ge=1, le=200)
    min_capital: float = Field(..., gt=0)
    max_capital: float | None = Field(None, gt=0)
    description: str | None = Field(None, max_length=200)
    allowed_coin_groups: list[str] | None = None


@router.get("", response_model=list[MMPresetResponse])
async def list_mm_presets(
    current_user: UserResponse = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all MM presets (built-in + user custom)."""
    await _ensure_builtin_presets(db)
    repo = MMPresetRepository(db)
    presets = await repo.get_by_user_id(current_user.id)
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
        }
        for p in presets
    ]


@router.post("/calculate", response_model=MMCalculationResponse)
async def calculate_mm(
    data: MMCalculationRequest,
    current_user: UserResponse = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Calculate buy amount, max coins, and volume filter from preset + capital.

    The coin group is REQUIRED: each coin receives `steps` DCA layers, so the
    per-layer buy amount is `capital / (steps * coin_group.max_coins)`.
    """
    await _ensure_builtin_coin_groups(db)
    group_repo = CoinGroupRepository(db)
    coin_group = await group_repo.get_by_name(data.coin_group_name)
    if coin_group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coin group '{data.coin_group_name}' not found",
        )

    try:
        result = _mm_calc.calculate(
            preset_type=data.preset_type,
            capital=Decimal(str(data.capital)),
            coin_group_name=data.coin_group_name,
            coin_group_max_coins=coin_group.max_coins,
            custom_steps=data.custom_steps,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return {
        "buy_amount": str(result.buy_amount),
        "max_coins": result.max_coins,
        "steps": result.steps,
        "capital": str(result.capital),
        "preset_type": result.preset_type,
        "min_volume_filter": str(result.min_volume_filter),
    }


@router.post("", response_model=MMPresetResponse, status_code=status.HTTP_201_CREATED)
async def create_mm_preset(
    data: MMPresetCreate,
    current_user: UserResponse = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a custom MM preset (Pro+ tier only)."""
    tier_str = current_user.subscription_tier
    limits = _DEFAULT_LIMITS.get(tier_str, _DEFAULT_LIMITS["free"])

    if tier_str not in ("pro", "enterprise"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Custom MM presets require Pro or Enterprise tier",
        )

    repo = MMPresetRepository(db)
    preset = await repo.create(
        name=data.name,
        preset_type="custom",
        steps=data.steps,
        min_capital=Decimal(str(data.min_capital)),
        max_capital=Decimal(str(data.max_capital)) if data.max_capital else None,
        description=data.description,
        allowed_coin_groups=data.allowed_coin_groups,
        is_builtin=False,
        is_active=True,
        user_id=current_user.id,
    )
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


@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mm_preset(
    preset_id: str,
    current_user: UserResponse = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a custom MM preset (cannot delete built-in)."""
    repo = MMPresetRepository(db)
    preset = await repo.get_by_id(UUID(preset_id))
    if preset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MM preset not found")
    if preset.is_builtin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete built-in preset")
    if preset.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    await repo.delete(preset)
