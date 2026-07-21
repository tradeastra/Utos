"""
CoinGroup model — Moonbot-style coin selection groups.

Replaces fixed "Coin Groups" with subscription-tier-limited selection.
Built-in groups: 3 Kings, 5 Kings, Top 10, Top 20, Top 50, All.
Users can also create custom groups (Pro+ tier).
"""

import uuid

from database.base import GUID, Base, JSONBCompat
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class CoinGroup(Base):
    """Coin selection groups — determines which coins are monitored/traded."""

    __tablename__ = "coin_groups"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_coins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    coins: Mapped[list[str]] = mapped_column(JSONBCompat(), nullable=False, default=list)
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
        Index("idx_coin_groups_user_id", "user_id"),
        Index("idx_coin_groups_is_builtin", "is_builtin"),
    )

    def __repr__(self) -> str:
        return f"<CoinGroup id={self.id} name={self.name} coins={len(self.coins)}>"
