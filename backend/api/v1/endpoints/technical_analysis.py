"""Technical Analysis config endpoints — per-instance TA indicator settings."""

from typing import Any
from uuid import UUID

from api.v1.endpoints.users import get_current_user_from_token
from database.base import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models.technical_analysis import TechnicalAnalysisConfig
from models.trading_instance import TradingInstance
from pydantic import BaseModel, Field
from schemas.auth import UserResponse
from services.ta_engine import get_indicator_descriptions
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class TAConfigModel(BaseModel):
    indicator: str = Field(..., description="Indicator name (rsi, macd, bollinger_bands, etc.)")
    time_frame: str = Field("1h", max_length=10)
    operator: str = Field("and", pattern="^(and|or)$")
    params: dict[str, Any] | None = None
    enabled: bool = True
    priority: int = Field(0, ge=0, le=100)
    description: str | None = None


class TAConfigResponse(BaseModel):
    id: str
    indicator: str
    time_frame: str
    operator: str
    params: dict[str, Any] | None
    enabled: bool
    priority: int
    description: str | None


class TAConfigUpdate(BaseModel):
    configs: list[TAConfigModel] = Field(..., min_length=0, max_length=20)


class IndicatorDescription(BaseModel):
    indicator: str
    label: str
    description: str
    default_params: dict[str, Any]


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


def _to_response(c: TechnicalAnalysisConfig) -> dict[str, Any]:
    return {
        "id": str(c.id),
        "indicator": c.indicator,
        "time_frame": c.time_frame,
        "operator": c.operator,
        "params": c.params,
        "enabled": c.enabled,
        "priority": c.priority,
        "description": c.description,
    }


@router.get("/{instance_id}/technical-analysis", response_model=list[TAConfigResponse])
async def get_ta_configs(
    instance_id: str,
    current_user: UserResponse = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get all TA indicator configs for a trading instance."""
    instance = await _get_user_instance(db, UUID(instance_id), current_user.id)
    result = await db.execute(
        select(TechnicalAnalysisConfig)
        .where(TechnicalAnalysisConfig.trading_instance_id == instance.id)
        .order_by(TechnicalAnalysisConfig.priority)
    )
    return [_to_response(c) for c in result.scalars().all()]


@router.put("/{instance_id}/technical-analysis", response_model=list[TAConfigResponse])
async def update_ta_configs(
    instance_id: str,
    data: TAConfigUpdate,
    current_user: UserResponse = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Replace all TA configs for a trading instance."""
    instance = await _get_user_instance(db, UUID(instance_id), current_user.id)

    await db.execute(
        delete(TechnicalAnalysisConfig).where(
            TechnicalAnalysisConfig.trading_instance_id == instance.id
        )
    )

    for cfg in data.configs:
        db.add(TechnicalAnalysisConfig(
            trading_instance_id=instance.id,
            indicator=cfg.indicator,
            time_frame=cfg.time_frame,
            operator=cfg.operator,
            params=cfg.params,
            enabled=cfg.enabled,
            priority=cfg.priority,
            description=cfg.description,
        ))
    await db.commit()

    result = await db.execute(
        select(TechnicalAnalysisConfig)
        .where(TechnicalAnalysisConfig.trading_instance_id == instance.id)
        .order_by(TechnicalAnalysisConfig.priority)
    )
    return [_to_response(c) for c in result.scalars().all()]


@router.post("/{instance_id}/technical-analysis/toggle", response_model=dict)
async def toggle_ta(
    instance_id: str,
    enabled: bool,
    current_user: UserResponse = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Enable or disable all TA configs for a trading instance."""
    instance = await _get_user_instance(db, UUID(instance_id), current_user.id)
    result = await db.execute(
        select(TechnicalAnalysisConfig).where(
            TechnicalAnalysisConfig.trading_instance_id == instance.id
        )
    )
    configs = result.scalars().all()
    for c in configs:
        c.enabled = enabled
    await db.commit()

    return {
        "instance_id": str(instance.id),
        "ta_enabled": enabled,
        "config_count": len(configs),
    }


@router.get("/technical-analysis/indicators", response_model=list[IndicatorDescription])
async def list_indicators(
    current_user: UserResponse = Depends(get_current_user_from_token),
) -> list[dict[str, Any]]:
    """List all available TA indicators with descriptions and default params."""
    return get_indicator_descriptions()
