"""
Exchange account endpoints for UTOS Trading Engine.

This module provides endpoints for managing exchange accounts.
"""

import base64
import os
import uuid
from datetime import UTC, datetime

from cryptography.fernet import Fernet
from database.base import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models.exchange_account import ExchangeAccount
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_user_token

router = APIRouter()


def _get_fernet() -> Fernet:
    """Get Fernet cipher for encrypting API keys."""
    key = os.environ.get("ENCRYPTION_KEY", "")
    if not key:
        # Generate a deterministic key from SECRET_KEY fallback
        from core.config import settings

        raw = settings.SECRET_KEY.encode()[:32]
        key = base64.urlsafe_b64encode(raw.ljust(32, b"0"))
    else:
        key = key.encode() if isinstance(key, str) else key
    return Fernet(key)


def _encrypt(value: str) -> str:
    """Encrypt a string value."""
    return _get_fernet().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    """Decrypt a string value."""
    return _get_fernet().decrypt(value.encode()).decode()


# Pydantic models
class ExchangeAccountCreate(BaseModel):
    """Exchange account creation model."""

    exchange_name: str = Field(..., description="Exchange name (e.g., binance, bybit)")
    api_key: str = Field(..., description="API key")
    api_secret: str = Field(..., description="API secret")
    passphrase: str | None = Field(None, description="Passphrase (for some exchanges)")
    is_testnet: bool = Field(False, description="Use testnet")


class ExchangeAccountResponse(BaseModel):
    """Exchange account response model."""

    id: str
    user_id: str
    exchange_name: str
    is_testnet: bool
    is_active: bool
    connection_status: str
    created_at: datetime
    updated_at: datetime


@router.post("/", response_model=ExchangeAccountResponse)
async def create_exchange_account(
    account_data: ExchangeAccountCreate,
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    """Create a new exchange account."""
    user_id = current_user["user_id"]

    # Check if user already has an account for this exchange + testnet combo
    existing = await db.execute(
        select(ExchangeAccount).where(
            ExchangeAccount.user_id == uuid.UUID(user_id),
            ExchangeAccount.exchange_name == account_data.exchange_name,
            ExchangeAccount.is_testnet == account_data.is_testnet,
            ExchangeAccount.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Exchange account already exists for this exchange and testnet mode",
        )

    account = ExchangeAccount(
        user_id=uuid.UUID(user_id),
        exchange_name=account_data.exchange_name,
        account_name=f"{account_data.exchange_name}_{'testnet' if account_data.is_testnet else 'mainnet'}",
        api_key_encrypted=_encrypt(account_data.api_key),
        api_secret_encrypted=_encrypt(account_data.api_secret),
        is_testnet=account_data.is_testnet,
        is_active=True,
        connection_status="connected",
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)

    return ExchangeAccountResponse(
        id=str(account.id),
        user_id=str(account.user_id),
        exchange_name=account.exchange_name,
        is_testnet=account.is_testnet,
        is_active=account.is_active,
        connection_status=account.connection_status,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


@router.get("/", response_model=list[ExchangeAccountResponse])
async def list_exchange_accounts(
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    """List exchange accounts for current user."""
    user_id = current_user["user_id"]
    result = await db.execute(
        select(ExchangeAccount).where(
            ExchangeAccount.user_id == uuid.UUID(user_id),
            ExchangeAccount.deleted_at.is_(None),
        )
    )
    accounts = result.scalars().all()
    return [
        ExchangeAccountResponse(
            id=str(a.id),
            user_id=str(a.user_id),
            exchange_name=a.exchange_name,
            is_testnet=a.is_testnet,
            is_active=a.is_active,
            connection_status=a.connection_status,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
        for a in accounts
    ]


@router.delete("/{account_id}")
async def delete_exchange_account(
    account_id: str,
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    """Delete a exchange account (soft delete)."""
    user_id = current_user["user_id"]
    result = await db.execute(
        select(ExchangeAccount).where(
            ExchangeAccount.id == uuid.UUID(account_id),
            ExchangeAccount.user_id == uuid.UUID(user_id),
            ExchangeAccount.deleted_at.is_(None),
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Exchange account not found"
        )

    account.deleted_at = datetime.now(tz=UTC)
    await db.commit()
    return {"message": "Exchange account deleted successfully"}


async def _get_adapter_for_account(account: ExchangeAccount):
    """Create and initialize a Binance adapter from a saved exchange account."""
    from core.domain_types import ExchangeAdapterConfig, ExchangeCredentials
    from exchanges.adapters.binance import BinanceSpotAdapter

    adapter = BinanceSpotAdapter()
    config = ExchangeAdapterConfig(
        exchange_name=account.exchange_name,
        is_testnet=account.is_testnet,
        rest_url="",
        market_stream_url="",
        request_timeout=30,
    )
    await adapter.initialize(config)

    credentials = ExchangeCredentials(
        exchange_name=account.exchange_name,
        api_key=_decrypt(account.api_key_encrypted),
        api_secret=_decrypt(account.api_secret_encrypted),
    )
    await adapter.authenticate(credentials)
    return adapter


@router.get("/{account_id}/balance")
async def get_account_balance(
    account_id: str,
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
):
    """Get account balance from exchange using saved API keys."""
    user_id = current_user["user_id"]
    result = await db.execute(
        select(ExchangeAccount).where(
            ExchangeAccount.id == uuid.UUID(account_id),
            ExchangeAccount.user_id == uuid.UUID(user_id),
            ExchangeAccount.deleted_at.is_(None),
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Exchange account not found"
        )

    try:
        adapter = await _get_adapter_for_account(account)
        balances = await adapter.get_balance()
        await adapter.disconnect()
        return {
            "balances": [
                {
                    "currency": b.currency,
                    "available": str(b.available),
                    "locked": str(b.locked),
                    "total": str(b.total),
                }
                for b in balances
                if b.total > 0
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch balance: {e}",
        )


@router.get("/{account_id}/orders")
async def get_account_orders(
    account_id: str,
    current_user: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
    symbol: str | None = None,
    limit: int = 50,
):
    """Get order history from exchange using saved API keys."""
    user_id = current_user["user_id"]
    result = await db.execute(
        select(ExchangeAccount).where(
            ExchangeAccount.id == uuid.UUID(account_id),
            ExchangeAccount.user_id == uuid.UUID(user_id),
            ExchangeAccount.deleted_at.is_(None),
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Exchange account not found"
        )

    try:
        adapter = await _get_adapter_for_account(account)
        open_orders = await adapter.get_open_orders(symbol)
        await adapter.disconnect()
        return {
            "open_orders": [
                {
                    "order_id": str(o.order_id),
                    "symbol": o.symbol,
                    "side": o.side,
                    "order_type": o.order_type,
                    "quantity": str(o.quantity),
                    "price": str(o.price) if o.price else None,
                    "status": o.status,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                }
                for o in open_orders
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch orders: {e}",
        )
