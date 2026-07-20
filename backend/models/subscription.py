"""
Subscription model — matches DATABASE.md §2.9.
"""

import uuid

from database.base import GUID, Base
from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from models.user import SubscriptionTier


class Subscription(Base):
    """Subscriptions table."""

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), unique=True, nullable=False
    )
    tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, name="subscription_tier_enum", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    start_date: Mapped[DateTime] = mapped_column(Date, nullable=False)
    end_date: Mapped[DateTime] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="subscription")

    __table_args__ = (
        Index("uq_subscriptions_user_id", "user_id", unique=True),
        Index("idx_subscriptions_tier", "tier"),
    )

    def __repr__(self) -> str:
        return f"<Subscription id={self.id} user={self.user_id} tier={self.tier}>"
