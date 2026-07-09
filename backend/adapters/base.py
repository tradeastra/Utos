"""
Base interface for all exchange adapters.

This module defines the IExchangeAdapter interface that all exchange
implementations (Binance, Bybit, OKX, etc.) must follow.
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, List
from decimal import Decimal
from datetime import datetime

from core.types import (
    OrderResult,
    BalanceEntry,
    PositionEntry,
    TradeEntry,
    TickerData,
    OrderBook,
    Candle,
    ExchangeInfo,
    ExchangeCredentials,
    ExchangeAdapterConfig,
)
from core.exceptions import ExchangeError


class IExchangeAdapter(ABC):
    """Base interface for all exchange adapters.
    
    Market data stream and trading API are managed as separate connections
    because most exchanges separate them (different endpoints, different rate limits,
    different failure modes).
    """

    @abstractmethod
    async def initialize(self, config: ExchangeAdapterConfig) -> bool:
        """Initialize the adapter with exchange configuration.
        
        This does NOT open network connections. It only loads configuration,
        exchange info, and validates credentials format.
        
        Args:
            config: Exchange adapter configuration
            
        Returns:
            True if initialization successful
            
        Raises:
            ExchangeError: If initialization fails
        """
        pass

    @abstractmethod
    async def authenticate(self, credentials: ExchangeCredentials) -> bool:
        """Authenticate with the exchange using decrypted API credentials.
        
        Performs a lightweight auth check (e.g., ping + account query).
        
        Args:
            credentials: Exchange API credentials
            
        Returns:
            True if authentication successful
            
        Raises:
            ExchangeError: If authentication fails
        """
        pass

    @abstractmethod
    async def connect_market(self) -> bool:
        """Open market data connection (WebSocket or REST polling).
        
        Returns:
            True if connection successful
            
        Raises:
            ExchangeConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def connect_account(self) -> bool:
        """Open trading/account connection (private API / WebSocket).
        
        Returns:
            True if connection successful
            
        Raises:
            ExchangeConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect all exchange connections."""
        pass

    @abstractmethod
    async def is_market_connected(self) -> bool:
        """Check if market data connection is alive.
        
        Returns:
            True if market connection is alive
        """
        pass

    @abstractmethod
    async def is_account_connected(self) -> bool:
        """Check if trading/account connection is alive.
        
        Returns:
            True if account connection is alive
        """
        pass

    # Trading Operations
    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,          # "buy" | "sell"
        order_type: str,     # "limit" | "market" | "stop_limit"
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        client_order_id: Optional[str] = None,
    ) -> OrderResult:
        """Place an order on the exchange.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            side: Order side ("buy" or "sell")
            order_type: Order type ("limit", "market", "stop_limit")
            quantity: Order quantity
            price: Order price (required for limit orders)
            stop_price: Stop price (required for stop_limit orders)
            client_order_id: Client-defined order ID
            
        Returns:
            OrderResult with exchange order ID and status
            
        Raises:
            ExchangeError: If order placement fails
            InsufficientBalanceError: If insufficient balance
            InvalidQuantity: If quantity is invalid
            InvalidPrice: If price is invalid
        """
        pass

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an existing order.
        
        Args:
            symbol: Trading symbol
            order_id: Exchange order ID
            
        Returns:
            True if cancellation successful
            
        Raises:
            ExchangeError: If cancellation fails
            OrderNotFound: If order not found
        """
        pass

    @abstractmethod
    async def modify_order(
        self,
        symbol: str,
        order_id: str,
        new_price: Optional[Decimal] = None,
        new_quantity: Optional[Decimal] = None,
    ) -> OrderResult:
        """Modify an existing order.
        
        Args:
            symbol: Trading symbol
            order_id: Exchange order ID
            new_price: New price (optional)
            new_quantity: New quantity (optional)
            
        Returns:
            OrderResult with updated order details
            
        Raises:
            ExchangeError: If modification fails
            OrderNotFound: If order not found
            OrderAlreadyFilled: If order is already filled
        """
        pass

    # Account Information
    @abstractmethod
    async def get_balance(self) -> List[BalanceEntry]:
        """Get account balances.
        
        Returns:
            List of BalanceEntry for each currency
            
        Raises:
            ExchangeError: If request fails
        """
        pass

    @abstractmethod
    async def get_positions(self) -> List[PositionEntry]:
        """Get current positions.
        
        Returns:
            List of PositionEntry for each open position
            
        Raises:
            ExchangeError: If request fails
        """
        pass

    # Order Information
    @abstractmethod
    async def get_order(self, symbol: str, order_id: str) -> OrderResult:
        """Get order details from exchange.
        
        Args:
            symbol: Trading symbol
            order_id: Exchange order ID
            
        Returns:
            OrderResult with current order state
            
        Raises:
            ExchangeError: If request fails
            OrderNotFound: If order not found
        """
        pass

    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResult]:
        """Get all open orders.
        
        Args:
            symbol: Trading symbol (optional, if None get all symbols)
            
        Returns:
            List of OrderResult for open orders
            
        Raises:
            ExchangeError: If request fails
        """
        pass

    @abstractmethod
    async def get_order_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 100,
    ) -> List[OrderResult]:
        """Get order history.
        
        Args:
            symbol: Trading symbol (optional)
            limit: Maximum number of orders to return
            
        Returns:
            List of OrderResult for historical orders
            
        Raises:
            ExchangeError: If request fails
        """
        pass

    @abstractmethod
    async def get_trade_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 100,
    ) -> List[TradeEntry]:
        """Get trade (fill) history.
        
        Args:
            symbol: Trading symbol (optional)
            limit: Maximum number of trades to return
            
        Returns:
            List of TradeEntry for historical trades
            
        Raises:
            ExchangeError: If request fails
        """
        pass

    # Market Data
    @abstractmethod
    async def get_ticker(self, symbol: str) -> TickerData:
        """Get current ticker data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            TickerData with bid, ask, last price, volume
            
        Raises:
            ExchangeError: If request fails
            SymbolNotSupported: If symbol not supported
        """
        pass

    @abstractmethod
    async def get_order_book(self, symbol: str, depth: int = 20) -> OrderBook:
        """Get order book for a symbol.
        
        Args:
            symbol: Trading symbol
            depth: Order book depth
            
        Returns:
            OrderBook with bids and asks
            
        Raises:
            ExchangeError: If request fails
            SymbolNotSupported: If symbol not supported
        """
        pass

    @abstractmethod
    async def get_candles(
        self,
        symbol: str,
        interval: str,       # "1m", "5m", "15m", "1h", "4h", "1d"
        limit: int = 100,
    ) -> List[Candle]:
        """Get historical candlestick data.
        
        Args:
            symbol: Trading symbol
            interval: Candle interval
            limit: Maximum number of candles to return
            
        Returns:
            List of Candle with OHLCV data
            
        Raises:
            ExchangeError: If request fails
            SymbolNotSupported: If symbol not supported
        """
        pass

    # Market Data Streaming
    @abstractmethod
    async def subscribe_market(
        self,
        symbol: str,
        channel: str,        # "ticker" | "orderbook" | "candle" | "trade"
        callback: Callable,
    ) -> str:
        """Subscribe to market data stream.
        
        Args:
            symbol: Trading symbol
            channel: Market data channel
            callback: Callback function for data updates
            
        Returns:
            Subscription ID for unsubscribing
            
        Raises:
            ExchangeError: If subscription fails
            SymbolNotSupported: If symbol not supported
        """
        pass

    @abstractmethod
    async def unsubscribe_market(self, subscription_id: str) -> None:
        """Unsubscribe from market data stream.
        
        Args:
            subscription_id: Subscription ID returned by subscribe_market
            
        Raises:
            ExchangeError: If unsubscription fails
        """
        pass

    # Exchange Information
    @abstractmethod
    async def get_exchange_info(self) -> ExchangeInfo:
        """Get exchange metadata (symbols, limits, fees).
        
        Returns:
            ExchangeInfo with supported symbols and rate limits
            
        Raises:
            ExchangeError: If request fails
        """
        pass

    # Utility Methods
    @property
    @abstractmethod
    def exchange_name(self) -> str:
        """Get the exchange name."""
        pass

    @property
    @abstractmethod
    def is_testnet(self) -> bool:
        """Check if using testnet."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if exchange adapter is healthy.
        
        Returns:
            True if adapter is healthy
        """
        pass
