"""MMPreset repository — CRUD for money management presets."""

import uuid

from models.mm_preset import MMPreset
from repositories.base import IRepository
from sqlalchemy import select


class MMPresetRepository(IRepository[MMPreset]):
    model = MMPreset

    async def get_builtin_presets(self) -> list[MMPreset]:
        result = await self._session.execute(
            select(MMPreset).where(MMPreset.is_builtin.is_(True))
        )
        return list(result.scalars().all())

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[MMPreset]:
        result = await self._session.execute(
            select(MMPreset).where(
                (MMPreset.user_id == user_id) | (MMPreset.is_builtin.is_(True))
            )
        )
        return list(result.scalars().all())

    async def get_active_by_user_id(self, user_id: uuid.UUID) -> list[MMPreset]:
        result = await self._session.execute(
            select(MMPreset).where(
                MMPreset.is_active.is_(True),
                (MMPreset.user_id == user_id) | (MMPreset.is_builtin.is_(True)),
            )
        )
        return list(result.scalars().all())
