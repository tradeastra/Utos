"""
Transaction model — matches DATABASE.md §2.8.
"""

import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, Text
from database.base import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.types import TransactionType
from database.base import Base


class Transaction(Base):
    """Transactions table."""

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False
    )
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="transaction_type"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    completed_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="transactions")

    __table_args__ = (
        Index("idx_transactions_user_id", "user_id"),
        Index("idx_transactions_type", "type"),
        Index("idx_transactions_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Transaction id={self.id} type={self.type} amount={self.amount}>"
