"""
Position model — matches DATABASE.md §2.4.
"""

import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String
from database.base import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.types import PositionSide
from database.base import Base


class Position(Base):
    """Positions table."""

    __tablename__ = "positions"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    trading_instance_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("trading_instances.id"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[PositionSide] = mapped_column(
        Enum(PositionSide, name="position_side"), nullable=False
    )
    entry_price: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    current_price: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    unrealized_pnl: Mapped[float] = mapped_column(Numeric(20, 8), default=0, nullable=False)
    realized_pnl: Mapped[float] = mapped_column(Numeric(20, 8), default=0, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    trading_instance: Mapped["TradingInstance"] = relationship(
        back_populates="positions"
    )

    __table_args__ = (
        Index("idx_positions_trading_instance_id", "trading_instance_id"),
        Index("idx_positions_symbol", "symbol"),
    )

    def __repr__(self) -> str:
        return f"<Position id={self.id} symbol={self.symbol} side={self.side}>"
