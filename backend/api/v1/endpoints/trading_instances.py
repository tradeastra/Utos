"""Trading instances endpoints for UTOS Trading Engine.

This module provides endpoints for managing trading processes.
A TradingProcess is the runtime wrapper around a TradingInstance row.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from api.v1.endpoints.users import get_current_user_from_token
from core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    InvalidStateTransition,
    TradingInstanceNotFound,
    ValidationError,
)
from core.types import TradingInstanceStatus
from engine.trading.process_manager import TradingProcessManager, get_process_manager
from models.user import User

router = APIRouter()


class TradingInstanceCreate(BaseModel):
    """Request model for creating a trading process."""

    exchange_account_id: str = Field(..., description="Exchange account ID")
    strategy_id: str = Field(..., description="Strategy ID")
    grid_profile_id: str = Field(..., description="Grid profile ID")
    symbol: str = Field(..., description="Trading symbol (e.g., BTCUSDT)")
    start_price: float | None = Field(None, description="Starting price")
    total_investment: float = Field(..., gt=0, description="Total investment amount")
    base_currency: str = Field("", description="Base currency")
    quote_currency: str = Field("", description="Quote currency")


class TradingInstanceResponse(BaseModel):
    """Response model for trading instance."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    exchange_account_id: str
    strategy_id: str
    grid_profile_id: str
    symbol: str
    status: TradingInstanceStatus
    start_price: float | None = None
    current_price: float | None = None
    total_investment: float = 0.0
    base_currency: str = ""
    quote_currency: str = ""
    profit_lock_enabled: bool = False
    portfolio_lock_enabled: bool = False
    worker_id: str | None = None
    memory_version: int = 0
    error_message: str | None = None
    started_at: str | None = None
    stopped_at: str | None = None
    deleted_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class TradingInstanceStatusResponse(BaseModel):
    """Short status response for lifecycle actions."""

    id: str
    status: str


def _to_response(instance: Any) -> dict[str, Any]:
    """Convert a TradingInstance to a dict for the response model."""
    return {
        "id": str(instance.id),
        "user_id": str(instance.user_id),
        "exchange_account_id": str(instance.exchange_account_id),
        "strategy_id": str(instance.strategy_id),
        "grid_profile_id": str(instance.grid_profile_id),
        "symbol": instance.symbol,
        "status": instance.status,
        "start_price": float(instance.start_price) if instance.start_price is not None else None,
        "current_price": float(instance.current_price) if instance.current_price is not None else None,
        "total_investment": float(instance.total_investment) if instance.total_investment is not None else 0.0,
        "base_currency": instance.base_currency or "",
        "quote_currency": instance.quote_currency or "",
        "profit_lock_enabled": bool(instance.profit_lock_enabled),
        "portfolio_lock_enabled": bool(instance.portfolio_lock_enabled),
        "worker_id": instance.worker_id,
        "memory_version": instance.memory_version or 0,
        "error_message": instance.error_message,
        "started_at": instance.started_at.isoformat() if instance.started_at else None,
        "stopped_at": instance.stopped_at.isoformat() if instance.stopped_at else None,
        "deleted_at": instance.deleted_at.isoformat() if instance.deleted_at else None,
        "created_at": instance.created_at.isoformat() if instance.created_at else None,
        "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
    }


