"""Add-ons endpoints — list available add-ons, check access, purchase add-ons."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from api.v1.endpoints.users import get_current_user_from_token
from core.exceptions import ValidationError
from database.base import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models.user import User
from pydantic import BaseModel
from repositories.user_addon_repository import UserAddOnRepository
from services.saas.license import ADDON_DESCRIPTIONS, ADDON_PRICES
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class AddOnInfo(BaseModel):
    key: str
    name: str
    description: str
    price: float
    is_purchased: bool
    is_active: bool


class PurchaseAddOnRequest(BaseModel):
    addon_key: str
    duration_days: int = 30


class PurchaseAddOnResponse(BaseModel):
    addon_key: str
    is_active: bool
    purchased_at: str
    expires_at: str | None


@router.get("/", response_model=list[AddOnInfo])
async def list_addons(
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List all available add-ons and their purchase status for the current user."""
    repo = UserAddOnRepository(db)
    user_addons = await repo.get_by_user_id(current_user.id)
    purchased_map = {a.addon_key: a for a in user_addons}

    result = []
    for key, price in ADDON_PRICES.items():
        addon = purchased_map.get(key)
        result.append({
            "key": key,
            "name": key.replace("_", " ").title(),
            "description": ADDON_DESCRIPTIONS.get(key, ""),
            "price": price,
            "is_purchased": addon is not None,
            "is_active": addon is not None and addon.is_active,
        })
    return result


@router.get("/check/{addon_key}")
async def check_addon_access(
    addon_key: str,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Check if user has access to a specific add-on (via tier or purchase)."""
    from services.saas.license import LicenseManager, _DEFAULT_LIMITS

    tier = current_user.subscription_tier.value if hasattr(current_user.subscription_tier, "value") else str(current_user.subscription_tier)
    limits = _DEFAULT_LIMITS.get(tier, _DEFAULT_LIMITS["free"])

    repo = UserAddOnRepository(db)
    addon = await repo.get_by_user_and_key(current_user.id, addon_key)

    has_via_tier = addon_key in limits.feature_flags
    has_via_addon = addon is not None and addon.is_active
    has_access = has_via_tier or has_via_addon

    return {
        "addon_key": addon_key,
        "has_access": has_access,
        "via_tier": has_via_tier,
        "via_addon": has_via_addon,
        "tier": tier,
    }


@router.post("/purchase", response_model=PurchaseAddOnResponse)
async def purchase_addon(
    req: PurchaseAddOnRequest,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Purchase an add-on for the current user."""
    if req.addon_key not in ADDON_PRICES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown add-on: {req.addon_key}",
        )

    repo = UserAddOnRepository(db)
    existing = await repo.get_by_user_and_key(current_user.id, req.addon_key)

    if existing is not None and existing.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Add-on '{req.addon_key}' is already active",
        )

    now = datetime.now(UTC)
    expires = now + timedelta(days=req.duration_days)

    if existing is not None:
        existing.is_active = True
        existing.purchased_at = now
        existing.expires_at = expires
        await db.flush()
        await db.refresh(existing)
        addon = existing
    else:
        addon = await repo.create(
            user_id=current_user.id,
            addon_key=req.addon_key,
            is_active=True,
            purchased_at=now,
            expires_at=expires,
        )

    await db.commit()

    return {
        "addon_key": addon.addon_key,
        "is_active": addon.is_active,
        "purchased_at": addon.purchased_at.isoformat() if addon.purchased_at else now.isoformat(),
        "expires_at": addon.expires_at.isoformat() if addon.expires_at else None,
    }
