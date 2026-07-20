"""
Grid profile repository — async CRUD for grid_profiles table.
"""

import uuid

from models.grid_profile import GridProfile
from sqlalchemy import select

from repositories.base import IRepository


class GridProfileRepository(IRepository[GridProfile]):
    model = GridProfile

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[GridProfile]:
        result = await self._session.execute(
            select(GridProfile).where(GridProfile.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_defaults(self) -> list[GridProfile]:
        result = await self._session.execute(
            select(GridProfile).where(GridProfile.is_default.is_(True))
        )
        return list(result.scalars().all())
