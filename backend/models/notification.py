"""
Notification model — matches DATABASE.md §2.11.
"""

import enum
import uuid

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from database.base import GUID, JSONBCompat
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database.base import Base


class NotificationType(str, enum.Enum):
    ORDER_FILLED = "order_filled"
    ORDER_FAILED = "order_failed"
    GRID_COMPLETED = "grid_completed"
    PROFIT_LOCK = "profit_lock"
    ERROR = "error"
    SYSTEM = "system"
    SUBSCRIPTION = "subscription"


class Notification(Base):
    """Notifications table."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict | None] = mapped_column(JSONBCompat(), nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="notifications")

    __table_args__ = (
        Index("idx_notifications_user_id", "user_id"),
        Index("idx_notifications_type", "type"),
        Index("idx_notifications_is_read", "is_read"),
    )

    def __repr__(self) -> str:
        return f"<Notification id={self.id} user={self.user_id} type={self.type}>"
