"""
Balance model — matches DATABASE.md §2.12.
"""

import uuid

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from database.base import GUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database.base import Base


class Balance(Base):
    """Balances table."""

    __tablename__ = "balances"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    exchange_account_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("exchange_accounts.id"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    available: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    locked: Mapped[float] = mapped_column(Numeric(20, 8), default=0, nullable=False)
    total: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)

    last_updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
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

    exchange_account: Mapped["ExchangeAccount"] = relationship(
        back_populates="balances"
    )

    __table_args__ = (
        Index("idx_balances_exchange_account_id", "exchange_account_id"),
        Index(
            "uq_balances_exchange_account_currency",
            "exchange_account_id",
            "currency",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<Balance account={self.exchange_account_id} currency={self.currency}>"
