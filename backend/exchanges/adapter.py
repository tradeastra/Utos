"""
Abstract exchange adapter interface — Sprint 3 infrastructure layer.

All concrete exchange adapters (Binance, Hyperliquid, Bybit, OKX, MEXC, etc.)
must implement this interface in later sprints.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from core.domain_types import (
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

    async def connect(self) -> bool:
        """Open both market and account connections."""
        await self.connect_market()
        await self.connect_account()
        return True

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
    async def get_balance(self, asset: str | None = None) -> list[BalanceEntry]:
        """Return account balances."""
        ...

    @abstractmethod
    async def get_account(self) -> Any:
        """Return full account information including balances and permissions."""
        ...

    @abstractmethod
    async def get_symbol_info(self, symbol: str) -> Any:
        """Return metadata for a single symbol (filters, lot size, tick size, etc.)."""
        ...

    @abstractmethod
    async def get_positions(self, symbol: str | None = None) -> list[PositionEntry]:
        """Return open positions."""
        ...

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Decimal | None = None,
        **kwargs: Any,
    ) -> OrderResult:
        """Place a new order."""
        ...

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> OrderResult:
        """Cancel an existing order."""
        ...

    @abstractmethod
    async def cancel_all(self, symbol: str | None = None) -> list[OrderResult]:
        """Cancel all open orders for the given symbol or account."""
        ...

    @abstractmethod
    async def get_order(self, symbol: str, order_id: str) -> OrderResult:
        """Get order details."""
        ...

    @abstractmethod
    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        """Return open orders."""
        ...

    @abstractmethod
    async def get_ticker(self, symbol: str) -> TickerData:
        """Return latest ticker for a symbol."""
        ...

    async def get_tickers(self) -> list[TickerData]:
        """Return tickers for all symbols, sorted by volume descending.

        Subclasses should override this with an efficient batch API call.
        The default implementation raises NotImplementedError.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support get_tickers"
        )

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

    async def subscribe_ticker(
        self, symbol: str, callback: Callable[[Any], None]
    ) -> bool:
        """Convenience wrapper for ticker market subscription."""
        return await self.subscribe_market([symbol], "ticker", callback)

    async def subscribe_orderbook(
        self, symbol: str, callback: Callable[[Any], None]
    ) -> bool:
        """Convenience wrapper for orderbook market subscription."""
        return await self.subscribe_market([symbol], "orderbook", callback)

    @abstractmethod
    async def subscribe_account(
        self, channel: str, callback: Callable[[Any], None]
    ) -> bool:
        """Subscribe to private account stream."""
        ...

    async def subscribe_user_data(self, callback: Callable[[Any], None]) -> bool:
        """Convenience wrapper for user account stream subscription."""
        return await self.subscribe_account("user", callback)

    @abstractmethod
    async def unsubscribe_market(self, symbols: list[str], channel: str) -> bool:
        """Unsubscribe from market data stream."""
        ...

    async def unsubscribe_ticker(self, symbol: str) -> bool:
        """Convenience wrapper for ticker unsubscription."""
        return await self.unsubscribe_market([symbol], "ticker")

    async def unsubscribe_orderbook(self, symbol: str) -> bool:
        """Convenience wrapper for orderbook unsubscription."""
        return await self.unsubscribe_market([symbol], "orderbook")

    @abstractmethod
    async def unsubscribe_account(self, channel: str) -> bool:
        """Unsubscribe from private account stream."""
        ...

    async def unsubscribe_user_data(self) -> bool:
        """Convenience wrapper for user account stream unsubscription."""
        return await self.unsubscribe_account("user")
