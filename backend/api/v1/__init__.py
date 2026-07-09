"""
API v1 router for UTOS Trading Engine.

This module aggregates all API version 1 routes.
"""

from fastapi import APIRouter
from .endpoints import (
    auth,
    trading_instances,
    users,
    exchange_accounts,
    portfolio,
    orders,
    health,
)

# Create API router
api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(exchange_accounts.router, prefix="/exchange-accounts", tags=["exchange-accounts"])
api_router.include_router(trading_instances.router, prefix="/trading-instances", tags=["trading-instances"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
