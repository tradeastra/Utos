"""
Exchange account model — matches DATABASE.md §2.2.
"""

import enum
import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from database.base import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database.base import Base


class ExchangeName(str, enum.Enum):
    BINANCE = "binance"
    BYBIT = "bybit"
    OKX = "okx"
    KRAKEN = "kraken"
    KUCOIN = "kucoin"


class ExchangeAccount(Base):
    """Exchange accounts table."""

    __tablename__ = "exchange_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False
    )
    exchange_name: Mapped[ExchangeName] = mapped_column(
        Enum(ExchangeName, name="exchange_name"), nullable=False
    )
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    api_secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)

    is_testnet: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_synced_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    connection_status: Mapped[str] = mapped_column(
        String(20), default="disconnected", nullable=False
    )
    deleted_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="exchange_accounts")
    trading_instances: Mapped[list["TradingInstance"]] = relationship(
        back_populates="exchange_account"
    )
    orders: Mapped[list["Order"]] = relationship(
        back_populates="exchange_account"
    )
    balances: Mapped[list["Balance"]] = relationship(
        back_populates="exchange_account", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_exchange_accounts_user_id", "user_id"),
        Index("idx_exchange_accounts_exchange_name", "exchange_name"),
    )

    def __repr__(self) -> str:
        return f"<ExchangeAccount id={self.id} exchange={self.exchange_name}>"
