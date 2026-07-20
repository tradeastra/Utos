"""UserAddOn repository — async CRUD for user_addons table."""

import uuid

from models.user_addon import UserAddOn
from sqlalchemy import select

from repositories.base import IRepository


class UserAddOnRepository(IRepository[UserAddOn]):
    model = UserAddOn

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[UserAddOn]:
        result = await self._session.execute(
            select(UserAddOn).where(UserAddOn.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_active_by_user_id(self, user_id: uuid.UUID) -> list[UserAddOn]:
        result = await self._session.execute(
            select(UserAddOn).where(
                UserAddOn.user_id == user_id,
                UserAddOn.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def get_by_user_and_key(
        self, user_id: uuid.UUID, addon_key: str
    ) -> UserAddOn | None:
        result = await self._session.execute(
            select(UserAddOn).where(
                UserAddOn.user_id == user_id,
                UserAddOn.addon_key == addon_key,
            )
        )
        return result.scalar_one_or_none()
