"""
API dependencies for UTOS Trading Engine.

This module provides FastAPI dependencies for authentication and authorization.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from database.base import get_db
from core.security import token_manager
from core.exceptions import AuthenticationError, AuthorizationError
from core.logging import get_logger

logger = get_logger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Get current user from JWT token."""
    try:
        # Verify the token
        payload = token_manager.verify_token(
            credentials.credentials,
            token_type="access"
        )
        
        # Extract user information
        user_id = payload.get("sub")
        if user_id is None:
            raise AuthenticationError("Invalid token payload")
        
        return {
            "user_id": user_id,
            "email": payload.get("email"),
            "role": payload.get("role"),
            "subscription_tier": payload.get("subscription_tier"),
        }
        
    except AuthenticationError as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    current_user_token: Dict[str, Any] = Depends(get_current_user_token),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get current user with database lookup."""
    try:
        # TODO: Implement actual user lookup from database
        # user = db.query(User).filter(User.id == current_user_token["user_id"]).first()
        # if user is None:
        #     raise AuthenticationError("User not found")
        
        # For now, return the token payload
        return current_user_token
        
    except AuthenticationError as e:
        logger.error(f"User lookup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected user lookup error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current active user."""
    try:
        # TODO: Check if user is active from database
        # if not current_user.is_active:
        #     raise AuthenticationError("User is not active")
        
        return current_user
        
    except AuthenticationError as e:
        logger.error(f"Active user check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_verified_user(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get current verified user."""
    try:
        # TODO: Check if user is verified from database
        # if not current_user.is_verified:
        #     raise AuthenticationError("User is not verified")
        
        return current_user
        
    except AuthenticationError as e:
        logger.error(f"Verified user check error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_role(required_role: str):
    """Create dependency to require specific role."""
    async def role_dependency(
        current_user: Dict[str, Any] = Depends(get_current_active_user)
    ) -> Dict[str, Any]:
        try:
            user_role = current_user.get("role")
            if user_role != required_role:
                raise AuthorizationError(f"Requires {required_role} role")
            
            return current_user
            
        except AuthorizationError as e:
            logger.error(f"Role authorization error: {e}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )
        except Exception as e:
            logger.error(f"Unexpected role check error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )
    
    return role_dependency


async def require_subscription(required_tier: str):
    """Create dependency to require specific subscription tier."""
    async def subscription_dependency(
        current_user: Dict[str, Any] = Depends(get_current_active_user)
    ) -> Dict[str, Any]:
        try:
            user_tier = current_user.get("subscription_tier")
            
            # Define tier hierarchy
            tier_hierarchy = {
                "free": 0,
                "basic": 1,
                "premium": 2,
                "enterprise": 3,
            }
            
            if tier_hierarchy.get(user_tier, 0) < tier_hierarchy.get(required_tier, 0):
                raise AuthorizationError(f"Requires {required_tier} subscription")
            
            return current_user
            
        except AuthorizationError as e:
            logger.error(f"Subscription authorization error: {e}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )
        except Exception as e:
            logger.error(f"Unexpected subscription check error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )
    
    return subscription_dependency


# Common dependencies
get_admin_user = require_role("admin")
get_moderator_user = require_role("moderator")
get_premium_user = require_subscription("premium")
get_enterprise_user = require_subscription("enterprise")


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """Get current user if token is provided, otherwise return None."""
    if credentials is None:
        return None
    
    try:
        return await get_current_user_token(credentials)
    except HTTPException:
        return None


class RateLimiter:
    """Simple rate limiter using Redis."""
    
    def __init__(self, requests: int, window: int):
        self.requests = requests
        self.window = window
    
    async def __call__(
        self,
        current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user)
    ) -> None:
        """Check rate limit."""
        try:
            from database.redis_client import cache
            
            # Use user ID or IP for rate limiting
            key = current_user["user_id"] if current_user else "anonymous"
            
            # Check current count
            current = cache.get(f"rate_limit:{key}")
            if current is None:
                current = 0
            
            if current >= self.requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                )
            
            # Increment counter
            cache.set(f"rate_limit:{key}", current + 1, ttl=self.window)
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # Don't block requests if rate limiting fails


# Rate limiting dependencies
rate_limit_auth = RateLimiter(requests=10, window=60)  # 10 requests per minute
rate_limit_trading = RateLimiter(requests=100, window=60)  # 100 requests per minute
rate_limit_data = RateLimiter(requests=1000, window=60)  # 1000 requests per minute
