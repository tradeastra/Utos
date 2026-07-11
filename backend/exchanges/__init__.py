"""
Exchange infrastructure layer for UTOS Trading Engine.

This package provides the foundational abstractions and utilities that all
exchange-specific adapters will build on in later sprints.
"""

from exchanges.adapter import IExchangeAdapter
from exchanges.errors import ErrorMapper
from exchanges.factory import ExchangeFactory
from exchanges.credential_manager import CredentialManager
from exchanges.rate_limiter import RateLimiter
from exchanges.retry import RetryPolicy
from exchanges.http_client import HttpClient
from exchanges.websocket_manager import WebSocketManager

__all__ = [
    "IExchangeAdapter",
    "ErrorMapper",
    "ExchangeFactory",
    "CredentialManager",
    "RateLimiter",
    "RetryPolicy",
    "HttpClient",
    "WebSocketManager",
]
