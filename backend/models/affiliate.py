"""
Affiliate model — matches DATABASE.md §2.10.
"""

import uuid

from database.base import GUID, Base
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Affiliate(Base):
    """Affiliates table."""

    __tablename__ = "affiliates"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), unique=True, nullable=False
    )
    commission_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    total_earnings: Mapped[float] = mapped_column(
        Numeric(20, 8), default=0, nullable=False
    )
    total_referrals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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

    user: Mapped["User"] = relationship(back_populates="affiliate")

    __table_args__ = (Index("uq_affiliates_user_id", "user_id", unique=True),)

    def __repr__(self) -> str:
        return f"<Affiliate id={self.id} user={self.user_id}>"
