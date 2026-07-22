"""Averaging config endpoints — per-step drop rate, multiplier, take profit."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from api.v1.endpoints.users import get_current_user_from_token
from database.base import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models.averaging_config import AveragingConfig
from models.trading_instance import TradingInstance
from pydantic import BaseModel, Field
from schemas.auth import UserResponse
from services.averaging_template import get_default_averaging_template, get_default_averaging_summary
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class AveragingStepModel(BaseModel):
    step_number: int = Field(..., ge=0, le=200)
    drop_rate: float = Field(..., ge=0, le=100, description="Drop rate percentage from previous level")
    multiple_buy_amount: float = Field(1.0, gt=0, description="Multiplier for buy amount at this step")
    take_profit: float = Field(..., gt=0, le=100, description="Take profit percentage")
    description: str | None = None


class AveragingConfigResponse(BaseModel):
    step_number: int
    drop_rate: str
    multiple_buy_amount: str
    take_profit: str
    description: str | None = None


class AveragingConfigUpdate(BaseModel):
    steps: list[AveragingStepModel] = Field(..., min_length=1, max_length=200)


class AveragingTemplateResponse(BaseModel):
    total_steps: int
    avg_drop_rate: float
    max_drop_rate: float
    min_drop_rate: float
    avg_take_profit: float
    max_multiplier: float
    drop_rates: list[float]
    take_profits: list[float]
    multipliers: list[float]


async def _get_user_instance(
    db: AsyncSession, instance_id: UUID, user_id: UUID
) -> TradingInstance:
    result = await db.execute(
        select(TradingInstance).where(
            TradingInstance.id == instance_id,
            TradingInstance.user_id == user_id,
        )
    )
    instance = result.scalar_one_or_none()
    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trading instance not found",
        )
    return instance


@router.get("/{instance_id}/averaging-config", response_model=list[AveragingConfigResponse])
async def get_averaging_config(
    instance_id: str,
    current_user: UserResponse = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get averaging configuration for a trading instance."""
    instance = await _get_user_instance(db, UUID(instance_id), current_user.id)
    result = await db.execute(
        select(AveragingConfig)
        .where(AveragingConfig.trading_instance_id == instance.id)
        .order_by(AveragingConfig.step_number)
    )
    configs = result.scalars().all()
    return [
        {
            "step_number": c.step_number,
            "drop_rate": str(c.drop_rate),
            "multiple_buy_amount": str(c.multiple_buy_amount),
            "take_profit": str(c.take_profit),
            "description": c.description,
        }
        for c in configs
    ]


@router.put("/{instance_id}/averaging-config", response_model=list[AveragingConfigResponse])
async def update_averaging_config(
    instance_id: str,
    data: AveragingConfigUpdate,
    current_user: UserResponse = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Update averaging configuration (replaces all steps)."""
    instance = await _get_user_instance(db, UUID(instance_id), current_user.id)

    # Delete existing config
    await db.execute(
        delete(AveragingConfig).where(
            AveragingConfig.trading_instance_id == instance.id
        )
    )

    # Insert new steps
    for step in data.steps:
        db.add(AveragingConfig(
            trading_instance_id=instance.id,
            step_number=step.step_number,
            drop_rate=Decimal(str(step.drop_rate)),
            multiple_buy_amount=Decimal(str(step.multiple_buy_amount)),
            take_profit=Decimal(str(step.take_profit)),
            description=step.description,
        ))
    await db.commit()

    # Return inserted rows
    result = await db.execute(
        select(AveragingConfig)
        .where(AveragingConfig.trading_instance_id == instance.id)
        .order_by(AveragingConfig.step_number)
    )
    configs = result.scalars().all()
    return [
        {
            "step_number": c.step_number,
            "drop_rate": str(c.drop_rate),
            "multiple_buy_amount": str(c.multiple_buy_amount),
            "take_profit": str(c.take_profit),
            "description": c.description,
        }
        for c in configs
    ]


@router.post("/{instance_id}/averaging-config/reset", response_model=list[AveragingConfigResponse])
async def reset_averaging_config(
    instance_id: str,
    current_user: UserResponse = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Reset averaging configuration to default 35-step template."""
    instance = await _get_user_instance(db, UUID(instance_id), current_user.id)

    # Delete existing config
    await db.execute(
        delete(AveragingConfig).where(
            AveragingConfig.trading_instance_id == instance.id
        )
    )

    # Insert default template
    template = get_default_averaging_template()
    for step in template:
        db.add(AveragingConfig(
            trading_instance_id=instance.id,
            step_number=step["step_number"],
            drop_rate=step["drop_rate"],
            multiple_buy_amount=step["multiple_buy_amount"],
            take_profit=step["take_profit"],
        ))
    await db.commit()

    result = await db.execute(
        select(AveragingConfig)
        .where(AveragingConfig.trading_instance_id == instance.id)
        .order_by(AveragingConfig.step_number)
    )
    configs = result.scalars().all()
    return [
        {
            "step_number": c.step_number,
            "drop_rate": str(c.drop_rate),
            "multiple_buy_amount": str(c.multiple_buy_amount),
            "take_profit": str(c.take_profit),
            "description": c.description,
        }
        for c in configs
    ]


@router.get("/averaging-config/template", response_model=AveragingTemplateResponse)
async def get_averaging_template(
    current_user: UserResponse = Depends(get_current_user_from_token),
) -> dict[str, Any]:
    """Get the default averaging template summary."""
    return get_default_averaging_summary()
