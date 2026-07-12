"""
API v1 router — Sprint 01 scope: auth + users only.
"""

from fastapi import APIRouter

from api.v1.endpoints.auth import router as auth_router
from api.v1.endpoints.trading_instances import router as trading_instances_router
from api.v1.endpoints.users import router as users_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(trading_instances_router, prefix="/trading-instances", tags=["trading-instances"])
