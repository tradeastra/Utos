"""
Money Management Preset model — capital allocation presets.

Built-in presets: MM30 (30 steps), MM50 (50 steps), MM70 (70 steps).
Users can create custom presets (Pro+ tier).

Core formula:
  buy_amount = capital / steps
  max_coins  = capital / buy_amount
"""

import uuid

from database.base import GUID, Base, JSONBCompat
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class MMPreset(Base):
    """Money Management presets — control buy amount and max coin allocation."""

    __tablename__ = "mm_presets"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    preset_type: Mapped[str] = mapped_column(String(20), nullable=False)
    steps: Mapped[int] = mapped_column(Integer, nullable=False)
    min_capital: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    max_capital: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_coin_groups: Mapped[list[str] | None] = mapped_column(JSONBCompat(), nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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

    user: Mapped["User | None"] = relationship("User")

    __table_args__ = (
        Index("idx_mm_presets_user_id", "user_id"),
        Index("idx_mm_presets_preset_type", "preset_type"),
        Index("idx_mm_presets_is_builtin", "is_builtin"),
    )

    def __repr__(self) -> str:
        return f"<MMPreset id={self.id} name={self.name} steps={self.steps}>"
