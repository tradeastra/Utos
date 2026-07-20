"""
Transaction repository — async CRUD for transactions table.
"""

import uuid

from models.transaction import Transaction
from sqlalchemy import select

from repositories.base import IRepository


class TransactionRepository(IRepository[Transaction]):
    model = Transaction

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[Transaction]:
        result = await self._session.execute(
            select(Transaction).where(Transaction.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_by_status(self, status: str) -> list[Transaction]:
        result = await self._session.execute(
            select(Transaction).where(Transaction.status == status)
        )
        return list(result.scalars().all())
