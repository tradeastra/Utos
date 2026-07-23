"""Bybit V5 adapter.

Implements IExchangeAdapter using the exchange-agnostic infrastructure from
Sprint 3 (HttpClient, WebSocketManager, RateLimiter, RetryPolicy).  All
Bybit-specific protocol logic (URLs, signatures, message routing, error
codes) lives in this file.
"""

import asyncio
import contextlib
import hashlib
import hmac
import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
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
from core.exceptions import (
    AuthenticationError,
    ExchangeConnectionError,
    ExchangeError,
    ExchangeRateLimitError,
    InsufficientBalanceError,
    OrderNotFound,
    SymbolNotSupported,
)
from core.logging import get_logger

from exchanges.adapter import IExchangeAdapter
from exchanges.credential_manager import CredentialManager
from exchanges.factory import ExchangeFactory
from exchanges.http_client import HttpClient
from exchanges.rate_limiter import RateLimitConfig, RateLimiter
from exchanges.retry import RetryPolicy
from exchanges.websocket_manager import WebSocketManager

logger = get_logger(__name__)


class BybitAuthenticator:
    """HMAC-SHA256 request signer for Bybit V5 API."""

    def __init__(self, api_key: str = "", api_secret: str = "") -> None:
        self.api_key = api_key
        self.api_secret = api_secret

    def set_credentials(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret

    def timestamp(self) -> str:
        return str(int(time.time() * 1000))

    def sign(self, timestamp: str, recv_window: str, param_str: str) -> str:
        payload = f"{timestamp}{self.api_key}{recv_window}{param_str}"
        return hmac.new(
            self.api_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def auth_headers(self, signature: str, timestamp: str, recv_window: str) -> dict[str, str]:
        return {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-SIGN": signature,
            "X-BAPI-SIGN-TYPE": "2",
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": recv_window,
        }


class BybitAdapter(IExchangeAdapter):
    """Concrete Bybit V5 adapter implementing IExchangeAdapter."""

    name = "bybit"

    REST_MAINNET = "https://api.bybit.com"
    REST_TESTNET = "https://api-testnet.bybit.com"
    WS_MAINNET = "wss://stream.bybit.com/v5/public/spot"
    WS_TESTNET = "wss://stream-testnet.bybit.com/v5/public/spot"
    WS_PRIVATE_MAINNET = "wss://stream.bybit.com/v5/private"
    WS_PRIVATE_TESTNET = "wss://stream-testnet.bybit.com/v5/private"

    def __init__(
        self,
        http_client: HttpClient | None = None,
        ws_manager: WebSocketManager | None = None,
        ws_account_manager: WebSocketManager | None = None,
        credential_manager: CredentialManager | None = None,
        authenticator: BybitAuthenticator | None = None,
    ) -> None:
        self.http = http_client
        self.ws = ws_manager
        self.ws_account = ws_account_manager
        self.credential_manager = credential_manager
        self.authenticator = authenticator or BybitAuthenticator()

        self.config: ExchangeAdapterConfig | None = None
        self.credentials: ExchangeCredentials | None = None
        self.rest_url: str = ""
        self.ws_url: str = ""
        self.ws_private_url: str = ""
        self.recv_window: str = "5000"
        self._exchange_info: dict[str, Any] | None = None

        self._ticker_callbacks: dict[str, Callable[[Any], None]] = {}
        self._orderbook_callbacks: dict[str, Callable[[Any], None]] = {}
        self._user_data_callback: Callable[[Any], None] | None = None

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------
    async def initialize(self, config: ExchangeAdapterConfig) -> bool:
        self.config = config
        self.name = config.exchange_name or self.name
        self.rest_url = (
            self.REST_TESTNET
            if config.is_testnet
            else config.rest_url or self.REST_MAINNET
        ).rstrip("/")
        self.ws_url = (
            self.WS_TESTNET
            if config.is_testnet
            else config.market_stream_url or self.WS_MAINNET
        ).rstrip("/")
        self.ws_private_url = (
            self.WS_PRIVATE_TESTNET
            if config.is_testnet
            else config.account_stream_url or self.WS_PRIVATE_MAINNET
        ).rstrip("/")
        self.recv_window = str(getattr(config, "recv_window", 5000))

        rate_limiter = RateLimiter()
        rate_limiter.configure(
            "rest", RateLimitConfig(max_tokens=120.0, refill_rate=20.0)
        )
        rate_limiter.configure(
            "websocket", RateLimitConfig(max_tokens=5.0, refill_rate=5.0)
        )

        retry_policy = RetryPolicy(
            max_retries=3,
            base_delay=0.5,
            exponential_base=2.0,
            retryable_status_codes={408, 429, 500, 502, 503, 504},
        )

        if self.http is None:
            self.http = HttpClient(
                base_url=self.rest_url,
                timeout=config.request_timeout,
                retry_policy=retry_policy,
                rate_limiter=rate_limiter,
                exchange_name=self.name,
            )
        else:
            self.http.base_url = self.rest_url
            self.http.exchange_name = self.name
            if self.http.retry_policy is None:
                self.http.retry_policy = retry_policy
            if self.http.rate_limiter is None:
                self.http.rate_limiter = rate_limiter

        ws_retry_policy = RetryPolicy(max_retries=5, base_delay=1.0)
        if self.ws is None:
            self.ws = WebSocketManager(
                retry_policy=ws_retry_policy, rate_limiter=rate_limiter
            )
        if self.ws_account is None:
            self.ws_account = WebSocketManager(
                retry_policy=ws_retry_policy, rate_limiter=rate_limiter
            )

        if self.credential_manager is None:
            self.credential_manager = CredentialManager()

        self.ws.register_callback(self._dispatch)
        self.ws_account.register_callback(self._dispatch)
        return True

    async def authenticate(self, credentials: ExchangeCredentials) -> bool:
        self.credentials = credentials
        self.authenticator.set_credentials(credentials.api_key, credentials.api_secret)
        response = await self._signed_get("/v5/account/wallet-balance", {"accountType": "UNIFIED"})
        self._raise_for_status(response)
        return True

    async def connect_market(self) -> bool:
        return await self.ws.connect(self.ws_url)

    async def connect_account(self) -> bool:
        return await self.ws_account.connect(self.ws_private_url)

    async def disconnect(self) -> None:
        self._ticker_callbacks.clear()
        self._orderbook_callbacks.clear()
        self._user_data_callback = None

        if self.ws is not None:
            await self.ws.disconnect()
        if self.ws_account is not None:
            await self.ws_account.disconnect()
        if self.http is not None:
            await self.http.close()

    async def health_check(self) -> bool:
        try:
            response = await self.http.get("/v5/market/time")
            self._raise_for_status(response)
            return True
        except Exception as exc:
            logger.warning(f"Bybit health check failed: {exc}")
            return False

    # -------------------------------------------------------------------------
    # Account & Symbol
    # -------------------------------------------------------------------------
    async def get_account(self) -> dict[str, Any]:
        response = await self._signed_get("/v5/account/wallet-balance", {"accountType": "UNIFIED"})
        return self._parse_json(response)

    async def get_balance(self, asset: str | None = None) -> list[BalanceEntry]:
        account = await self.get_account()
        balances: list[BalanceEntry] = []
        for acct in account.get("result", {}).get("list", []):
            for coin in acct.get("coin", []):
                if asset and coin.get("coin") != asset.upper():
                    continue
                free = Decimal(coin.get("availableToWithdraw", "0"))
                locked = Decimal(coin.get("locked", "0"))
                total = Decimal(coin.get("walletBalance", "0"))
                balances.append(
                    BalanceEntry(
                        currency=coin.get("coin", ""),
                        available=free,
                        locked=locked,
                        total=total,
                    )
                )
        return balances

    async def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        info = await self._load_exchange_info()
        upper = symbol.upper()
        for sym in info.get("result", {}).get("list", []):
            if sym.get("symbol") == upper:
                return sym
        raise SymbolNotSupported(symbol, self.name)

    async def get_exchange_info(self) -> ExchangeInfo:
        info = await self._load_exchange_info()
        symbols = [s["symbol"] for s in info.get("result", {}).get("list", [])]
        return ExchangeInfo(
            name=self.name,
            supported_symbols=symbols,
            rate_limits={},
            fee_structure={},
            server_time=datetime.now(UTC),
        )

    async def get_positions(self, symbol: str | None = None) -> list[PositionEntry]:
        params: dict[str, Any] = {"category": "linear", "settleCoin": "USDT"}
        if symbol:
            params["symbol"] = symbol.upper()
        response = await self._signed_get("/v5/position/list", params)
        self._raise_for_status(response)
        data = self._parse_json(response)
        positions: list[PositionEntry] = []
        for pos in data.get("result", {}).get("list", []):
            positions.append(
                PositionEntry(
                    symbol=pos.get("symbol", ""),
                    side=pos.get("side", "").lower(),
                    quantity=Decimal(pos.get("size", "0")),
                    entry_price=Decimal(pos.get("avgPrice", "0")),
                    unrealized_pnl=Decimal(pos.get("unrealisedPnl", "0")),
                )
            )
        return positions

    # -------------------------------------------------------------------------
    # Market data
    # -------------------------------------------------------------------------
    async def get_ticker(self, symbol: str) -> TickerData:
        upper = symbol.upper()
        data = self._parse_json(
            await self.http.get(
                "/v5/market/tickers", params={"category": "spot", "symbol": upper}
            )
        )
        tickers = data.get("result", {}).get("list", [])
        if not tickers:
            raise SymbolNotSupported(symbol, self.name)
        t = tickers[0]
        return TickerData(
            symbol=upper,
            bid=Decimal(t.get("bid1Price", "0")),
            ask=Decimal(t.get("ask1Price", "0")),
            last=Decimal(t.get("lastPrice", "0")),
            volume=Decimal(t.get("volume24h", "0")),
            timestamp=datetime.now(UTC),
        )

    async def get_order_book(self, symbol: str, limit: int = 50) -> OrderBook:
        data = self._parse_json(
            await self.http.get(
                "/v5/market/orderbook",
                params={"category": "spot", "symbol": symbol.upper(), "limit": limit},
            )
        )
        result = data.get("result", {})
        return OrderBook(
            symbol=symbol.upper(),
            bids=[(Decimal(b[0]), Decimal(b[1])) for b in result.get("bids", [])],
            asks=[(Decimal(a[0]), Decimal(a[1])) for a in result.get("asks", [])],
            timestamp=datetime.now(UTC),
        )

    async def get_candles(
        self, symbol: str, interval: str, limit: int = 200
    ) -> list[Candle]:
        interval_map = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1d": "D"}
        bybit_interval = interval_map.get(interval, interval)
        data = self._parse_json(
            await self.http.get(
                "/v5/market/kline",
                params={
                    "category": "spot",
                    "symbol": symbol.upper(),
                    "interval": bybit_interval,
                    "limit": limit,
                },
            )
        )
        candles: list[Candle] = []
        for row in data.get("result", {}).get("list", []):
            candles.append(
                Candle(
                    symbol=symbol.upper(),
                    interval=interval,
                    open=Decimal(row[1]),
                    high=Decimal(row[2]),
                    low=Decimal(row[3]),
                    close=Decimal(row[4]),
                    volume=Decimal(row[5]),
                    timestamp=datetime.fromtimestamp(int(row[0]) / 1000, tz=UTC),
                )
            )
        return candles

    async def get_trades(self, symbol: str, limit: int = 100) -> list[TradeEntry]:
        data = self._parse_json(
            await self.http.get(
                "/v5/market/recent-trade",
                params={"category": "spot", "symbol": symbol.upper(), "limit": limit},
            )
        )
        trades: list[TradeEntry] = []
        for row in data.get("result", {}).get("list", []):
            trades.append(
                TradeEntry(
                    trade_id=str(row.get("execId", "")),
                    order_id="",
                    symbol=symbol.upper(),
                    side=row.get("side", "").lower(),
                    quantity=Decimal(row.get("size", "0")),
                    price=Decimal(row.get("price", "0")),
                    fee=Decimal("0"),
                    fee_currency="USDT",
                    timestamp=datetime.fromtimestamp(int(row.get("time", "0")) / 1000, tz=UTC),
                )
            )
        return trades

    # -------------------------------------------------------------------------
    # Orders
    # -------------------------------------------------------------------------
    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Decimal | None = None,
        **kwargs: Any,
    ) -> OrderResult:
        params: dict[str, Any] = {
            "category": "spot",
            "symbol": symbol.upper(),
            "side": side.capitalize(),
            "qty": str(quantity),
            "orderType": order_type.capitalize(),
        }
        if price is not None:
            params["price"] = str(price)
        if kwargs.get("client_order_id"):
            params["orderLinkId"] = kwargs["client_order_id"]
        response = await self._signed_post("/v5/order/create", params)
        return self._order_result_from_response(self._parse_json(response), symbol.upper(), side, order_type, quantity, price)

    async def cancel_order(self, symbol: str, order_id: str) -> OrderResult:
        params = {"category": "spot", "symbol": symbol.upper(), "orderId": order_id}
        response = await self._signed_post("/v5/order/cancel", params)
        return self._order_result_from_response(self._parse_json(response), symbol.upper(), "", "", Decimal("0"), None)

    async def cancel_all(self, symbol: str | None = None) -> list[OrderResult]:
        params: dict[str, Any] = {"category": "spot"}
        if symbol:
            params["symbol"] = symbol.upper()
        response = await self._signed_post("/v5/order/cancel-all", params)
        self._raise_for_status(response)
        return []

    async def get_order(self, symbol: str, order_id: str) -> OrderResult:
        params = {"category": "spot", "symbol": symbol.upper(), "orderId": order_id}
        response = await self._signed_get("/v5/order/realtime", params)
        data = self._parse_json(response)
        orders = data.get("result", {}).get("list", [])
        if not orders:
            raise OrderNotFound(order_id)
        return self._order_result_from_list(orders[0])

    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        params: dict[str, Any] = {"category": "spot"}
        if symbol:
            params["symbol"] = symbol.upper()
        response = await self._signed_get("/v5/order/realtime", params)
        data = self._parse_json(response)
        return [
            self._order_result_from_list(o)
            for o in data.get("result", {}).get("list", [])
        ]

    # -------------------------------------------------------------------------
    # WebSocket subscriptions
    # -------------------------------------------------------------------------
    async def subscribe_market(
        self, symbols: list[str], channel: str, callback: Callable[[Any], None]
    ) -> bool:
        if not self.ws.is_connected:
            await self.connect_market()

        args: list[str] = []
        for symbol in symbols:
            upper = symbol.upper()
            if channel == "ticker":
                args.append(f"tickers.{upper}")
                self._ticker_callbacks[upper] = callback
            elif channel == "orderbook":
                args.append(f"orderbook.50.{upper}")
                self._orderbook_callbacks[upper] = callback
            else:
                args.append(f"{channel}.{upper}")

        msg = {"op": "subscribe", "args": args}
        await self.ws.subscribe(json.dumps(msg))
        return True

    async def subscribe_account(
        self, channel: str, callback: Callable[[Any], None]
    ) -> bool:
        if not self.ws_account.is_connected:
            await self.connect_account()
        self._user_data_callback = callback
        return True

    async def unsubscribe_market(self, symbols: list[str], channel: str) -> bool:
        args: list[str] = []
        for symbol in symbols:
            upper = symbol.upper()
            if channel == "ticker":
                self._ticker_callbacks.pop(upper, None)
                args.append(f"tickers.{upper}")
            elif channel == "orderbook":
                self._orderbook_callbacks.pop(upper, None)
                args.append(f"orderbook.50.{upper}")
            else:
                args.append(f"{channel}.{upper}")
        msg = {"op": "unsubscribe", "args": args}
        await self.ws.unsubscribe(json.dumps(msg))
        return True

    async def unsubscribe_account(self, channel: str) -> bool:
        self._user_data_callback = None
        return True

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------
    def _ensure_authenticated(self) -> None:
        if not self.authenticator.api_key:
            raise AuthenticationError("Bybit adapter is not authenticated")

    async def _signed_request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        self._ensure_authenticated()
        params = params or {}
        ts = self.authenticator.timestamp()
        recv_window = self.recv_window

        if method == "GET":
            param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        else:
            param_str = json.dumps(params, separators=(",", ":"), sort_keys=True)

        signature = self.authenticator.sign(ts, recv_window, param_str)
        headers = self.authenticator.auth_headers(signature, ts, recv_window)

        if method == "GET":
            response = await self.http.get(path, params=params, headers=headers)
        elif method == "POST":
            headers["Content-Type"] = "application/json"
            response = await self.http.post(path, json=params, headers=headers)
        else:
            raise ValueError(f"Unsupported signed method: {method}")

        self._raise_for_status(response)
        return response

    async def _signed_get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> httpx.Response:
        return await self._signed_request("GET", path, params or {})

    async def _signed_post(self, path: str, params: dict[str, Any]) -> httpx.Response:
        return await self._signed_request("POST", path, params)

    async def _load_exchange_info(self) -> dict[str, Any]:
        if self._exchange_info is None:
            response = await self.http.get("/v5/market/instruments-info", params={"category": "spot"})
            self._exchange_info = self._parse_json(response)
        return self._exchange_info

    def _parse_json(self, response: httpx.Response) -> Any:
        self._raise_for_status(response)
        try:
            return response.json()
        except Exception as exc:
            raise ExchangeError("Invalid JSON response from Bybit", self.name) from exc

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        try:
            body = response.json()
        except Exception:
            body = {}

        ret_code = body.get("retCode", 0)
        ret_msg = body.get("retMsg", "")
        status = response.status_code

        if status == 429 or ret_code == 10001:
            raise ExchangeRateLimitError(f"Bybit rate limit: {ret_msg}", self.name)
        if ret_code in (10003, 10004):
            raise AuthenticationError(f"Bybit auth error: {ret_msg}")
        if ret_code == 110001:
            raise SymbolNotSupported("", self.name)
        if ret_code == 110017:
            raise InsufficientBalanceError(f"Bybit insufficient balance: {ret_msg}")
        if ret_code == 20001:
            raise OrderNotFound(str(ret_msg))
        if status >= 500:
            raise ExchangeConnectionError(f"Bybit server error {status}: {ret_msg}", self.name)

        raise ExchangeError(f"Bybit error {ret_code}: {ret_msg}", self.name)

    def _order_result_from_response(
        self,
        data: dict[str, Any],
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Decimal | None,
    ) -> OrderResult:
        result = data.get("result", {})
        return OrderResult(
            order_id=str(result.get("orderLinkId", "")),
            exchange_order_id=str(result.get("orderId", "")),
            symbol=symbol,
            side=side.lower(),
            order_type=order_type.lower(),
            quantity=quantity,
            price=price,
            filled_quantity=Decimal("0"),
            average_fill_price=None,
            status="open",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            error_message=None,
        )

    def _order_result_from_list(self, data: dict[str, Any]) -> OrderResult:
        return OrderResult(
            order_id=str(data.get("orderLinkId", "")),
            exchange_order_id=str(data.get("orderId", "")),
            symbol=data.get("symbol", ""),
            side=data.get("side", "").lower(),
            order_type=data.get("orderType", "").lower(),
            quantity=Decimal(data.get("qty", "0")),
            price=Decimal(data.get("price", "0")) or None,
            filled_quantity=Decimal(data.get("cumExecQty", "0")),
            average_fill_price=Decimal(data.get("avgPrice", "0")) or None,
            status=self._map_order_status(data.get("orderStatus", "")),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            error_message=None,
        )

    def _map_order_status(self, status: str) -> str:
        mapping = {
            "New": "open",
            "PartiallyFilled": "partially_filled",
            "Filled": "filled",
            "Cancelled": "cancelled",
            "Rejected": "rejected",
            "Untriggered": "pending",
            "Triggered": "open",
            "Deactivated": "cancelled",
        }
        return mapping.get(status, status.lower())

    def _dispatch(self, message: Any) -> None:
        if not isinstance(message, str):
            return
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return
        if not isinstance(data, dict):
            return

        topic = data.get("topic", "")
        msg_type = data.get("type", "")

        if topic.startswith("tickers."):
            symbol = topic.replace("tickers.", "").upper()
            cb = self._ticker_callbacks.get(symbol)
            if cb:
                cb(data)
        elif topic.startswith("orderbook."):
            parts = topic.split(".")
            if len(parts) >= 3:
                symbol = parts[-1].upper()
                cb = self._orderbook_callbacks.get(symbol)
                if cb:
                    cb(data)
        elif msg_type == "snapshot":
            if self._user_data_callback:
                self._user_data_callback(data)
        else:
            logger.debug(f"Unhandled Bybit WebSocket message: {data}")


# Register adapter automatically when module is imported.
ExchangeFactory.register("bybit", BybitAdapter)
