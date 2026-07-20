"""
Balance repository — async CRUD for balances table.
"""

import uuid

from models.balance import Balance
from sqlalchemy import select

from repositories.base import IRepository


class BalanceRepository(IRepository[Balance]):
    model = Balance

    async def get_by_exchange_account(self, account_id: uuid.UUID) -> list[Balance]:
        result = await self._session.execute(
            select(Balance).where(Balance.exchange_account_id == account_id)
        )
        return list(result.scalars().all())

    async def get_by_account_and_currency(
        self, account_id: uuid.UUID, currency: str
    ) -> Balance | None:
        result = await self._session.execute(
            select(Balance).where(
                Balance.exchange_account_id == account_id,
                Balance.currency == currency,
            )
        )
        return result.scalar_one_or_none()
