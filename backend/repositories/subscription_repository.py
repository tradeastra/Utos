"""
Subscription repository — async CRUD for subscriptions table.
"""

import uuid

from sqlalchemy import select

from models.subscription import Subscription
from repositories.base import IRepository


class SubscriptionRepository(IRepository[Subscription]):
    model = Subscription

    async def get_by_user_id(self, user_id: uuid.UUID) -> Subscription | None:
        result = await self._session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_active(self) -> list[Subscription]:
        result = await self._session.execute(
            select(Subscription).where(Subscription.is_active.is_(True))
        )
        return list(result.scalars().all())
