"""
Notification repository — async CRUD for notifications table.
"""

import uuid

from models.notification import Notification
from sqlalchemy import select

from repositories.base import IRepository


class NotificationRepository(IRepository[Notification]):
    model = Notification

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[Notification]:
        result = await self._session.execute(
            select(Notification).where(Notification.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_unread(self, user_id: uuid.UUID) -> list[Notification]:
        result = await self._session.execute(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        return list(result.scalars().all())

    async def mark_as_read(self, notification_id: uuid.UUID) -> Notification | None:
        result = await self._session.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        notification = result.scalar_one_or_none()
        if notification:
            notification.is_read = True
            from sqlalchemy.sql import func

            notification.read_at = func.now()
            await self._session.flush()
            await self._session.refresh(notification)
        return notification
