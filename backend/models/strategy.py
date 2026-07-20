"""
Strategy model — matches DATABASE.md §2.7.
"""

import uuid

from core.domain_types import StrategyType
from database.base import GUID, Base
from sqlalchemy import Boolean, DateTime, Enum, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Strategy(Base):
    """Strategies table."""

    __tablename__ = "strategies"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    type: Mapped[StrategyType] = mapped_column(
        Enum(StrategyType, name="strategy_type", values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    min_investment: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    max_investment: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    trading_instances: Mapped[list["TradingInstance"]] = relationship(
        back_populates="strategy"
    )

    def __repr__(self) -> str:
        return f"<Strategy id={self.id} name={self.name}>"
