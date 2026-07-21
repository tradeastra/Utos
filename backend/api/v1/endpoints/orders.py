"""
Order management endpoints for UTOS Trading Engine.

This module provides endpoints for managing orders.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from api.dependencies import get_current_user_token
from core.domain_types import OrderStatus
from core.logging import get_logger
from database.base import get_db
from fastapi import APIRouter, Depends, HTTPException, Query, status
from models.order import Order
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
logger = get_logger(__name__)


# Pydantic models
class OrderResponse(BaseModel):
    """Order response model."""

    id: str
    exchange_order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal | None
    filled_quantity: Decimal
    average_fill_price: Decimal | None
    status: str
    created_at: datetime
    updated_at: datetime
    trading_instance_id: str


@router.get("/", response_model=list[OrderResponse])
async def list_orders(
    symbol: str | None = Query(None, description="Filter by symbol"),
    order_status: str | None = Query(
        None, alias="status", description="Filter by status"
    ),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of orders to return"
    ),
    offset: int = Query(0, ge=0, description="Number of orders to skip"),
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    """List orders for current user."""
    try:
        user_id = uuid.UUID(current_user["user_id"])

        stmt = (
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if symbol:
            stmt = stmt.where(Order.symbol == symbol.upper())
        if order_status:
            stmt = stmt.where(Order.status == OrderStatus(order_status))

        result = await db.execute(stmt)
        orders = result.scalars().all()

        return [
            OrderResponse(
                id=str(o.id),
                exchange_order_id=o.exchange_order_id or "",
                symbol=o.symbol,
                side=o.side.value if hasattr(o.side, "value") else str(o.side),
                order_type=o.order_type.value if hasattr(o.order_type, "value") else str(o.order_type),
                quantity=o.quantity,
                price=o.price,
                filled_quantity=o.filled_quantity,
                average_fill_price=o.average_fill_price,
                status=o.status.value if hasattr(o.status, "value") else str(o.status),
                created_at=o.created_at,
                updated_at=o.updated_at,
                trading_instance_id=str(o.trading_instance_id) if o.trading_instance_id else "",
            )
            for o in orders
        ]

    except Exception as e:
        logger.error(f"List orders failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list orders",
        )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific order."""
    try:
        user_id = uuid.UUID(current_user["user_id"])

        result = await db.execute(
            select(Order).where(
                Order.id == uuid.UUID(order_id),
                Order.user_id == user_id,
            )
        )
        order = result.scalar_one_or_none()
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )

        return OrderResponse(
            id=str(order.id),
            exchange_order_id=order.exchange_order_id or "",
            symbol=order.symbol,
            side=order.side.value if hasattr(order.side, "value") else str(order.side),
            order_type=order.order_type.value if hasattr(order.order_type, "value") else str(order.order_type),
            quantity=order.quantity,
            price=order.price,
            filled_quantity=order.filled_quantity,
            average_fill_price=order.average_fill_price,
            status=order.status.value if hasattr(order.status, "value") else str(order.status),
            created_at=order.created_at,
            updated_at=order.updated_at,
            trading_instance_id=str(order.trading_instance_id) if order.trading_instance_id else "",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get order failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get order",
        )


@router.delete("/{order_id}")
async def cancel_order(
    order_id: str,
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    """Cancel an order."""
    try:
        user_id = uuid.UUID(current_user["user_id"])

        result = await db.execute(
            select(Order).where(
                Order.id == uuid.UUID(order_id),
                Order.user_id == user_id,
            )
        )
        order = result.scalar_one_or_none()
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )

        cancellable_statuses = {OrderStatus.PENDING, OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED}
        if order.status not in cancellable_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel order with status: {order.status.value}",
            )

        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now(tz=UTC)
        await db.commit()

        return {"message": "Order cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cancel order failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Order cancellation failed"
        )
