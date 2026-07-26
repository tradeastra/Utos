"""Coin groups endpoints — list, create custom, seed builtins."""

from typing import Any
from uuid import UUID

from api.v1.endpoints.users import get_current_user_from_token
from database.base import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models.coin_group import CoinGroup
from pydantic import BaseModel, ConfigDict, Field
from repositories.coin_group_repository import CoinGroupRepository
from schemas.auth import UserResponse
from services.saas.license import _DEFAULT_LIMITS
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

BUILTIN_GROUPS = [
    {"name": "Top 3", "description": "Top 3 coins by volume", "max_coins": 3, "coins": ["BTC", "ETH", "BNB"]},
    {"name": "Top 5", "description": "Top 5 coins by volume", "max_coins": 5, "coins": ["BTC", "ETH", "BNB", "SOL", "XRP"]},
    {"name": "Top 10", "description": "Top 10 coins by volume", "max_coins": 10, "coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "AVAX", "DOT", "MATIC"]},
    {"name": "Top 20", "description": "Top 20 coins by volume", "max_coins": 20, "coins": ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "AVAX", "DOT", "MATIC", "LINK", "UNI", "ATOM", "LTC", "BCH", "NEAR", "APT", "FIL", "ARB", "OP"]},
    {"name": "Top 50", "description": "Top 50 coins by volume", "max_coins": 50, "coins": []},
    {"name": "All", "description": "All available coins", "max_coins": 999, "coins": []},
]


async def _ensure_builtin_groups(db: AsyncSession):
    """Seed built-in coin groups if none exist."""
    repo = CoinGroupRepository(db)
    existing = await repo.get_builtin_groups()
    if existing:
        return
    for g in BUILTIN_GROUPS:
        db.add(CoinGroup(
            name=g["name"],
            description=g["description"],
            max_coins=g["max_coins"],
            coins=g["coins"],
            is_builtin=True,
            is_active=True,
            user_id=None,
        ))
    await db.commit()


class CoinGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    max_coins: int
    coins: list[str] = []
    is_builtin: bool = False
    is_active: bool = True


class CoinGroupCreate(BaseModel):
    name: str = Field(..., max_length=50, description="Group name")
    description: str | None = Field(None, max_length=200)
    coins: list[str] = Field(..., min_length=1, description="List of coin symbols")


class CoinSelectionLimitResponse(BaseModel):
    tier: str
    max_coin_selection: int
    current_selection: int


@router.get("", response_model=list[CoinGroupResponse])
async def list_coin_groups(
    current_user: UserResponse = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all coin groups (built-in + user custom)."""
    await _ensure_builtin_groups(db)
    repo = CoinGroupRepository(db)
    groups = await repo.get_by_user_id(current_user.id)
    return [
        {
            "id": str(g.id),
            "name": g.name,
            "description": g.description,
            "max_coins": g.max_coins,
            "coins": g.coins or [],
            "is_builtin": g.is_builtin,
            "is_active": g.is_active,
        }
        for g in groups
    ]


@router.post("", response_model=CoinGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_coin_group(
    data: CoinGroupCreate,
    current_user: UserResponse = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a custom coin group (Pro+ tier only)."""
    tier_str = current_user.subscription_tier
    limits = _DEFAULT_LIMITS.get(tier_str, _DEFAULT_LIMITS["free"])

    if limits.max_coin_selection < len(data.coins):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your tier ({tier_str}) allows max {limits.max_coin_selection} coins per group",
        )

    repo = CoinGroupRepository(db)
    group = await repo.create(
        name=data.name,
        description=data.description,
        max_coins=len(data.coins),
        coins=[c.upper() for c in data.coins],
        is_builtin=False,
        is_active=True,
        user_id=current_user.id,
    )
    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "max_coins": group.max_coins,
        "coins": group.coins or [],
        "is_builtin": group.is_builtin,
        "is_active": group.is_active,
    }


@router.get("/limits", response_model=CoinSelectionLimitResponse)
async def get_selection_limits(
    current_user: UserResponse = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get coin selection limits for the current user's tier."""
    tier_str = current_user.subscription_tier
    limits = _DEFAULT_LIMITS.get(tier_str, _DEFAULT_LIMITS["free"])
    return {
        "tier": tier_str,
        "max_coin_selection": limits.max_coin_selection,
        "current_selection": 0,
    }


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_coin_group(
    group_id: str,
    current_user: UserResponse = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a custom coin group (cannot delete built-in)."""
    repo = CoinGroupRepository(db)
    group = await repo.get_by_id(UUID(group_id))
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coin group not found")
    if group.is_builtin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete built-in group")
    if group.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    await repo.delete(group)
