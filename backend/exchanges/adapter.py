"""
Abstract exchange adapter interface — Sprint 3 infrastructure layer.

All concrete exchange adapters (Binance, Hyperliquid, Bybit, OKX, MEXC, etc.)
must implement this interface in later sprints.
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, Callable, Optional

from core.types import (
    BalanceEntry,
    Candle,
    ExchangeAdapterConfig,
    ExchangeCredentials,
    ExchangeInfo,
    OrderBook,
    OrderResult,
    PositionEntry,
    TickerData,
    TradeEntry,
)


class IExchangeAdapter(ABC):
    """Abstract interface for all exchange adapters."""

    name: str = ""

    @abstractmethod
    async def initialize(self, config: ExchangeAdapterConfig) -> bool:
        """Load configuration and validate exchange info without opening network connections."""
        ...

    @abstractmethod
    async def authenticate(self, credentials: ExchangeCredentials) -> bool:
        """Perform a lightweight authentication check (e.g., account ping)."""
        ...

    @abstractmethod
    async def connect_market(self) -> bool:
        """Open market data connection (WebSocket or REST polling)."""
        ...

    @abstractmethod
    async def connect_account(self) -> bool:
        """Open private trading/account connection."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect all exchange connections."""
        ...

    @abstractmethod
    async def get_exchange_info(self) -> ExchangeInfo:
        """Return exchange metadata (symbols, lot sizes, filters)."""
        ...

    @abstractmethod
    async def get_balance(self, asset: Optional[str] = None) -> list[BalanceEntry]:
        """Return account balances."""
        ...

    @abstractmethod
    async def get_positions(self, symbol: Optional[str] = None) -> list[PositionEntry]:
        """Return open positions."""
        ...

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        **kwargs: Any,
    ) -> OrderResult:
        """Place a new order."""
        ...

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> OrderResult:
        """Cancel an existing order."""
        ...

    @abstractmethod
    async def get_order(self, symbol: str, order_id: str) -> OrderResult:
        """Get order details."""
        ...

    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> list[OrderResult]:
        """Return open orders."""
        ...

    @abstractmethod
    async def get_ticker(self, symbol: str) -> TickerData:
        """Return latest ticker for a symbol."""
        ...

    @abstractmethod
    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        """Return order book for a symbol."""
        ...

    @abstractmethod
    async def get_candles(
        self, symbol: str, interval: str, limit: int = 100
    ) -> list[Candle]:
        """Return OHLCV candles."""
        ...

    @abstractmethod
    async def get_trades(self, symbol: str, limit: int = 100) -> list[TradeEntry]:
        """Return recent public trades."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the exchange is reachable."""
        ...

    @abstractmethod
    async def subscribe_market(
        self, symbols: list[str], channel: str, callback: Callable[[Any], None]
    ) -> bool:
        """Subscribe to market data stream."""
        ...

    @abstractmethod
    async def subscribe_account(
        self, channel: str, callback: Callable[[Any], None]
    ) -> bool:
        """Subscribe to private account stream."""
        ...

    @abstractmethod
    async def unsubscribe_market(
        self, symbols: list[str], channel: str
    ) -> bool:
        """Unsubscribe from market data stream."""
        ...

    @abstractmethod
    async def unsubscribe_account(self, channel: str) -> bool:
        """Unsubscribe from private account stream."""
        ...
