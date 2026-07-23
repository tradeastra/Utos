"""OKX V5 adapter.

Implements IExchangeAdapter using the exchange-agnostic infrastructure from
Sprint 3.  OKX uses HMAC-SHA256 + base64 signature and requires a passphrase.
"""

import base64
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


class OKXAuthenticator:
    """HMAC-SHA256 + base64 request signer for OKX V5 API."""

    def __init__(self, api_key: str = "", api_secret: str = "", passphrase: str = "") -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase

    def set_credentials(self, api_key: str, api_secret: str, passphrase: str = "") -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase

    def timestamp(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.") + f"{int(datetime.now(UTC).microsecond / 1000):03d}Z"

    def sign(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        prehash = f"{timestamp}{method.upper()}{path}{body}"
        mac = hmac.new(
            self.api_secret.encode("utf-8"),
            prehash.encode("utf-8"),
            hashlib.sha256,
        )
        return base64.b64encode(mac.digest()).decode("utf-8")

    def auth_headers(self, signature: str, timestamp: str, passphrase: str) -> dict[str, str]:
        return {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": passphrase,
            "Content-Type": "application/json",
        }


class OKXAdapter(IExchangeAdapter):
    """Concrete OKX V5 adapter implementing IExchangeAdapter."""

    name = "okx"

    REST_MAINNET = "https://www.okx.com"
    REST_TESTNET = "https://sim5.okx.com"
    WS_PUBLIC_MAINNET = "wss://ws.okx.com/ws/v5/public"
    WS_PUBLIC_TESTNET = "wss://wspap.okx.com/ws/v5/public?brokerId=9999"
    WS_PRIVATE_MAINNET = "wss://ws.okx.com/ws/v5/private"
    WS_PRIVATE_TESTNET = "wss://wspap.okx.com/ws/v5/private?brokerId=9999"

    def __init__(
        self,
        http_client: HttpClient | None = None,
        ws_manager: WebSocketManager | None = None,
        ws_account_manager: WebSocketManager | None = None,
        credential_manager: CredentialManager | None = None,
        authenticator: OKXAuthenticator | None = None,
    ) -> None:
        self.http = http_client
        self.ws = ws_manager
        self.ws_account = ws_account_manager
        self.credential_manager = credential_manager
        self.authenticator = authenticator or OKXAuthenticator()

        self.config: ExchangeAdapterConfig | None = None
        self.credentials: ExchangeCredentials | None = None
        self.rest_url: str = ""
        self.ws_url: str = ""
        self.ws_private_url: str = ""
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
            self.WS_PUBLIC_TESTNET
            if config.is_testnet
            else config.market_stream_url or self.WS_PUBLIC_MAINNET
        ).rstrip("/")
        self.ws_private_url = (
            self.WS_PRIVATE_TESTNET
            if config.is_testnet
            else config.account_stream_url or self.WS_PRIVATE_MAINNET
        ).rstrip("/")

        rate_limiter = RateLimiter()
        rate_limiter.configure(
            "rest", RateLimitConfig(max_tokens=60.0, refill_rate=10.0)
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
        passphrase = credentials.passphrase or ""
        self.authenticator.set_credentials(credentials.api_key, credentials.api_secret, passphrase)
        response = await self._signed_get("/api/v5/account/balance")
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
            response = await self.http.get("/api/v5/public/time")
            self._raise_for_status(response)
            return True
        except Exception as exc:
            logger.warning(f"OKX health check failed: {exc}")
            return False

    # -------------------------------------------------------------------------
    # Account & Symbol
    # -------------------------------------------------------------------------
    async def get_account(self) -> dict[str, Any]:
        response = await self._signed_get("/api/v5/account/balance")
        return self._parse_json(response)

    async def get_balance(self, asset: str | None = None) -> list[BalanceEntry]:
        account = await self.get_account()
        balances: list[BalanceEntry] = []
        for detail in account.get("data", [{}]):
            for bal in detail.get("details", []):
                if asset and bal.get("ccy") != asset.upper():
                    continue
                available = Decimal(bal.get("availBal", "0"))
                frozen = Decimal(bal.get("frozenBal", "0"))
                total = available + frozen
                balances.append(
                    BalanceEntry(
                        currency=bal.get("ccy", ""),
                        available=available,
                        locked=frozen,
                        total=total,
                    )
                )
        return balances

    async def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        info = await self._load_exchange_info()
        for inst in info.get("data", []):
            if inst.get("instId") == symbol.upper():
                return inst
        raise SymbolNotSupported(symbol, self.name)

    async def get_exchange_info(self) -> ExchangeInfo:
        info = await self._load_exchange_info()
        symbols = [s["instId"] for s in info.get("data", []) if s.get("instType") == "SPOT"]
        return ExchangeInfo(
            name=self.name,
            supported_symbols=symbols,
            rate_limits={},
            fee_structure={},
            server_time=datetime.now(UTC),
        )

    async def get_positions(self, symbol: str | None = None) -> list[PositionEntry]:
        params: dict[str, Any] = {"instType": "SWAP"}
        if symbol:
            params["instId"] = symbol.upper()
        response = await self._signed_get("/api/v5/account/positions", params)
        data = self._parse_json(response)
        positions: list[PositionEntry] = []
        for pos in data.get("data", []):
            positions.append(
                PositionEntry(
                    symbol=pos.get("instId", ""),
                    side=pos.get("posSide", "").lower(),
                    quantity=Decimal(pos.get("pos", "0")),
                    entry_price=Decimal(pos.get("avgPx", "0")),
                    unrealized_pnl=Decimal(pos.get("upl", "0")),
                )
            )
        return positions

    # -------------------------------------------------------------------------
    # Market data
    # -------------------------------------------------------------------------
    async def get_ticker(self, symbol: str) -> TickerData:
        upper = symbol.upper()
        data = self._parse_json(
            await self.http.get("/api/v5/market/ticker", params={"instId": upper})
        )
        tickers = data.get("data", [])
        if not tickers:
            raise SymbolNotSupported(symbol, self.name)
        t = tickers[0]
        return TickerData(
            symbol=upper,
            bid=Decimal(t.get("bidPx", "0")),
            ask=Decimal(t.get("askPx", "0")),
            last=Decimal(t.get("last", "0")),
            volume=Decimal(t.get("vol24h", "0")),
            timestamp=datetime.now(UTC),
        )

    async def get_order_book(self, symbol: str, limit: int = 50) -> OrderBook:
        data = self._parse_json(
            await self.http.get(
                "/api/v5/market/books", params={"instId": symbol.upper(), "sz": limit}
            )
        )
        books = data.get("data", [])
        if not books:
            raise SymbolNotSupported(symbol, self.name)
        book = books[0]
        return OrderBook(
            symbol=symbol.upper(),
            bids=[(Decimal(b[0]), Decimal(b[1])) for b in book.get("bids", [])],
            asks=[(Decimal(a[0]), Decimal(a[1])) for a in book.get("asks", [])],
            timestamp=datetime.now(UTC),
        )

    async def get_candles(
        self, symbol: str, interval: str, limit: int = 300
    ) -> list[Candle]:
        interval_map = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1H", "4h": "4H", "1d": "1D"}
        okx_interval = interval_map.get(interval, interval)
        data = self._parse_json(
            await self.http.get(
                "/api/v5/market/candles",
                params={"instId": symbol.upper(), "bar": okx_interval, "limit": limit},
            )
        )
        candles: list[Candle] = []
        for row in data.get("data", []):
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
                "/api/v5/market/trades", params={"instId": symbol.upper(), "limit": limit}
            )
        )
        trades: list[TradeEntry] = []
        for row in data.get("data", []):
            trades.append(
                TradeEntry(
                    trade_id=str(row.get("tradeId", "")),
                    order_id=str(row.get("ordId", "")),
                    symbol=symbol.upper(),
                    side=row.get("side", "").lower(),
                    quantity=Decimal(row.get("sz", "0")),
                    price=Decimal(row.get("px", "0")),
                    fee=Decimal("0"),
                    fee_currency="USDT",
                    timestamp=datetime.fromtimestamp(int(row.get("ts", "0")) / 1000, tz=UTC),
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
            "instId": symbol.upper(),
            "tdMode": "cash",
            "side": side.lower(),
            "ordType": order_type.lower(),
            "sz": str(quantity),
        }
        if price is not None:
            params["px"] = str(price)
        if kwargs.get("client_order_id"):
            params["clOrdId"] = kwargs["client_order_id"]
        response = await self._signed_post("/api/v5/trade/order", params)
        return self._order_result_from_response(self._parse_json(response), symbol.upper(), side, order_type, quantity, price)

    async def cancel_order(self, symbol: str, order_id: str) -> OrderResult:
        params = {"instId": symbol.upper(), "ordId": order_id}
        response = await self._signed_post("/api/v5/trade/cancel-order", params)
        self._raise_for_status(response)
        return OrderResult(
            order_id="",
            exchange_order_id=order_id,
            symbol=symbol.upper(),
            side="",
            order_type="",
            quantity=Decimal("0"),
            price=None,
            filled_quantity=Decimal("0"),
            average_fill_price=None,
            status="cancelled",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    async def cancel_all(self, symbol: str | None = None) -> list[OrderResult]:
        params: dict[str, Any] = {}
        if symbol:
            params["instId"] = symbol.upper()
        response = await self._signed_post("/api/v5/trade/cancel-orders", params)
        self._raise_for_status(response)
        return []

    async def get_order(self, symbol: str, order_id: str) -> OrderResult:
        params = {"instId": symbol.upper(), "ordId": order_id}
        response = await self._signed_get("/api/v5/trade/order", params)
        data = self._parse_json(response)
        orders = data.get("data", [])
        if not orders:
            raise OrderNotFound(order_id)
        return self._order_result_from_list(orders[0])

    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        params: dict[str, Any] = {}
        if symbol:
            params["instId"] = symbol.upper()
        response = await self._signed_get("/api/v5/trade/orders-pending", params)
        data = self._parse_json(response)
        return [self._order_result_from_list(o) for o in data.get("data", [])]

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
                args.append(f"tickers/{upper}")
                self._ticker_callbacks[upper] = callback
            elif channel == "orderbook":
                args.append(f"books5/{upper}")
                self._orderbook_callbacks[upper] = callback
            else:
                args.append(f"{channel}/{upper}")

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
                args.append(f"tickers/{upper}")
            elif channel == "orderbook":
                self._orderbook_callbacks.pop(upper, None)
                args.append(f"books5/{upper}")
            else:
                args.append(f"{channel}/{upper}")
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
            raise AuthenticationError("OKX adapter is not authenticated")

    async def _signed_request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        self._ensure_authenticated()
        params = params or {}
        ts = self.authenticator.timestamp()

        if method == "GET":
            query = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            full_path = f"{path}?{query}" if query else path
            body = ""
        else:
            full_path = path
            body = json.dumps(params, separators=(",", ":"))

        signature = self.authenticator.sign(ts, method, full_path, body)
        passphrase = self.authenticator.passphrase
        headers = self.authenticator.auth_headers(signature, ts, passphrase)

        if method == "GET":
            response = await self.http.get(path, params=params, headers=headers)
        elif method == "POST":
            response = await self.http.post(path, content=body, headers=headers)
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
            response = await self.http.get("/api/v5/public/instruments", params={"instType": "SPOT"})
            self._exchange_info = self._parse_json(response)
        return self._exchange_info

    def _parse_json(self, response: httpx.Response) -> Any:
        self._raise_for_status(response)
        try:
            return response.json()
        except Exception as exc:
            raise ExchangeError("Invalid JSON response from OKX", self.name) from exc

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        try:
            body = response.json()
        except Exception:
            body = {}

        code = body.get("code", "0")
        msg = body.get("msg", "")
        status = response.status_code

        if status == 429 or code == "50011":
            raise ExchangeRateLimitError(f"OKX rate limit: {msg}", self.name)
        if code in ("50102", "50103", "50104"):
            raise AuthenticationError(f"OKX auth error: {msg}")
        if code == "51001":
            raise SymbolNotSupported("", self.name)
        if code == "51020":
            raise InsufficientBalanceError(f"OKX insufficient balance: {msg}")
        if code == "51401":
            raise OrderNotFound(str(msg))
        if status >= 500:
            raise ExchangeConnectionError(f"OKX server error {status}: {msg}", self.name)

        raise ExchangeError(f"OKX error {code}: {msg}", self.name)

    def _order_result_from_response(
        self,
        data: dict[str, Any],
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Decimal | None,
    ) -> OrderResult:
        result = data.get("data", [{}])[0] if data.get("data") else {}
        return OrderResult(
            order_id=str(result.get("clOrdId", "")),
            exchange_order_id=str(result.get("ordId", "")),
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
            error_message=result.get("sMsg"),
        )

    def _order_result_from_list(self, data: dict[str, Any]) -> OrderResult:
        return OrderResult(
            order_id=str(data.get("clOrdId", "")),
            exchange_order_id=str(data.get("ordId", "")),
            symbol=data.get("instId", ""),
            side=data.get("side", "").lower(),
            order_type=data.get("ordType", "").lower(),
            quantity=Decimal(data.get("sz", "0")),
            price=Decimal(data.get("px", "0")) or None,
            filled_quantity=Decimal(data.get("fillSz", "0")),
            average_fill_price=Decimal(data.get("avgPx", "0")) or None,
            status=self._map_order_status(data.get("state", "")),
            created_at=datetime.fromtimestamp(int(data.get("cTime", "0")) / 1000, tz=UTC),
            updated_at=datetime.fromtimestamp(int(data.get("uTime", "0")) / 1000, tz=UTC),
            error_message=None,
        )

    def _map_order_status(self, status: str) -> str:
        mapping = {
            "live": "open",
            "partially_filled": "partially_filled",
            "filled": "filled",
            "canceled": "cancelled",
            "mmp_canceled": "cancelled",
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

        arg = data.get("arg", {})
        channel = arg.get("channel", "")
        inst_id = arg.get("instId", "")

        if channel == "tickers" and inst_id:
            cb = self._ticker_callbacks.get(inst_id.upper())
            if cb:
                cb(data)
        elif channel.startswith("books") and inst_id:
            cb = self._orderbook_callbacks.get(inst_id.upper())
            if cb:
                cb(data)
        elif data.get("event") == "login":
            logger.info("OKX private WebSocket authenticated")
        else:
            logger.debug(f"Unhandled OKX WebSocket message: {data}")


# Register adapter automatically when module is imported.
ExchangeFactory.register("okx", OKXAdapter)
