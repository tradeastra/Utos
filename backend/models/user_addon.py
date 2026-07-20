"""UserAddOn model — tracks add-on purchases per user."""

import uuid
from datetime import datetime

from database.base import GUID, Base
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class UserAddOn(Base):
    """User add-ons table — tracks purchased add-on features."""

    __tablename__ = "user_addons"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False
    )
    addon_key: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    purchased_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[DateTime | None] = mapped_column(
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

    user: Mapped["User"] = relationship("User", backref="addons")

    __table_args__ = (
        Index("idx_user_addons_user_id", "user_id"),
        Index("idx_user_addons_addon_key", "addon_key"),
        Index("uq_user_addons_user_addon", "user_id", "addon_key", unique=True),
    )

    def __repr__(self) -> str:
        return f"<UserAddOn id={self.id} user={self.user_id} addon={self.addon_key}>"
