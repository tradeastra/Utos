"""
Strategy repository — async CRUD for strategies table.
"""

from models.strategy import Strategy
from sqlalchemy import select

from repositories.base import IRepository


class StrategyRepository(IRepository[Strategy]):
    model = Strategy

    async def get_active(self) -> list[Strategy]:
        result = await self._session.execute(
            select(Strategy).where(Strategy.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> Strategy | None:
        result = await self._session.execute(
            select(Strategy).where(Strategy.name == name)
        )
        return result.scalar_one_or_none()
