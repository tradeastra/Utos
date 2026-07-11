"""
Exchange account repository — async CRUD for exchange_accounts table.
"""

from typing import Optional
import uuid

from sqlalchemy import select

from models.exchange_account import ExchangeAccount
from repositories.base import IRepository


class ExchangeAccountRepository(IRepository[ExchangeAccount]):
    model = ExchangeAccount

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[ExchangeAccount]:
        result = await self._session.execute(
            select(ExchangeAccount).where(ExchangeAccount.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_active_by_user(self, user_id: uuid.UUID) -> list[ExchangeAccount]:
        result = await self._session.execute(
            select(ExchangeAccount).where(
                ExchangeAccount.user_id == user_id,
                ExchangeAccount.is_active.is_(True),
            )
        )
        return list(result.scalars().all())
