"""
API v1 router — Sprint 01 scope: auth + users only.
"""

from api.v1.endpoints.auth import router as auth_router
from api.v1.endpoints.addons import router as addons_router
from api.v1.endpoints.exchange_accounts import router as exchange_accounts_router
from api.v1.endpoints.grid_profiles import router as grid_profiles_router
from api.v1.endpoints.market import router as market_router
from api.v1.endpoints.strategies import router as strategies_router
from api.v1.endpoints.trading_instances import router as trading_instances_router
from api.v1.endpoints.users import router as users_router
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(
    trading_instances_router, prefix="/trading-instances", tags=["trading-instances"]
)
api_router.include_router(market_router, prefix="/market", tags=["market"])
api_router.include_router(
    exchange_accounts_router, prefix="/exchange-accounts", tags=["exchange-accounts"]
)
api_router.include_router(
    strategies_router, prefix="/strategies", tags=["strategies"]
)
api_router.include_router(
    grid_profiles_router, prefix="/grid-profiles", tags=["grid-profiles"]
)
api_router.include_router(
    addons_router, prefix="/addons", tags=["addons"]
)
