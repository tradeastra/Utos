"""
StrategyMode model — configurable strategy mode definitions.

Stores the take-profit range and risk level for each strategy mode
(A, B, C, D, U) so that admins can tune them at runtime and the
changes persist across backend restarts.

Replaces the former hardcoded ``STRATEGY_MODES_CONFIG`` list in
``api.v1.endpoints.admin``.
"""

from database.base import Base
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func


class StrategyMode(Base):
    """A single strategy mode (e.g. A=Steady, B=Conventional, …)."""

    __tablename__ = "strategy_modes"

    mode: Mapped[str] = mapped_column(String(2), primary_key=True)
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    tp_range_min: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tp_range_max: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="Medium")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<StrategyMode mode={self.mode} label={self.label} tp_max={self.tp_range_max}>"
