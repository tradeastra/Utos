"""Binance Spot adapter — Sprint 4.

Implements IExchangeAdapter using the exchange-agnostic infrastructure from
Sprint 3 (HttpClient, WebSocketManager, RateLimiter, RetryPolicy).  All
Binance-specific protocol logic (URLs, signatures, message routing, error
codes) lives in this file.
"""

import asyncio
import hashlib
import hmac
import json
import time
import urllib.parse
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

import httpx

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
from exchanges.adapter import IExchangeAdapter
from exchanges.credential_manager import CredentialManager
from exchanges.errors import ErrorMapper
from exchanges.factory import ExchangeFactory
from exchanges.http_client import HttpClient
from exchanges.rate_limiter import RateLimiter, RateLimitConfig
from exchanges.retry import RetryPolicy
from exchanges.websocket_manager import WebSocketManager

logger = get_logger(__name__)


class BinanceAuthenticator:
    """HMAC-SHA256 request signer for Binance."""

    def __init__(self, api_key: str = "", api_secret: str = "") -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self._time_offset_ms: float = 0.0

    def set_credentials(self, api_key: str, api_secret: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret

    def update_time_offset(self, server_time_ms: int, local_time_ms: int) -> None:
        self._time_offset_ms = server_time_ms - local_time_ms

    def timestamp(self) -> int:
        return int((time.time() * 1000) + self._time_offset_ms)

    def sign(self, query_string: str) -> str:
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def auth_headers(self) -> dict[str, str]:
        return {"X-MBX-APIKEY": self.api_key}


class BinanceSpotAdapter(IExchangeAdapter):
    """Concrete Binance Spot adapter implementing IExchangeAdapter."""

    name = "binance"

    # Binance Spot API defaults
    REST_MAINNET = "https://api.binance.com"
    REST_TESTNET = "https://testnet.binance.vision"
    WS_MAINNET = "wss://stream.binance.com:9443/ws"
    WS_TESTNET = "wss://testnet.binance.vision/ws"

    def __init__(
        self,
        http_client: Optional[HttpClient] = None,
        ws_manager: Optional[WebSocketManager] = None,
        ws_account_manager: Optional[WebSocketManager] = None,
        credential_manager: Optional[CredentialManager] = None,
        authenticator: Optional[BinanceAuthenticator] = None,
    ) -> None:
        self.http = http_client
        self.ws = ws_manager
        self.ws_account = ws_account_manager
        self.credential_manager = credential_manager
        self.authenticator = authenticator or BinanceAuthenticator()

        self.config: Optional[ExchangeAdapterConfig] = None
        self.credentials: Optional[ExchangeCredentials] = None
        self.rest_url: str = ""
        self.ws_url: str = ""
        self.recv_window: int = 5000
        self._exchange_info: Optional[dict[str, Any]] = None
        self._listen_key: Optional[str] = None
        self._keepalive_task: Optional[asyncio.Task] = None

        self._ticker_callbacks: dict[str, Callable[[Any], None]] = {}
        self._orderbook_callbacks: dict[str, Callable[[Any], None]] = {}
        self._user_data_callback: Optional[Callable[[Any], None]] = None

        self._subscribed_ids: dict[str, int] = {}
        self._next_id: int = 1

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------
    async def initialize(self, config: ExchangeAdapterConfig) -> bool:
        self.config = config
        self.name = config.exchange_name or self.name
        self.rest_url = (
            self.REST_TESTNET if config.is_testnet else config.rest_url or self.REST_MAINNET
        ).rstrip("/")
        self.ws_url = (
            self.WS_TESTNET if config.is_testnet else config.market_stream_url or self.WS_MAINNET
        ).rstrip("/")
        self.recv_window = getattr(config, "recv_window", 5000)

        rate_limiter = RateLimiter()
        rate_limiter.configure("rest", RateLimitConfig(max_tokens=1200.0, refill_rate=20.0))
        rate_limiter.configure("websocket", RateLimitConfig(max_tokens=5.0, refill_rate=5.0))

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
            self.ws = WebSocketManager(retry_policy=ws_retry_policy, rate_limiter=rate_limiter)
        if self.ws_account is None:
            self.ws_account = WebSocketManager(retry_policy=ws_retry_policy, rate_limiter=rate_limiter)

        if self.credential_manager is None:
            self.credential_manager = CredentialManager()

        self.ws.register_callback(self._dispatch)
        self.ws_account.register_callback(self._dispatch)
        return True

    async def authenticate(self, credentials: ExchangeCredentials) -> bool:
        await self._sync_time()
        self.credentials = credentials
        self.authenticator.set_credentials(credentials.api_key, credentials.api_secret)
        response = await self._signed_get("/api/v3/account")
        self._raise_for_status(response)
        return True

    async def _sync_time(self) -> bool:
        response = await self.http.get("/api/v3/time")
        self._raise_for_status(response)
        data = response.json()
        local_ms = int(time.time() * 1000)
        self.authenticator.update_time_offset(data["serverTime"], local_ms)
        return True

    async def connect_market(self) -> bool:
        return await self.ws.connect(self.ws_url)

    async def connect_account(self) -> bool:
        if not self._listen_key:
            response = await self._start_listen_key()
            self._raise_for_status(response)
            data = response.json()
            self._listen_key = data["listenKey"]
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())

        url = f"{self.ws_url}/{self._listen_key}"
        return await self.ws_account.connect(url)

    async def disconnect(self) -> None:
        self._ticker_callbacks.clear()
        self._orderbook_callbacks.clear()
        self._user_data_callback = None

        if self._keepalive_task is not None:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass
            self._keepalive_task = None

        if self.ws is not None:
            await self.ws.disconnect()

        if self.ws_account is not None:
            await self.ws_account.disconnect()

        if self.http is not None:
            await self.http.close()

        self._listen_key = None

    async def health_check(self) -> bool:
        try:
            await self._sync_time()
            return True
        except Exception as exc:
            logger.warning(f"Binance health check failed: {exc}")
            return False

    # -------------------------------------------------------------------------
    # Account & Symbol
    # -------------------------------------------------------------------------
    async def get_account(self) -> dict[str, Any]:
        response = await self._signed_get("/api/v3/account")
        return self._parse_json(response)

    async def get_balance(self, asset: Optional[str] = None) -> list[BalanceEntry]:
        account = await self.get_account()
        balances: list[BalanceEntry] = []
        for item in account.get("balances", []):
            if asset and item["asset"] != asset.upper():
                continue
            balances.append(
                BalanceEntry(
                    currency=item["asset"],
                    available=Decimal(item["free"]),
                    locked=Decimal(item["locked"]),
                    total=Decimal(item["free"]) + Decimal(item["locked"]),
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
            rate_limits=info.get("rateLimits", {}),
            fee_structure={},
            server_time=datetime.fromtimestamp(
                info.get("serverTime", int(time.time() * 1000)) / 1000, tz=timezone.utc
            ),
        )

    async def get_positions(self, symbol: Optional[str] = None) -> list[PositionEntry]:
        # Spot does not have leveraged positions in this adapter.
        return []

    # -------------------------------------------------------------------------
    # Market data
    # -------------------------------------------------------------------------
    async def get_ticker(self, symbol: str) -> TickerData:
        upper = symbol.upper()
        book = self._parse_json(
            await self.http.get("/api/v3/ticker/bookTicker", params={"symbol": upper})
        )
        stats = self._parse_json(
            await self.http.get("/api/v3/ticker/24hr", params={"symbol": upper})
        )
        return TickerData(
            symbol=upper,
            bid=Decimal(book["bidPrice"]),
            ask=Decimal(book["askPrice"]),
            last=Decimal(stats["lastPrice"]),
            volume=Decimal(stats["volume"]),
            timestamp=datetime.fromtimestamp(stats["closeTime"] / 1000, tz=timezone.utc),
        )

    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        data = self._parse_json(
            await self.http.get("/api/v3/depth", params={"symbol": symbol.upper(), "limit": limit})
        )
        return OrderBook(
            symbol=symbol.upper(),
            bids=[(Decimal(b[0]), Decimal(b[1])) for b in data.get("bids", [])],
            asks=[(Decimal(a[0]), Decimal(a[1])) for a in data.get("asks", [])],
            timestamp=datetime.now(timezone.utc),
        )

    async def get_candles(
        self, symbol: str, interval: str, limit: int = 100
    ) -> list[Candle]:
        data = self._parse_json(
            await self.http.get(
                "/api/v3/klines",
                params={"symbol": symbol.upper(), "interval": interval, "limit": limit},
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
                    timestamp=datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc),
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
                    trade_id=str(row["id"]),
                    order_id="",
                    symbol=symbol.upper(),
                    side="sell" if row.get("isBuyerMaker") else "buy",
                    quantity=Decimal(row["qty"]),
                    price=Decimal(row["price"]),
                    fee=Decimal("0"),
                    fee_currency=self._quote_asset(symbol),
                    timestamp=datetime.fromtimestamp(row["time"] / 1000, tz=timezone.utc),
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
        price: Optional[Decimal] = None,
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
        for key in ("stopPrice", "icebergQty", "newClientOrderId"):
            if key in kwargs:
                params[key] = kwargs[key]
        response = await self._signed_post("/api/v3/order", params)
        return self._order_result_from_response(self._parse_json(response))

    async def cancel_order(self, symbol: str, order_id: str) -> OrderResult:
        params = {"symbol": symbol.upper(), "orderId": int(order_id)}
        response = await self._signed_delete("/api/v3/order", params)
        return self._order_result_from_response(self._parse_json(response))

    async def cancel_all(self, symbol: Optional[str] = None) -> list[OrderResult]:
        if symbol:
            params = {"symbol": symbol.upper()}
            response = await self._signed_delete("/api/v3/openOrders", params)
        else:
            # Without symbol, Binance requires per-symbol cancellation.
            results: list[OrderResult] = []
            for order in await self.get_open_orders():
                if order.symbol:
                    results.append(await self.cancel_order(order.symbol, order.exchange_order_id))
            return results

        if response.status_code == 200:
            data = self._parse_json(response)
            if isinstance(data, list):
                return [self._order_result_from_response(o) for o in data]
            if data is None:
                return []
        return []

    async def get_order(self, symbol: str, order_id: str) -> OrderResult:
        params = {"symbol": symbol.upper(), "orderId": int(order_id)}
        response = await self._signed_get("/api/v3/order", params)
        return self._order_result_from_response(self._parse_json(response))

    async def get_open_orders(self, symbol: Optional[str] = None) -> list[OrderResult]:
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

        streams: list[str] = []
        for symbol in symbols:
            upper = symbol.upper()
            if channel == "ticker":
                stream = f"{upper.lower()}@ticker"
                self._ticker_callbacks[upper] = callback
            elif channel == "orderbook":
                stream = f"{upper.lower()}@depth"
                self._orderbook_callbacks[upper] = callback
            else:
                stream = f"{upper.lower()}@{channel}"
            streams.append(stream)

        msg = self._ws_subscribe_message(streams)
        await self.ws.subscribe(json.dumps(msg))
        return True

    async def subscribe_account(self, channel: str, callback: Callable[[Any], None]) -> bool:
        if not self.ws_account.is_connected or not self._listen_key:
            await self.connect_account()
        self._user_data_callback = callback
        return True

    async def unsubscribe_market(self, symbols: list[str], channel: str) -> bool:
        streams: list[str] = []
        for symbol in symbols:
            upper = symbol.upper()
            if channel == "ticker":
                self._ticker_callbacks.pop(upper, None)
                streams.append(f"{upper.lower()}@ticker")
            elif channel == "orderbook":
                self._orderbook_callbacks.pop(upper, None)
                streams.append(f"{upper.lower()}@depth")
            else:
                streams.append(f"{upper.lower()}@{channel}")

        msg = self._ws_unsubscribe_message(streams)
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
            raise AuthenticationError("Binance adapter is not authenticated")

    def _signed_params(self, params: dict[str, Any]) -> dict[str, Any]:
        self._ensure_authenticated()
        params = dict(params)
        params["recvWindow"] = params.get("recvWindow", self.recv_window)
        params["timestamp"] = self.authenticator.timestamp()
        to_sign = urllib.parse.urlencode(sorted(params.items()), doseq=True)
        params["signature"] = self.authenticator.sign(to_sign)
        return params

    async def _signed_request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
    ) -> httpx.Response:
        """Execute a signed request and auto-resync once on timestamp drift."""
        params = params or {}
        for attempt in range(2):
            signed = self._signed_params(dict(params))
            headers = self.authenticator.auth_headers()
            try:
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
            except ExchangeError as exc:
                if attempt == 0 and getattr(exc, "error_code", None) == "TIMESTAMP_DRIFT":
                    logger.warning("Binance timestamp drift detected; resyncing server time")
                    await self._sync_time()
                    continue
                raise
        raise ExchangeError("Binance timestamp drift persisted after resync", self.name)

    async def _signed_get(self, path: str, params: Optional[dict[str, Any]] = None) -> httpx.Response:
        return await self._signed_request("GET", path, params)

    async def _signed_post(self, path: str, params: dict[str, Any]) -> httpx.Response:
        return await self._signed_request("POST", path, params)

    async def _signed_delete(self, path: str, params: dict[str, Any]) -> httpx.Response:
        return await self._signed_request("DELETE", path, params)

    async def _start_listen_key(self) -> httpx.Response:
        self._ensure_authenticated()
        headers = self.authenticator.auth_headers()
        return await self.http.post(
            "/api/v3/userDataStream", headers=headers
        )

    async def _keepalive_loop(self, interval: float = 1800.0) -> None:
        while True:
            try:
                await asyncio.sleep(interval)
                if self._listen_key:
                    await self.http.put(
                        "/api/v3/userDataStream",
                        params={"listenKey": self._listen_key},
                        headers=self.authenticator.auth_headers(),
                    )
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning(f"Listen key keepalive failed: {exc}")

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
            raise ExchangeError("Invalid JSON response from Binance", self.name) from exc

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

        if status == 429 or code == -1003 or code == -1015:
            raise ExchangeRateLimitError("Binance rate limit exceeded", self.name)
        if status == 418:
            raise ExchangeRateLimitError("Binance IP banned", self.name)
        if code == -1021:
            raise ExchangeError(
                "Binance timestamp drift detected",
                self.name,
                error_code="TIMESTAMP_DRIFT",
                details={"binance_code": code, "msg": msg},
            )
        if code == -1022 or code == -2014 or code == -2015:
            raise AuthenticationError(f"Binance invalid API key or signature: {msg}")
        if code == -2013:
            raise OrderNotFound(str(body.get("orderId", "")))
        if code == -2010 and "balance" in msg.lower():
            raise InsufficientBalanceError(f"Binance insufficient balance: {msg}")
        if code == -1120 or code == -1121:
            raise SymbolNotSupported(body.get("symbol", ""), self.name)
        if status >= 500:
            raise ExchangeConnectionError(f"Binance server error {status}: {msg}", self.name)

        raise ExchangeError(f"Binance HTTP {status}: {msg}", self.name)

    def _order_result_from_response(self, data: dict[str, Any]) -> OrderResult:
        filled = Decimal(data.get("executedQty", "0"))
        quote = Decimal(data.get("cummulativeQuoteQty", "0"))
        avg_price = quote / filled if filled > 0 else Decimal("0")
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
            created_at=datetime.fromtimestamp(data.get("time", int(time.time() * 1000)) / 1000, tz=timezone.utc),
            updated_at=datetime.fromtimestamp(data.get("updateTime", int(time.time() * 1000)) / 1000, tz=timezone.utc),
            error_message=None,
        )

    def _map_order_status(self, status: str) -> str:
        mapping = {
            "NEW": "open",
            "PARTIALLY_FILLED": "partially_filled",
            "FILLED": "filled",
            "CANCELED": "cancelled",
            "PENDING_CANCEL": "pending",
            "REJECTED": "rejected",
            "EXPIRED": "expired",
        }
        return mapping.get(status, status.lower())

    def _quote_asset(self, symbol: str) -> str:
        s = symbol.upper()
        if len(s) > 6:
            return s[-4:] if s[-4] in ("U", "B", "T", "F") else s[-3:]
        return s[-3:]

    def _ws_subscribe_message(self, streams: list[str]) -> dict[str, Any]:
        msg_id = self._next_id
        self._next_id += 1
        return {"method": "SUBSCRIBE", "params": streams, "id": msg_id}

    def _ws_unsubscribe_message(self, streams: list[str]) -> dict[str, Any]:
        msg_id = self._next_id
        self._next_id += 1
        return {"method": "UNSUBSCRIBE", "params": streams, "id": msg_id}

    def _dispatch(self, message: Any) -> None:
        if not isinstance(message, str):
            return
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        if not isinstance(data, dict):
            return

        event = data.get("e")
        symbol = data.get("s")

        if event == "24hrTicker" and symbol:
            cb = self._ticker_callbacks.get(symbol.upper())
            if cb:
                cb(data)
        elif event == "depthUpdate" and symbol:
            cb = self._orderbook_callbacks.get(symbol.upper())
            if cb:
                cb(data)
        elif event in ("outboundAccountPosition", "executionReport", "balanceUpdate"):
            if self._user_data_callback:
                self._user_data_callback(data)
        elif "result" in data and data.get("result") is None:
            logger.debug(f"Subscription acknowledged: {data}")
        else:
            logger.debug(f"Unhandled Binance WebSocket message: {data}")


# Register adapter automatically when module is imported.
ExchangeFactory.register("binance", BinanceSpotAdapter)
