"""Grid profiles endpoints — create and list grid trading profiles."""

import uuid
from typing import Any

from api.dependencies import get_current_user_token
from database.base import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models.grid_profile import GridProfile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class GridProfileCreate(BaseModel):
    name: str = Field(..., description="Profile name")
    upper_price: float = Field(..., gt=0, description="Upper price bound")
    lower_price: float = Field(..., gt=0, description="Lower price bound")
    grid_count: int = Field(..., ge=2, le=100, description="Number of grid levels")
    investment_per_grid: float = Field(..., gt=0, description="Investment per grid level")
    take_profit_enabled: bool = False
    take_profit_percentage: float | None = None
    stop_loss_enabled: bool = False
    stop_loss_percentage: float | None = None


class GridProfileResponse(BaseModel):
    id: str
    user_id: str
    name: str
    strategy_type: str
    upper_price: float
    lower_price: float
    grid_count: int
    grid_spacing: float | None
    investment_per_grid: float
    take_profit_enabled: bool
    take_profit_percentage: float | None
    stop_loss_enabled: bool
    stop_loss_percentage: float | None
    is_default: bool
    created_at: str


def _to_response(gp: GridProfile) -> dict[str, Any]:
    return {
        "id": str(gp.id),
        "user_id": str(gp.user_id),
        "name": gp.name,
        "strategy_type": gp.strategy_type,
        "upper_price": float(gp.upper_price),
        "lower_price": float(gp.lower_price),
        "grid_count": gp.grid_count,
        "grid_spacing": float(gp.grid_spacing) if gp.grid_spacing else None,
        "investment_per_grid": float(gp.investment_per_grid),
        "take_profit_enabled": gp.take_profit_enabled,
        "take_profit_percentage": float(gp.take_profit_percentage) if gp.take_profit_percentage else None,
        "stop_loss_enabled": gp.stop_loss_enabled,
        "stop_loss_percentage": float(gp.stop_loss_percentage) if gp.stop_loss_percentage else None,
        "is_default": gp.is_default,
        "created_at": gp.created_at.isoformat() if gp.created_at else None,
    }


@router.get("/", response_model=list[GridProfileResponse])
async def list_grid_profiles(
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    """List grid profiles for current user."""
    user_id = current_user["user_id"]
    result = await db.execute(
        select(GridProfile).where(GridProfile.user_id == uuid.UUID(user_id))
    )
    profiles = result.scalars().all()
    return [_to_response(p) for p in profiles]


@router.post("/", response_model=GridProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_grid_profile(
    data: GridProfileCreate,
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    """Create a new grid profile."""
    if data.upper_price <= data.lower_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upper price must be greater than lower price",
        )

    grid_spacing = (data.upper_price - data.lower_price) / data.grid_count

    profile = GridProfile(
        user_id=uuid.UUID(current_user["user_id"]),
        name=data.name,
        strategy_type="smart_grid",
        upper_price=data.upper_price,
        lower_price=data.lower_price,
        grid_count=data.grid_count,
        grid_spacing=grid_spacing,
        investment_per_grid=data.investment_per_grid,
        take_profit_enabled=data.take_profit_enabled,
        take_profit_percentage=data.take_profit_percentage,
        stop_loss_enabled=data.stop_loss_enabled,
        stop_loss_percentage=data.stop_loss_percentage,
        is_default=False,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return _to_response(profile)


@router.delete("/{profile_id}")
async def delete_grid_profile(
    profile_id: str,
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    """Delete a grid profile."""
    user_id = current_user["user_id"]
    result = await db.execute(
        select(GridProfile).where(
            GridProfile.id == uuid.UUID(profile_id),
            GridProfile.user_id == uuid.UUID(user_id),
        )
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Grid profile not found"
        )
    await db.delete(profile)
    await db.commit()
    return {"message": "Grid profile deleted"}
