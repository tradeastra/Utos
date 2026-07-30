"""Trading instances endpoints for UTOS Trading Engine.

This module provides endpoints for managing trading processes.
A TradingProcess is the runtime wrapper around a TradingInstance row.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, NoReturn
from uuid import UUID

from api.v1.endpoints.users import get_current_user_from_token
from core.domain_types import StrategyMode, TradingInstanceStatus
from core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    InvalidStateTransition,
    TradingInstanceNotFound,
    ValidationError,
)
from engine.trading.process_manager import TradingProcessManager, get_process_manager
from fastapi import APIRouter, Depends, HTTPException, Query, status
from models.user import User
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter()


class TradingInstanceCreate(BaseModel):
    """Request model for creating a trading process."""

    exchange_account_id: str = Field(..., description="Exchange account ID")
    strategy_id: str = Field(..., description="Strategy ID")
    grid_profile_id: str = Field(..., description="Grid profile ID")
    symbol: str = Field(..., description="Trading symbol (e.g., BTCUSDT)")
    start_price: float | None = Field(None, description="Starting price")
    total_investment: float | None = Field(None, description="Total investment — auto-calculated from grid profile if omitted")
    base_currency: str = Field("", description="Base currency")
    quote_currency: str = Field("", description="Quote currency")
    strategy_mode: str | None = Field(None, description="Strategy mode (A/B/C/D/U) — determines grid spacing")
    selected_coins: list[str] | None = Field(None, description="Coins selected from coin group (for audit/multi-bot)")
    continuation_rate: float | None = Field(None, description="Circuit breaker continuation rate (0.70/0.80/0.90)")
    breaker_enabled: bool = Field(True, description="Enable circuit breaker")
    auto_start: bool = Field(False, description="If true, automatically start the bot after creation (skip manual Start)")


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
    avg_enabled: bool = True
    non_stop: bool = False
    partial_sell: bool = False
    formula_mode: str = "default"
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


def _parse_strategy_mode(mode: str | None) -> StrategyMode | None:
    """Convert frontend mode letter (A/B/C/D/U) to StrategyMode enum."""
    if not mode:
        return None
    mode_upper = mode.upper()
    try:
        return StrategyMode[mode_upper]
    except KeyError:
        return None


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
        "start_price": (
            float(instance.start_price) if instance.start_price is not None else None
        ),
        "current_price": (
            float(instance.current_price)
            if instance.current_price is not None
            else None
        ),
        "total_investment": (
            float(instance.total_investment)
            if instance.total_investment is not None
            else 0.0
        ),
        "base_currency": instance.base_currency or "",
        "quote_currency": instance.quote_currency or "",
        "profit_lock_enabled": bool(instance.profit_lock_enabled),
        "portfolio_lock_enabled": bool(instance.portfolio_lock_enabled),
        "avg_enabled": bool(instance.avg_enabled) if hasattr(instance, "avg_enabled") else True,
        "non_stop": bool(instance.non_stop) if hasattr(instance, "non_stop") else False,
        "partial_sell": bool(instance.partial_sell) if hasattr(instance, "partial_sell") else False,
        "formula_mode": instance.formula_mode if hasattr(instance, "formula_mode") else "default",
        "worker_id": instance.worker_id,
        "memory_version": instance.memory_version or 0,
        "error_message": instance.error_message,
        "started_at": instance.started_at.isoformat() if instance.started_at else None,
        "stopped_at": instance.stopped_at.isoformat() if instance.stopped_at else None,
        "deleted_at": instance.deleted_at.isoformat() if instance.deleted_at else None,
        "created_at": instance.created_at.isoformat() if instance.created_at else None,
        "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
    }


def _handle_manager_exception(exc: Exception) -> NoReturn:
    """Map domain exceptions to FastAPI HTTPException."""
    if isinstance(exc, TradingInstanceNotFound):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, AuthenticationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, AuthorizationError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, (InvalidStateTransition, ValidationError)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
    )


@router.post(
    "", response_model=TradingInstanceResponse, status_code=status.HTTP_201_CREATED
)
async def create_trading_instance(
    data: TradingInstanceCreate,
    current_user: User = Depends(get_current_user_from_token),
    manager: TradingProcessManager = Depends(get_process_manager),
) -> dict[str, Any]:
    """Create a new trading process (CREATED)."""
    try:
        total_inv = data.total_investment
        if total_inv is None:
            from repositories.grid_profile_repository import GridProfileRepository
            from database.base import get_db

            async for session in get_db():
                repo = GridProfileRepository(session)
                profile = await repo.get_by_id(UUID(data.grid_profile_id))
                if profile:
                    total_inv = float(profile.grid_count) * float(profile.investment_per_grid)
                break

            if total_inv is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not determine total investment from grid profile",
                )

        instance = await manager.create_process(
            user_id=current_user.id,
            exchange_account_id=UUID(data.exchange_account_id),
            strategy_id=UUID(data.strategy_id),
            grid_profile_id=UUID(data.grid_profile_id),
            symbol=data.symbol.upper(),
            start_price=data.start_price,
            total_investment=total_inv,
            base_currency=data.base_currency,
            quote_currency=data.quote_currency,
            strategy_mode=_parse_strategy_mode(data.strategy_mode),
            selected_coins=data.selected_coins,
            continuation_rate=data.continuation_rate,
            breaker_enabled=data.breaker_enabled,
        )

        # Auto-start: skip the CREATED → READY → RUNNING manual steps.
        # The setup wizard uses this so users get a running bot in one click.
        if data.auto_start:
            instance = await manager.prepare(instance.id, current_user.id)
            instance = await manager.start(instance.id, current_user.id)

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
        instance.deleted_at = datetime.now(tz=UTC)
        manager.session.add(instance)
        await manager.session.flush()
    except Exception as exc:
        _handle_manager_exception(exc)


@router.get("/{instance_id}/grid", response_model=dict)
async def get_grid_state(
    instance_id: str,
    current_user: User = Depends(get_current_user_from_token),
    manager: TradingProcessManager = Depends(get_process_manager),
) -> dict[str, Any]:
    """Get grid state and levels for a trading instance."""
    try:
        instance = await manager.get_status(UUID(instance_id), current_user.id)

        from main import grid_engine

        if grid_engine is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Grid engine not initialized",
            )

        try:
            state = await grid_engine.get_grid_state(str(instance.id))
            levels = await grid_engine.get_grid_levels(str(instance.id))
        except Exception:
            return {
                "instance_id": str(instance.id),
                "status": "no_grid",
                "symbol": instance.symbol,
                "current_price": float(instance.current_price) if instance.current_price else None,
                "upper_price": 0,
                "lower_price": 0,
                "grid_count": 0,
                "grid_spacing": 0,
                "investment_per_grid": 0,
                "total_cycles": 0,
                "total_profit": 0,
                "levels": [],
            }

        return {
            "instance_id": str(instance.id),
            "status": state.status,
            "symbol": state.symbol,
            "current_price": float(instance.current_price) if instance.current_price else None,
            "upper_price": float(state.upper_price) if hasattr(state, "upper_price") else 0,
            "lower_price": float(state.lower_price) if hasattr(state, "lower_price") else 0,
            "grid_count": len(levels),
            "grid_spacing": float(state.grid_spacing) if hasattr(state, "grid_spacing") and state.grid_spacing else 0,
            "investment_per_grid": float(levels[0].quantity) if levels else 0,
            "total_cycles": state.total_cycles if hasattr(state, "total_cycles") else 0,
            "total_profit": float(state.total_profit) if hasattr(state, "total_profit") else 0,
            "levels": [
                {
                    "index": lv.level,
                    "price": float(lv.buy_price) if hasattr(lv, "buy_price") else 0,
                    "buy_price": float(lv.buy_price) if hasattr(lv, "buy_price") else 0,
                    "sell_price": float(lv.sell_price) if hasattr(lv, "sell_price") else 0,
                    "side": "buy" if lv.status.value in ("waiting", "open") else "sell",
                    "status": lv.status.value if hasattr(lv.status, "value") else str(lv.status),
                    "quantity": float(lv.quantity),
                    "order_id": lv.buy_order_id or lv.sell_order_id,
                }
                for lv in levels
            ],
        }
    except HTTPException:
        raise
    except Exception as exc:
        _handle_manager_exception(exc)


class TrailingProfitConfig(BaseModel):
    """Configuration for trailing profit lock."""
    trigger_percentage: float = Field(..., gt=0, description="Profit % to trigger trailing (e.g. 2.0)")
    trail_percentage: float = Field(..., gt=0, lt=100, description="Trail % below highest price (e.g. 1.5)")
    max_profit_percentage: float = Field(0, ge=0, description="Max profit % cap — auto-sell when reached. 0 = no cap (ride trend indefinitely)")


@router.post("/{instance_id}/trailing-profit", response_model=dict)
async def configure_trailing_profit(
    instance_id: str,
    config: TrailingProfitConfig,
    current_user: User = Depends(get_current_user_from_token),
    manager: TradingProcessManager = Depends(get_process_manager),
) -> dict[str, Any]:
    """Configure trailing profit for a trading instance.

    Requires 'trailing_profit' feature — available via starter+ subscription
    or by purchasing the trailing profit add-on.
    """
    try:
        instance = await manager.get_status(UUID(instance_id), current_user.id)

        from database.base import get_db as _get_db
        from repositories.user_addon_repository import UserAddOnRepository
        from services.saas.license import _DEFAULT_LIMITS

        tier = current_user.subscription_tier.value if hasattr(current_user.subscription_tier, "value") else str(current_user.subscription_tier)
        limits = _DEFAULT_LIMITS.get(tier, _DEFAULT_LIMITS["free"])

        has_via_tier = "trailing_profit" in limits.feature_flags

        addon_repo = UserAddOnRepository(manager.session)
        addon = await addon_repo.get_by_user_and_key(current_user.id, "trailing_profit")
        has_via_addon = addon is not None and addon.is_active

        if not has_via_tier and not has_via_addon:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Trailing Profit requires a Starter+ plan or the Trailing Profit add-on. Purchase it from the Add-ons page.",
            )

        from main import grid_engine

        if grid_engine is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Grid engine not initialized",
            )

        grid_engine.configure_trailing_profit(
            instance_id=str(instance.id),
            trigger_percentage=Decimal(str(config.trigger_percentage)),
            trail_percentage=Decimal(str(config.trail_percentage)),
            max_profit_percentage=Decimal(str(config.max_profit_percentage)),
        )

        return {
            "instance_id": str(instance.id),
            "trigger_percentage": config.trigger_percentage,
            "trail_percentage": config.trail_percentage,
            "max_profit_percentage": config.max_profit_percentage,
            "status": "configured",
        }
    except HTTPException:
        raise
    except Exception as exc:
        _handle_manager_exception(exc)


# ------------------------------------------------------------------
# Force Buy / Force Sell
# ------------------------------------------------------------------

class ForceBuyRequest(BaseModel):
    level: int | None = Field(None, ge=0, description="Grid level to buy at (auto-select if omitted)")
    price: float | None = Field(None, gt=0, description="Override buy price (defaults to level price)")
    quantity: float | None = Field(None, gt=0, description="Override quantity (defaults to level config)")


class ForceSellRequest(BaseModel):
    level: int | None = Field(None, ge=0, description="Grid level to sell (sell all filled if omitted)")
    price: float | None = Field(None, gt=0, description="Override sell price (defaults to current market price)")
    quantity: float | None = Field(None, gt=0, description="Partial sell quantity (defaults to full position)")


@router.post("/{instance_id}/force-buy")
async def force_buy(
    instance_id: str,
    data: ForceBuyRequest,
    current_user: User = Depends(get_current_user_from_token),
    manager: TradingProcessManager = Depends(get_process_manager),
) -> dict[str, Any]:
    """Force buy — manually place a buy order bypassing the planner.

    Spot market: initiates a buy at the specified level (or auto-selects next waiting level).
    After the forced buy fills, averaging continues automatically for subsequent levels.
    """
    try:
        instance = await manager.get_status(UUID(instance_id), current_user.id)

        from main import grid_engine

        if grid_engine is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Grid engine not initialized",
            )

        result = await grid_engine.force_buy(
            instance_id=str(instance.id),
            level=data.level,
            price=Decimal(str(data.price)) if data.price else None,
            quantity=Decimal(str(data.quantity)) if data.quantity else None,
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        _handle_manager_exception(exc)


@router.post("/{instance_id}/force-sell")
async def force_sell(
    instance_id: str,
    data: ForceSellRequest,
    current_user: User = Depends(get_current_user_from_token),
    manager: TradingProcessManager = Depends(get_process_manager),
) -> dict[str, Any]:
    """Force sell — manually close an existing position.

    Spot market: can only sell levels with FILLED status (coins we actually hold).
    If no level specified, sells ALL filled positions. Cannot short sell.
    """
    try:
        instance = await manager.get_status(UUID(instance_id), current_user.id)

        from main import grid_engine

        if grid_engine is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Grid engine not initialized",
            )

        result = await grid_engine.force_sell(
            instance_id=str(instance.id),
            level=data.level,
            price=Decimal(str(data.price)) if data.price else None,
            quantity=Decimal(str(data.quantity)) if data.quantity else None,
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        _handle_manager_exception(exc)


# ------------------------------------------------------------------
# Per-Coin Settings (Avg, Non-Stop, Partial Sell, Formula)
# ------------------------------------------------------------------

class PerCoinSettingsUpdate(BaseModel):
    """Update per-coin settings for a trading instance."""
    avg_enabled: bool | None = Field(None, description="Enable/disable averaging for this coin")
    non_stop: bool | None = Field(None, description="Continue averaging without stopping at limit")
    partial_sell: bool | None = Field(None, description="Allow partial selling instead of full position")
    formula_mode: str | None = Field(None, max_length=50, description="Averaging formula mode")


@router.patch("/{instance_id}/coin-settings", response_model=dict)
async def update_coin_settings(
    instance_id: str,
    data: PerCoinSettingsUpdate,
    current_user: User = Depends(get_current_user_from_token),
    manager: TradingProcessManager = Depends(get_process_manager),
) -> dict[str, Any]:
    """Update per-coin settings (avg, non-stop, partial sell, formula mode)."""
    try:
        instance = await manager.get_status(UUID(instance_id), current_user.id)

        changed = False
        if data.avg_enabled is not None:
            instance.avg_enabled = data.avg_enabled
            changed = True
        if data.non_stop is not None:
            instance.non_stop = data.non_stop
            changed = True
        if data.partial_sell is not None:
            instance.partial_sell = data.partial_sell
            changed = True
        if data.formula_mode is not None:
            instance.formula_mode = data.formula_mode
            changed = True

        if changed:
            manager.session.add(instance)
            await manager.session.flush()

        return {
            "instance_id": str(instance.id),
            "avg_enabled": bool(instance.avg_enabled),
            "non_stop": bool(instance.non_stop),
            "partial_sell": bool(instance.partial_sell),
            "formula_mode": instance.formula_mode,
            "updated": changed,
        }
    except HTTPException:
        raise
    except Exception as exc:
        _handle_manager_exception(exc)
