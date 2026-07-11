"""
Order model — matches DATABASE.md §2.5.
"""

import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text
from database.base import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.types import OrderSide, OrderStatus, OrderType
from database.base import Base


class Order(Base):
    """Orders table."""

    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False
    )
    exchange_account_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("exchange_accounts.id"), nullable=False
    )
    trading_instance_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("trading_instances.id"), nullable=True
    )
    exchange_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[OrderSide] = mapped_column(
        Enum(OrderSide, name="order_side"), nullable=False
    )
    order_type: Mapped[OrderType] = mapped_column(
        Enum(OrderType, name="order_type"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    price: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    stop_price: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)

    filled_quantity: Mapped[float] = mapped_column(Numeric(20, 8), default=0, nullable=False)
    average_fill_price: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)

    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status"),
        default=OrderStatus.PENDING,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    grid_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    purpose: Mapped[str] = mapped_column(String(30), default="grid", nullable=False)
    is_profit_lock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    filled_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="orders")
    exchange_account: Mapped["ExchangeAccount"] = relationship(back_populates="orders")
    trading_instance: Mapped["TradingInstance | None"] = relationship(
        back_populates="orders"
    )

    __table_args__ = (
        Index("idx_orders_user_id", "user_id"),
        Index("idx_orders_exchange_account_id", "exchange_account_id"),
        Index("idx_orders_trading_instance_id", "trading_instance_id"),
        Index("idx_orders_exchange_order_id", "exchange_order_id"),
        Index("idx_orders_symbol", "symbol"),
        Index("idx_orders_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} symbol={self.symbol} status={self.status}>"
