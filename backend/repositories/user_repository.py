"""
User repository — async CRUD for the users table.
"""

from models.user import User
from sqlalchemy import select

from repositories.base import IRepository


class UserRepository(IRepository[User]):
    """Data-access layer for the User model."""

    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def exists_by_email(self, email: str) -> bool:
        result = await self._session.execute(
            select(User.id).where(User.email == email.lower())
        )
        return result.scalar_one_or_none() is not None

    async def get_by_referral_code(self, referral_code: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.referral_code == referral_code)
        )
        return result.scalar_one_or_none()
