"""
API v1 router — Sprint 01 scope: auth + users only.
"""

from api.v1.endpoints.auth import router as auth_router
from api.v1.endpoints.addons import router as addons_router
from api.v1.endpoints.admin import router as admin_router
from api.v1.endpoints.averaging_config import router as averaging_config_router
from api.v1.endpoints.breaker_thresholds import router as breaker_thresholds_router
from api.v1.endpoints.coin_groups import router as coin_groups_router
from api.v1.endpoints.exchange_accounts import router as exchange_accounts_router
from api.v1.endpoints.grid_profiles import router as grid_profiles_router
from api.v1.endpoints.market import router as market_router
from api.v1.endpoints.mm_presets import router as mm_presets_router
from api.v1.endpoints.orders import router as orders_router
from api.v1.endpoints.portfolio import router as portfolio_router
from api.v1.endpoints.strategies import router as strategies_router
from api.v1.endpoints.technical_analysis import router as technical_analysis_router
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
api_router.include_router(
    coin_groups_router, prefix="/coin-groups", tags=["coin-groups"]
)
api_router.include_router(
    mm_presets_router, prefix="/mm-presets", tags=["mm-presets"]
)
api_router.include_router(
    admin_router, prefix="/admin", tags=["admin"]
)
api_router.include_router(
    breaker_thresholds_router, prefix="/breaker-thresholds", tags=["breaker-thresholds"]
)
api_router.include_router(
    averaging_config_router, prefix="/trading-instances", tags=["averaging-config"]
)
api_router.include_router(
    technical_analysis_router, prefix="/trading-instances", tags=["technical-analysis"]
)
api_router.include_router(
    portfolio_router, prefix="/portfolio", tags=["portfolio"]
)
api_router.include_router(
    orders_router, prefix="/orders", tags=["orders"]
)
