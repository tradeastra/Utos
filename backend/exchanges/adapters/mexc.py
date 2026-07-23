"""MEXC Spot adapter.

Implements IExchangeAdapter using the exchange-agnostic infrastructure from
Sprint 3.  MEXC uses HMAC-SHA256 query-string signing similar to Binance.
"""

import hashlib
import hmac
import json
import time
import urllib.parse
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


class MEXCAuthenticator:
    """HMAC-SHA256 request signer for MEXC."""

    def __init__(self, api_key: str = "", api_secret: str = "") -> None:
        self.api_key = api_key
        self.api_secret = api_secret

    def set_credentials(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret

    def timestamp(self) -> int:
        return int(time.time() * 1000)

    def sign(self, query_string: str) -> str:
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def auth_headers(self) -> dict[str, str]:
        return {"X-MEXC-APIKEY": self.api_key}


class MEXCAdapter(IExchangeAdapter):
    """Concrete MEXC Spot adapter implementing IExchangeAdapter."""

    name = "mexc"

    REST_MAINNET = "https://api.mexc.com"
    REST_TESTNET = "https://sandbox.mexc.com"
    WS_MAINNET = "wss://wbs-api.mexc.com/ws"
    WS_TESTNET = "wss://wbs-api.mexc.com/ws"

    def __init__(
        self,
        http_client: HttpClient | None = None,
        ws_manager: WebSocketManager | None = None,
        ws_account_manager: WebSocketManager | None = None,
        credential_manager: CredentialManager | None = None,
        authenticator: MEXCAuthenticator | None = None,
    ) -> None:
        self.http = http_client
        self.ws = ws_manager
        self.ws_account = ws_account_manager
        self.credential_manager = credential_manager
        self.authenticator = authenticator or MEXCAuthenticator()

        self.config: ExchangeAdapterConfig | None = None
        self.credentials: ExchangeCredentials | None = None
        self.rest_url: str = ""
        self.ws_url: str = ""
        self.recv_window: int = 5000
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
        self.recv_window = getattr(config, "recv_window", 5000)

        rate_limiter = RateLimiter()
        rate_limiter.configure(
            "rest", RateLimitConfig(max_tokens=100.0, refill_rate=15.0)
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
        response = await self._signed_get("/api/v3/account")
        self._raise_for_status(response)
        return True

    async def connect_market(self) -> bool:
        return await self.ws.connect(self.ws_url)

    async def connect_account(self) -> bool:
        return await self.ws_account.connect(self.ws_url)

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
            response = await self.http.get("/api/v3/ping")
            self._raise_for_status(response)
            return True
        except Exception as exc:
            logger.warning(f"MEXC health check failed: {exc}")
            return False

    # -------------------------------------------------------------------------
    # Account & Symbol
    # -------------------------------------------------------------------------
    async def get_account(self) -> dict[str, Any]:
        response = await self._signed_get("/api/v3/account")
        return self._parse_json(response)

    async def get_balance(self, asset: str | None = None) -> list[BalanceEntry]:
        account = await self.get_account()
        balances: list[BalanceEntry] = []
        for item in account.get("balances", []):
            if asset and item["asset"] != asset.upper():
                continue
            free = Decimal(item.get("free", "0"))
            locked = Decimal(item.get("locked", "0"))
            balances.append(
                BalanceEntry(
                    currency=item.get("asset", ""),
                    available=free,
                    locked=locked,
                    total=free + locked,
                )
            )
        return balances

    async def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        info = await self._load_exchange_info()
        upper = symbol.upper()
        for sym in info.get("symbols", []):
            if sym.get("symbol") == upper:
                return sym
        raise SymbolNotSupported(symbol, self.name)

    async def get_exchange_info(self) -> ExchangeInfo:
        info = await self._load_exchange_info()
        return ExchangeInfo(
            name=self.name,
            supported_symbols=[s["symbol"] for s in info.get("symbols", [])],
            rate_limits={},
            fee_structure={},
            server_time=datetime.now(UTC),
        )

    async def get_positions(self, symbol: str | None = None) -> list[PositionEntry]:
        return []

    # -------------------------------------------------------------------------
    # Market data
    # -------------------------------------------------------------------------
    async def get_ticker(self, symbol: str) -> TickerData:
        upper = symbol.upper()
        data = self._parse_json(
            await self.http.get("/api/v3/ticker/bookTicker", params={"symbol": upper})
        )
        stats = self._parse_json(
            await self.http.get("/api/v3/ticker/24hr", params={"symbol": upper})
        )
        return TickerData(
            symbol=upper,
            bid=Decimal(data.get("bidPrice", "0")),
            ask=Decimal(data.get("askPrice", "0")),
            last=Decimal(stats.get("lastPrice", "0")),
            volume=Decimal(stats.get("volume", "0")),
            timestamp=datetime.now(UTC),
        )

    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        data = self._parse_json(
            await self.http.get(
                "/api/v3/depth", params={"symbol": symbol.upper(), "limit": limit}
            )
        )
        return OrderBook(
            symbol=symbol.upper(),
            bids=[(Decimal(b[0]), Decimal(b[1])) for b in data.get("bids", [])],
            asks=[(Decimal(a[0]), Decimal(a[1])) for a in data.get("asks", [])],
            timestamp=datetime.now(UTC),
        )

    async def get_candles(
        self, symbol: str, interval: str, limit: int = 500
    ) -> list[Candle]:
        interval_map = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "60m", "4h": "4h", "1d": "1d"}
        mexc_interval = interval_map.get(interval, interval)
        data = self._parse_json(
            await self.http.get(
                "/api/v3/klines",
                params={"symbol": symbol.upper(), "interval": mexc_interval, "limit": limit},
            )
        )
        candles: list[Candle] = []
        for row in data:
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
                "/api/v3/trades", params={"symbol": symbol.upper(), "limit": limit}
            )
        )
        trades: list[TradeEntry] = []
        for row in data:
            trades.append(
                TradeEntry(
                    trade_id=str(row.get("id", "")),
                    order_id="",
                    symbol=symbol.upper(),
                    side="sell" if row.get("isBuyerMaker") else "buy",
                    quantity=Decimal(row.get("qty", "0")),
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
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": str(quantity),
        }
        if price is not None:
            params["price"] = str(price)
            params["timeInForce"] = kwargs.get("time_in_force", "GTC")
        if kwargs.get("client_order_id"):
            params["newClientOrderId"] = kwargs["client_order_id"]
        response = await self._signed_post("/api/v3/order", params)
        return self._order_result_from_response(self._parse_json(response))

    async def cancel_order(self, symbol: str, order_id: str) -> OrderResult:
        params = {"symbol": symbol.upper(), "orderId": order_id}
        response = await self._signed_delete("/api/v3/order", params)
        return self._order_result_from_response(self._parse_json(response))

    async def cancel_all(self, symbol: str | None = None) -> list[OrderResult]:
        if symbol:
            params = {"symbol": symbol.upper()}
            response = await self._signed_delete("/api/v3/openOrders", params)
            self._raise_for_status(response)
        else:
            results: list[OrderResult] = []
            for order in await self.get_open_orders():
                if order.symbol:
                    results.append(await self.cancel_order(order.symbol, order.exchange_order_id))
            return results
        return []

    async def get_order(self, symbol: str, order_id: str) -> OrderResult:
        params = {"symbol": symbol.upper(), "orderId": order_id}
        response = await self._signed_get("/api/v3/order", params)
        return self._order_result_from_response(self._parse_json(response))

    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        params = {"symbol": symbol.upper()} if symbol else {}
        response = await self._signed_get("/api/v3/openOrders", params)
        data = self._parse_json(response)
        return [self._order_result_from_response(o) for o in (data or [])]

    # -------------------------------------------------------------------------
    # WebSocket subscriptions
    # -------------------------------------------------------------------------
    async def subscribe_market(
        self, symbols: list[str], channel: str, callback: Callable[[Any], None]
    ) -> bool:
        if not self.ws.is_connected:
            await self.connect_market()

        for symbol in symbols:
            upper = symbol.upper()
            if channel == "ticker":
                self._ticker_callbacks[upper] = callback
                sub_msg = {"method": "SUBSCRIPTION", "params": [f"spot@ticker@{upper}"], "id": hash(upper) % 100000}
            elif channel == "orderbook":
                self._orderbook_callbacks[upper] = callback
                sub_msg = {"method": "SUBSCRIPTION", "params": [f"spot@depth@{upper}"], "id": hash(upper) % 100000}
            else:
                sub_msg = {"method": "SUBSCRIPTION", "params": [f"spot@{channel}@{upper}"], "id": hash(upper) % 100000}
            await self.ws.subscribe(json.dumps(sub_msg))
        return True

    async def subscribe_account(
        self, channel: str, callback: Callable[[Any], None]
    ) -> bool:
        if not self.ws_account.is_connected:
            await self.connect_account()
        self._user_data_callback = callback
        return True

    async def unsubscribe_market(self, symbols: list[str], channel: str) -> bool:
        for symbol in symbols:
            upper = symbol.upper()
            if channel == "ticker":
                self._ticker_callbacks.pop(upper, None)
                unsub_msg = {"method": "UNSUBSCRIPTION", "params": [f"spot@ticker@{upper}"], "id": hash(upper) % 100000}
            elif channel == "orderbook":
                self._orderbook_callbacks.pop(upper, None)
                unsub_msg = {"method": "UNSUBSCRIPTION", "params": [f"spot@depth@{upper}"], "id": hash(upper) % 100000}
            else:
                unsub_msg = {"method": "UNSUBSCRIPTION", "params": [f"spot@{channel}@{upper}"], "id": hash(upper) % 100000}
            await self.ws.unsubscribe(json.dumps(unsub_msg))
        return True

    async def unsubscribe_account(self, channel: str) -> bool:
        self._user_data_callback = None
        return True

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------
    def _ensure_authenticated(self) -> None:
        if not self.authenticator.api_key:
            raise AuthenticationError("MEXC adapter is not authenticated")

    def _signed_params(self, params: dict[str, Any]) -> dict[str, Any]:
        self._ensure_authenticated()
        params = dict(params)
        params["timestamp"] = self.authenticator.timestamp()
        params["recvWindow"] = params.get("recvWindow", self.recv_window)
        to_sign = urllib.parse.urlencode(sorted(params.items()), doseq=True)
        params["signature"] = self.authenticator.sign(to_sign)
        return params

    async def _signed_request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        params = params or {}
        signed = self._signed_params(dict(params))
        headers = self.authenticator.auth_headers()

        if method == "GET":
            response = await self.http.get(path, params=signed, headers=headers)
        elif method == "POST":
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            body = urllib.parse.urlencode(sorted(signed.items()), doseq=True)
            response = await self.http.post(path, content=body, headers=headers)
        elif method == "DELETE":
            response = await self.http.delete(path, params=signed, headers=headers)
        else:
            raise ValueError(f"Unsupported signed method: {method}")

        self._raise_for_status(response)
        return response

    async def _signed_get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> httpx.Response:
        return await self._signed_request("GET", path, params)

    async def _signed_post(self, path: str, params: dict[str, Any]) -> httpx.Response:
        return await self._signed_request("POST", path, params)

    async def _signed_delete(self, path: str, params: dict[str, Any]) -> httpx.Response:
        return await self._signed_request("DELETE", path, params)

    async def _load_exchange_info(self) -> dict[str, Any]:
        if self._exchange_info is None:
            response = await self.http.get("/api/v3/exchangeInfo")
            self._exchange_info = self._parse_json(response)
        return self._exchange_info

    def _parse_json(self, response: httpx.Response) -> Any:
        self._raise_for_status(response)
        try:
            return response.json()
        except Exception as exc:
            raise ExchangeError("Invalid JSON response from MEXC", self.name) from exc

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        try:
            body = response.json()
        except Exception:
            body = {}

        code = body.get("code")
        msg = body.get("msg", "")
        status = response.status_code

        if status == 429 or code == 429:
            raise ExchangeRateLimitError(f"MEXC rate limit: {msg}", self.name)
        if code in (401, 403):
            raise AuthenticationError(f"MEXC auth error: {msg}")
        if code == 1120 or code == 1121:
            raise SymbolNotSupported("", self.name)
        if code == 2010:
            raise InsufficientBalanceError(f"MEXC insufficient balance: {msg}")
        if code == 2013:
            raise OrderNotFound(str(msg))
        if status >= 500:
            raise ExchangeConnectionError(f"MEXC server error {status}: {msg}", self.name)

        raise ExchangeError(f"MEXC HTTP {status}: {msg}", self.name)

    def _order_result_from_response(self, data: dict[str, Any]) -> OrderResult:
        filled = Decimal(data.get("executedQty", "0"))
        quote = Decimal(data.get("cummulativeQuoteQty", "0"))
        avg_price = quote / filled if filled > 0 else None
        return OrderResult(
            order_id=str(data.get("clientOrderId", "")),
            exchange_order_id=str(data.get("orderId", "")),
            symbol=data.get("symbol", ""),
            side=data.get("side", "").lower(),
            order_type=data.get("type", "").lower(),
            quantity=Decimal(data.get("origQty", "0")),
            price=Decimal(data.get("price", "0")) or None,
            filled_quantity=filled,
            average_fill_price=avg_price,
            status=self._map_order_status(data.get("status", "")),
            created_at=datetime.fromtimestamp(
                data.get("time", int(time.time() * 1000)) / 1000, tz=UTC
            ),
            updated_at=datetime.fromtimestamp(
                data.get("updateTime", int(time.time() * 1000)) / 1000, tz=UTC
            ),
            error_message=None,
        )

    def _map_order_status(self, status: str) -> str:
        mapping = {
            "NEW": "open",
            "PARTIALLY_FILLED": "partially_filled",
            "FILLED": "filled",
            "CANCELED": "cancelled",
            "REJECTED": "rejected",
            "EXPIRED": "expired",
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

        # MEXC sends different message formats
        if data.get("c") and data.get("d"):
            symbol = data.get("symbol", "").upper()
            channel = data.get("c", "")
            if "ticker" in channel:
                cb = self._ticker_callbacks.get(symbol)
                if cb:
                    cb(data)
            elif "depth" in channel:
                cb = self._orderbook_callbacks.get(symbol)
                if cb:
                    cb(data)
        else:
            logger.debug(f"Unhandled MEXC WebSocket message: {data}")


# Register adapter automatically when module is imported.
ExchangeFactory.register("mexc", MEXCAdapter)