def _handle_manager_exception(exc: Exception) -> None:
    """Map domain exceptions to FastAPI HTTPException."""
    if isinstance(exc, TradingInstanceNotFound):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, AuthenticationError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    if isinstance(exc, AuthorizationError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, (InvalidStateTransition, ValidationError)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("", response_model=TradingInstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_trading_instance(
    data: TradingInstanceCreate,
    current_user: User = Depends(get_current_user_from_token),
    manager: TradingProcessManager = Depends(get_process_manager),
) -> dict[str, Any]:
    """Create a new trading process (CREATED)."""
    try:
        instance = await manager.create_process(
            user_id=current_user.id,
            exchange_account_id=UUID(data.exchange_account_id),
            strategy_id=UUID(data.strategy_id),
            grid_profile_id=UUID(data.grid_profile_id),
            symbol=data.symbol.upper(),
            start_price=data.start_price,
            total_investment=data.total_investment,
            base_currency=data.base_currency,
            quote_currency=data.quote_currency,
        )
        return _to_response(instance)
    except Exception as exc:
        _handle_manager_exception(exc)


@router.get("", response_model=list[TradingInstanceResponse])
async def list_trading_instances(
    status_filter: TradingInstanceStatus | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user_from_token),
    manager: TradingProcessManager = Depends(get_process_manager),
) -> list[dict[str, Any]]:
    """List trading processes for the current user."""
    try:
        instances = await manager.list_by_user(current_user.id)
        if status_filter:
            instances = [i for i in instances if i.status == status_filter]
        return [_to_response(i) for i in instances]
    except Exception as exc:
        _handle_manager_exception(exc)


@router.get("/{instance_id}", response_model=TradingInstanceResponse)
async def get_trading_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user_from_token),
    manager: TradingProcessManager = Depends(get_process_manager),
) -> dict[str, Any]:
    """Get a single trading process."""
    try:
        instance = await manager.get_status(UUID(instance_id), current_user.id)
        return _to_response(instance)
    except Exception as exc:
        _handle_manager_exception(exc)


@router.post("/{instance_id}/prepare", response_model=TradingInstanceResponse)
async def prepare_trading_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user_from_token),
    manager: TradingProcessManager = Depends(get_process_manager),
) -> dict[str, Any]:
    """Prepare a trading process (CREATED -> READY)."""
    try:
        instance = await manager.prepare(UUID(instance_id), current_user.id)
        return _to_response(instance)
    except Exception as exc:
        _handle_manager_exception(exc)


@router.post("/{instance_id}/start", response_model=TradingInstanceResponse)
async def start_trading_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user_from_token),
    manager: TradingProcessManager = Depends(get_process_manager),
) -> dict[str, Any]:
    """Start a trading process (READY -> RUNNING)."""
    try:
        instance = await manager.start(UUID(instance_id), current_user.id)
        return _to_response(instance)
    except Exception as exc:
        _handle_manager_exception(exc)


@router.post("/{instance_id}/pause", response_model=TradingInstanceResponse)
async def pause_trading_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user_from_token),
    manager: TradingProcessManager = Depends(get_process_manager),
) -> dict[str, Any]:
    """Pause a trading process (RUNNING -> PAUSED)."""
    try:
        instance = await manager.pause(UUID(instance_id), current_user.id)
        return _to_response(instance)
    except Exception as exc:
        _handle_manager_exception(exc)


@router.post("/{instance_id}/resume", response_model=TradingInstanceResponse)
async def resume_trading_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user_from_token),
    manager: TradingProcessManager = Depends(get_process_manager),
) -> dict[str, Any]:
    """Resume a trading process (PAUSED -> RUNNING)."""
    try:
        instance = await manager.resume(UUID(instance_id), current_user.id)
        return _to_response(instance)
    except Exception as exc:
        _handle_manager_exception(exc)


@router.post("/{instance_id}/stop", response_model=TradingInstanceResponse)
async def stop_trading_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user_from_token),
    manager: TradingProcessManager = Depends(get_process_manager),
) -> dict[str, Any]:
    """Stop a trading process (RUNNING -> STOPPED)."""
    try:
        instance = await manager.stop(UUID(instance_id), current_user.id)
        return _to_response(instance)
    except Exception as exc:
        _handle_manager_exception(exc)


@router.delete("/{instance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trading_instance(
    instance_id: str,
    current_user: User = Depends(get_current_user_from_token),
    manager: TradingProcessManager = Depends(get_process_manager),
) -> None:
    """Soft-delete a trading process."""
    try:
        instance = await manager.get_status(UUID(instance_id), current_user.id)
        if instance.status == TradingInstanceStatus.RUNNING:
            raise ValidationError("Cannot delete a running process; stop it first")
        instance.deleted_at = datetime.now(tz=timezone.utc)
        manager.session.add(instance)
        await manager.session.flush()
    except Exception as exc:
        _handle_manager_exception(exc)
