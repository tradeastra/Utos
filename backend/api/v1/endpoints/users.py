"""
User endpoints — Sprint 01: GET /users/me.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import AuthenticationError
from core.logging import get_logger
from core.security import TokenManager
from database.base import get_db
from repositories.user_repository import UserRepository
from schemas.auth import UserResponse

router = APIRouter()
logger = get_logger(__name__)
_bearer = HTTPBearer()
token_manager = TokenManager()


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Dependency: validate bearer token and return the DB user."""
    try:
        payload = token_manager.verify_token(credentials.credentials, token_type="access")
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_TOKEN", "message": str(exc), "details": None}},
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    repo = UserRepository(db)
    user = await repo.get_by_id(uuid.UUID(user_id_str))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found or inactive", "details": None}},
        )
    return user  # type: ignore[return-value]


@router.get("/me", response_model=dict)
async def get_me(user=Depends(get_current_user_from_token)) -> dict:
    """Return the authenticated user's profile."""
    return {
        "data": UserResponse.model_validate(user).model_dump(),
        "meta": {"timestamp": datetime.now(tz=timezone.utc).isoformat()},
    }
