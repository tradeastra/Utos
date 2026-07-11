"""
User model — matches DATABASE.md §2.1.
"""

import enum
import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String
from database.base import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database.base import Base


class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    """Users table."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.USER,
        nullable=False,
    )
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, name="subscription_tier"),
        default=SubscriptionTier.FREE,
        nullable=False,
    )

    referral_code: Mapped[str | None] = mapped_column(
        String(20), unique=True, nullable=True
    )
    referred_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=True
    )

    last_login_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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

    # Relationships
    exchange_accounts: Mapped[list["ExchangeAccount"]] = relationship(
        back_populates="user", foreign_keys="ExchangeAccount.user_id"
    )
    trading_instances: Mapped[list["TradingInstance"]] = relationship(
        back_populates="user", foreign_keys="TradingInstance.user_id"
    )
    orders: Mapped[list["Order"]] = relationship(
        back_populates="user", foreign_keys="Order.user_id"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user", foreign_keys="Notification.user_id"
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="user", foreign_keys="Transaction.user_id"
    )
    grid_profiles: Mapped[list["GridProfile"]] = relationship(
        back_populates="user", foreign_keys="GridProfile.user_id"
    )
    subscription: Mapped["Subscription | None"] = relationship(
        back_populates="user", uselist=False, foreign_keys="Subscription.user_id"
    )
    affiliate: Mapped["Affiliate | None"] = relationship(
        back_populates="user", uselist=False, foreign_keys="Affiliate.user_id"
    )
    referrer: Mapped["User | None"] = relationship(
        "User",
        remote_side="User.id",
        foreign_keys=[referred_by],
    )

    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_referral_code", "referral_code"),
        Index("idx_users_subscription_tier", "subscription_tier"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
