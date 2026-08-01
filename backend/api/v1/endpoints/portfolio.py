"""
Portfolio endpoints for UTOS Trading Engine.

This module provides endpoints for portfolio management.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from api.dependencies import get_current_user_token
from core.logging import get_logger
from database.base import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models.position import Position as PositionModel
from models.trading_instance import TradingInstance
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
logger = get_logger(__name__)


# Pydantic models
class PortfolioSummary(BaseModel):
    """Portfolio summary model."""

    total_value: Decimal
    total_investment: Decimal
    total_pnl: Decimal
    pnl_percentage: Decimal


class PositionResponse(BaseModel):
    """Position response model."""

    id: str
    trading_instance_id: str
    symbol: str
    side: str
    quantity: Decimal
    entry_price: Decimal
    current_price: Decimal
    value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    created_at: datetime


class PortfolioResponse(BaseModel):
    """Portfolio response model."""

    summary: PortfolioSummary
    positions: list[PositionResponse]


@router.get("/", response_model=PortfolioResponse)
async def get_portfolio(
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio summary for current user."""
    try:
        user_id = uuid.UUID(current_user["user_id"])

        result = await db.execute(
            select(PositionModel)
            .join(TradingInstance, PositionModel.trading_instance_id == TradingInstance.id)
            .where(
                TradingInstance.user_id == user_id,
                TradingInstance.deleted_at.is_(None),
            )
        )
        positions = result.scalars().all()

        total_value = sum(
            (p.value or Decimal(0)) for p in positions
        )
        total_investment = sum(
            (p.entry_price * p.quantity) for p in positions
        )
        total_pnl = sum(
            (p.unrealized_pnl or Decimal(0)) + (p.realized_pnl or Decimal(0))
            for p in positions
        )
        pnl_percentage = (
            (total_pnl / total_investment * Decimal(100))
            if total_investment > 0
            else Decimal(0)
        )

        return PortfolioResponse(
            summary=PortfolioSummary(
                total_value=Decimal(total_value),
                total_investment=Decimal(total_investment),
                total_pnl=Decimal(total_pnl),
                pnl_percentage=Decimal(pnl_percentage),
            ),
            positions=[
                PositionResponse(
                    id=str(p.id),
                    trading_instance_id=str(p.trading_instance_id),
                    symbol=p.symbol,
                    side=p.side.value if hasattr(p.side, "value") else str(p.side),
                    quantity=p.quantity,
                    entry_price=p.entry_price,
                    current_price=p.current_price or Decimal(0),
                    value=p.value,
                    unrealized_pnl=p.unrealized_pnl or Decimal(0),
                    realized_pnl=p.realized_pnl or Decimal(0),
                    created_at=p.created_at,
                )
                for p in positions
            ],
        )

    except Exception as e:
        logger.error(f"Get portfolio failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get portfolio",
        )


@router.get("/positions", response_model=list[PositionResponse])
async def get_positions(
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    """Get all positions for current user."""
    try:
        user_id = uuid.UUID(current_user["user_id"])

        result = await db.execute(
            select(PositionModel)
            .join(TradingInstance, PositionModel.trading_instance_id == TradingInstance.id)
            .where(
                TradingInstance.user_id == user_id,
                TradingInstance.deleted_at.is_(None),
            )
        )
        positions = result.scalars().all()

        return [
            PositionResponse(
                id=str(p.id),
                trading_instance_id=str(p.trading_instance_id),
                symbol=p.symbol,
                side=p.side.value if hasattr(p.side, "value") else str(p.side),
                quantity=p.quantity,
                entry_price=p.entry_price,
                current_price=p.current_price or Decimal(0),
                value=p.value,
                unrealized_pnl=p.unrealized_pnl or Decimal(0),
                realized_pnl=p.realized_pnl or Decimal(0),
                created_at=p.created_at,
            )
            for p in positions
        ]

    except Exception as e:
        logger.error(f"Get positions failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get positions",
        )
