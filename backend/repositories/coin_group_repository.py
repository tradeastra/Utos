"""CoinGroup repository — CRUD for coin selection groups."""

import uuid

from models.coin_group import CoinGroup
from repositories.base import IRepository
from sqlalchemy import select


class CoinGroupRepository(IRepository[CoinGroup]):
    model = CoinGroup

    async def get_builtin_groups(self) -> list[CoinGroup]:
        result = await self._session.execute(
            select(CoinGroup).where(CoinGroup.is_builtin.is_(True))
        )
        return list(result.scalars().all())

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[CoinGroup]:
        result = await self._session.execute(
            select(CoinGroup).where(
                (CoinGroup.user_id == user_id) | (CoinGroup.is_builtin.is_(True))
            )
        )
        return list(result.scalars().all())

    async def get_active_by_user_id(self, user_id: uuid.UUID) -> list[CoinGroup]:
        result = await self._session.execute(
            select(CoinGroup).where(
                CoinGroup.is_active.is_(True),
                (CoinGroup.user_id == user_id) | (CoinGroup.is_builtin.is_(True)),
            )
        )
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> CoinGroup | None:
        """Look up a coin group by its exact name (built-in or user-owned)."""
        result = await self._session.execute(
            select(CoinGroup).where(CoinGroup.name == name)
        )
        return result.scalar_one_or_none()
