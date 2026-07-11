"""
Affiliate repository — async CRUD for affiliates table.
"""

import uuid

from sqlalchemy import select

from models.affiliate import Affiliate
from repositories.base import IRepository


class AffiliateRepository(IRepository[Affiliate]):
    model = Affiliate

    async def get_by_user_id(self, user_id: uuid.UUID) -> Affiliate | None:
        result = await self._session.execute(
            select(Affiliate).where(Affiliate.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_active(self) -> list[Affiliate]:
        result = await self._session.execute(
            select(Affiliate).where(Affiliate.is_active.is_(True))
        )
        return list(result.scalars().all())
