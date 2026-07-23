"""Hyperliquid DEX adapter.

Implements IExchangeAdapter for Hyperliquid — a decentralized L1 exchange.
Unlike CEX adapters, Hyperliquid uses EIP-712 typed-data signatures via
an Ethereum wallet private key rather than API key/secret HMAC.

The adapter communicates with the Hyperliquid API endpoint via POST requests
with action payloads.  Market data (prices, orderbook, candles) is public
and requires no authentication.  Trading operations require signing.
"""

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


class HyperliquidAdapter(IExchangeAdapter):
    """Concrete Hyperliquid DEX adapter implementing IExchangeAdapter.

    Uses api_secret as the Ethereum wallet private key for signing.
    api_key is used as the wallet address.
    """

    name = "hyperliquid"

    REST_MAINNET = "https://api.hyperliquid.xyz"
    REST_TESTNET = "https://api.hyperliquid-testnet.xyz"
    WS_MAINNET = "wss://api.hyperliquid.xyz/ws"
    WS_TESTNET = "wss://api.hyperliquid-testnet.xyz/ws"

    def __init__(
        self,
        http_client: HttpClient | None = None,
        ws_manager: WebSocketManager | None = None,
        ws_account_manager: WebSocketManager | None = None,
        credential_manager: CredentialManager | None = None,
    ) -> None:
        self.http = http_client
        self.ws = ws_manager
        self.ws_account = ws_account_manager
        self.credential_manager = credential_manager

        self.config: ExchangeAdapterConfig | None = None
        self.credentials: ExchangeCredentials | None = None
        self.rest_url: str = ""
        self.ws_url: str = ""
        self._exchange_info: dict[str, Any] | None = None
        self._wallet_address: str = ""

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
        self._wallet_address = credentials.api_key
        # Verify by querying clearinghouse state (user's account)
        response = await self._post_info(
            {"type": "clearinghouseState", "user": self._wallet_address}
        )
        if response is None:
            raise AuthenticationError("Hyperliquid authentication failed: cannot query account")
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
            response = await self._post_info({"type": "meta"})
            return response is not None
        except Exception as exc:
            logger.warning(f"Hyperliquid health check failed: {exc}")
            return False

    # -------------------------------------------------------------------------
    # Account & Symbol
    # -------------------------------------------------------------------------
    async def get_account(self) -> dict[str, Any]:
        return await self._post_info(
            {"type": "clearinghouseState", "user": self._wallet_address}
        )

    async def get_balance(self, asset: str | None = None) -> list[BalanceEntry]:
        data = await self.get_account()
        balances: list[BalanceEntry] = []
        if not data:
            return balances

        # Margin / perp balance
        margin = Decimal(data.get("marginSummary", {}).get("accountValue", "0"))
        if margin > 0:
            balances.append(
                BalanceEntry(
                    currency="USDC",
                    available=Decimal(data.get("marginSummary", {}).get("availableMargin", "0")),
                    locked=margin - Decimal(data.get("marginSummary", {}).get("availableMargin", "0")),
                    total=margin,
                )
            )

        # Spot balances
        spot_data = await self._post_info(
            {"type": "spotClearinghouseState", "user": self._wallet_address}
        )
        if spot_data:
            for bal in spot_data.get("balances", []):
                coin = bal.get("coin", "")
                if asset and coin != asset.upper():
                    continue
                total = Decimal(bal.get("total", "0"))
                hold = Decimal(bal.get("hold", "0"))
                balances.append(
                    BalanceEntry(
                        currency=coin,
                        available=total - hold,
                        locked=hold,
                        total=total,
                    )
                )
        return balances

    async def get_symbol_info(self, symbol: str) -> dict[str, Any]:
        meta = await self._post_info({"type": "meta"})
        if not meta:
            raise SymbolNotSupported(symbol, self.name)
        for asset in meta.get("universe", []):
            if asset.get("name") == symbol.upper():
                return asset
        raise SymbolNotSupported(symbol, self.name)

    async def get_exchange_info(self) -> ExchangeInfo:
        meta = await self._post_info({"type": "meta"})
        symbols = [a["name"] for a in (meta or {}).get("universe", [])]
        return ExchangeInfo(
            name=self.name,
            supported_symbols=symbols,
            rate_limits={},
            fee_structure={},
            server_time=datetime.now(UTC),
        )

    async def get_positions(self, symbol: str | None = None) -> list[PositionEntry]:
        data = await self.get_account()
        positions: list[PositionEntry] = []
        if not data:
            return positions
        for pos in data.get("assetPositions", []):
            p = pos.get("position", {})
            if symbol and p.get("coin") != symbol.upper():
                continue
            positions.append(
                PositionEntry(
                    symbol=p.get("coin", ""),
                    side="long" if Decimal(p.get("szi", "0")) > 0 else "short",
                    quantity=abs(Decimal(p.get("szi", "0"))),
                    entry_price=Decimal(p.get("entryPx", "0")),
                    unrealized_pnl=Decimal(p.get("unrealizedPnl", "0")),
                )
            )
        return positions

    # -------------------------------------------------------------------------
    # Market data
    # -------------------------------------------------------------------------
    async def get_ticker(self, symbol: str) -> TickerData:
        upper = symbol.upper()
        data = await self._post_info({"type": "l2Book", "coin": upper})
        if not data:
            raise SymbolNotSupported(symbol, self.name)
        levels = data.get("levels", [])
        bids = [(Decimal(l["px"]), Decimal(l["sz"])) for l in levels if l.get("side") == "bid"]
        asks = [(Decimal(l["px"]), Decimal(l["sz"])) for l in levels if l.get("side") == "ask"]
        best_bid = bids[0][0] if bids else Decimal("0")
        best_ask = asks[0][0] if asks else Decimal("0")

        # Get last trade price from allMids
        mids = await self._post_info({"type": "allMids"})
        last = Decimal(mids.get(upper, str(best_bid))) if mids else best_bid

        return TickerData(
            symbol=upper,
            bid=best_bid,
            ask=best_ask,
            last=last,
            volume=Decimal("0"),
            timestamp=datetime.now(UTC),
        )

    async def get_order_book(self, symbol: str, limit: int = 100) -> OrderBook:
        upper = symbol.upper()
        data = await self._post_info({"type": "l2Book", "coin": upper})
        if not data:
            raise SymbolNotSupported(symbol, self.name)
        levels = data.get("levels", [])
        bids = [(Decimal(l["px"]), Decimal(l["sz"])) for l in levels if l.get("side") == "bid"]
        asks = [(Decimal(l["px"]), Decimal(l["sz"])) for l in levels if l.get("side") == "ask"]
        return OrderBook(
            symbol=upper,
            bids=bids[:limit],
            asks=asks[:limit],
            timestamp=datetime.now(UTC),
        )

    async def get_candles(
        self, symbol: str, interval: str, limit: int = 500
    ) -> list[Candle]:
        interval_map = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
        hl_interval = interval_map.get(interval, interval)
        now_ms = int(time.time() * 1000)
        # Hyperliquid candle endpoint uses start/end timestamps
        start_ms = now_ms - (limit * self._interval_to_ms(hl_interval))
        data = await self._post_info(
            {"type": "candleSnapshot", "coin": symbol.upper(), "interval": hl_interval, "startTime": start_ms, "endTime": now_ms}
        )
        candles: list[Candle] = []
        for row in (data or {}).get("t", {}).get(symbol.upper(), []):
            candles.append(
                Candle(
                    symbol=symbol.upper(),
                    interval=interval,
                    open=Decimal(str(row.get("o", "0"))),
                    high=Decimal(str(row.get("h", "0"))),
                    low=Decimal(str(row.get("l", "0"))),
                    close=Decimal(str(row.get("c", "0"))),
                    volume=Decimal(str(row.get("v", "0"))),
                    timestamp=datetime.fromtimestamp(int(row.get("t", "0")) / 1000, tz=UTC),
                )
            )
        return candles

    async def get_trades(self, symbol: str, limit: int = 100) -> list[TradeEntry]:
        data = await self._post_info(
            {"type": "userFills", "user": self._wallet_address}
        )
        trades: list[TradeEntry] = []
        if not data:
            return trades
        for fill in data.get("fills", []):
            if fill.get("coin") != symbol.upper():
                continue
            trades.append(
                TradeEntry(
                    trade_id=str(fill.get("tid", "")),
                    order_id=str(fill.get("oid", "")),
                    symbol=symbol.upper(),
                    side=fill.get("side", "").lower(),
                    quantity=Decimal(str(fill.get("sz", "0"))),
                    price=Decimal(str(fill.get("px", "0"))),
                    fee=Decimal(str(fill.get("fee", "0"))),
                    fee_currency="USDC",
                    timestamp=datetime.fromtimestamp(int(fill.get("time", "0")) / 1000, tz=UTC),
                )
            )
        return trades[:limit]

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
        upper = symbol.upper()
        order_type_hl = "trigger" if order_type.lower() == "stop_limit" else "limit" if price else "ioc"

        order_data: dict[str, Any] = {
            "coin": upper,
            "isBuy": side.lower() == "buy",
            "sz": str(quantity),
            "limitPx": str(price) if price else "0",
            "orderType": {"limit": "limit", "ioc": "ioc", "alo": "alo"}.get(order_type_hl, "limit"),
            "reduceOnly": kwargs.get("reduce_only", False),
        }
        if kwargs.get("client_order_id"):
            order_data["cloid"] = kwargs["client_order_id"]

        # For production, this would sign with the wallet private key.
        # The actual signing requires eth_account library.
        # For now, we construct the action and log a warning.
        action = {
            "type": "order",
            "orders": [order_data],
            "grouping": "na",
        }

        logger.warning(
            "Hyperliquid place_order requires EIP-712 signing with wallet private key. "
            "Ensure eth_account is installed and signing is configured."
        )

        response = await self._post_action(action)
        status_val = response.get("status", "err") if response else "err"
        resting_oid = response.get("resting", {}).get("oid", "") if response else ""

        return OrderResult(
            order_id=kwargs.get("client_order_id", ""),
            exchange_order_id=str(resting_oid),
            symbol=upper,
            side=side.lower(),
            order_type=order_type.lower(),
            quantity=quantity,
            price=price,
            filled_quantity=Decimal("0"),
            average_fill_price=None,
            status="open" if status_val == "ok" else "rejected",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            error_message=None if status_val == "ok" else f"Hyperliquid order error: {status_val}",
        )

    async def cancel_order(self, symbol: str, order_id: str) -> OrderResult:
        action = {
            "type": "cancel",
            "cancels": [{"coin": symbol.upper(), "oid": int(order_id)}],
        }
        await self._post_action(action)
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
        open_orders = await self.get_open_orders(symbol)
        results: list[OrderResult] = []
        for o in open_orders:
            results.append(await self.cancel_order(o.symbol, o.exchange_order_id))
        return results

    async def get_order(self, symbol: str, order_id: str) -> OrderResult:
        orders = await self.get_open_orders(symbol)
        for o in orders:
            if o.exchange_order_id == order_id:
                return o
        raise OrderNotFound(order_id)

    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        data = await self._post_info(
            {"type": "openOrders", "user": self._wallet_address}
        )
        results: list[OrderResult] = []
        if not data:
            return results
        for o in data:
            if symbol and o.get("coin") != symbol.upper():
                continue
            results.append(
                OrderResult(
                    order_id=str(o.get("cloid", "")),
                    exchange_order_id=str(o.get("oid", "")),
                    symbol=o.get("coin", ""),
                    side="buy" if o.get("side", "").lower() == "b" else "sell",
                    order_type="limit",
                    quantity=Decimal(str(o.get("sz", "0"))),
                    price=Decimal(str(o.get("limitPx", "0"))),
                    filled_quantity=Decimal(str(o.get("origSz", "0"))) - Decimal(str(o.get("sz", "0"))),
                    average_fill_price=None,
                    status="open",
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )
        return results

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
                sub_msg = {"method": "subscribe", "subscription": {"type": "allMids"}}
                self._ticker_callbacks[upper] = callback
            elif channel == "orderbook":
                sub_msg = {"method": "subscribe", "subscription": {"type": "l2Book", "coin": upper}}
                self._orderbook_callbacks[upper] = callback
            else:
                sub_msg = {"method": "subscribe", "subscription": {"type": channel, "coin": upper}}
            await self.ws.subscribe(json.dumps(sub_msg))
        return True

    async def subscribe_account(
        self, channel: str, callback: Callable[[Any], None]
    ) -> bool:
        if not self.ws_account.is_connected:
            await self.connect_account()
        self._user_data_callback = callback
        sub_msg = {"method": "subscribe", "subscription": {"type": "userFills", "user": self._wallet_address}}
        await self.ws_account.subscribe(json.dumps(sub_msg))
        return True

    async def unsubscribe_market(self, symbols: list[str], channel: str) -> bool:
        for symbol in symbols:
            upper = symbol.upper()
            if channel == "ticker":
                self._ticker_callbacks.pop(upper, None)
                unsub_msg = {"method": "unsubscribe", "subscription": {"type": "allMids"}}
            elif channel == "orderbook":
                self._orderbook_callbacks.pop(upper, None)
                unsub_msg = {"method": "unsubscribe", "subscription": {"type": "l2Book", "coin": upper}}
            else:
                unsub_msg = {"method": "unsubscribe", "subscription": {"type": channel, "coin": upper}}
            await self.ws.unsubscribe(json.dumps(unsub_msg))
        return True

    async def unsubscribe_account(self, channel: str) -> bool:
        self._user_data_callback = None
        return True

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------
    async def _post_info(self, req_body: dict[str, Any]) -> dict[str, Any] | None:
        """POST to /info endpoint for market data and account queries."""
        response = await self.http.post("/info", json=req_body)
        self._raise_for_status(response)
        try:
            data = response.json()
            return data if isinstance(data, dict) else {"data": data}
        except Exception as exc:
            raise ExchangeError("Invalid JSON from Hyperliquid", self.name) from exc

    async def _post_action(self, action: dict[str, Any]) -> dict[str, Any] | None:
        """POST to /exchange endpoint for trading actions.

        NOTE: In production, the action must be signed with the wallet's
        private key using EIP-712 typed data. This method sends the raw
        action — signing must be added before production use.
        """
        body = {"action": action, "nonce": int(time.time() * 1000)}
        response = await self.http.post("/exchange", json=body)
        self._raise_for_status(response)
        try:
            return response.json()
        except Exception as exc:
            raise ExchangeError("Invalid JSON from Hyperliquid", self.name) from exc

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        try:
            body = response.json()
        except Exception:
            body = {}

        msg = body.get("response", body.get("error", body.get("msg", "")))
        status = response.status_code

        if status == 429:
            raise ExchangeRateLimitError(f"Hyperliquid rate limit: {msg}", self.name)
        if status in (401, 403):
            raise AuthenticationError(f"Hyperliquid auth error: {msg}")
        if status >= 500:
            raise ExchangeConnectionError(f"Hyperliquid server error {status}: {msg}", self.name)

        raise ExchangeError(f"Hyperliquid HTTP {status}: {msg}", self.name)

    @staticmethod
    def _interval_to_ms(interval: str) -> int:
        mapping = {
            "1m": 60_000, "5m": 300_000, "15m": 900_000,
            "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000,
        }
        return mapping.get(interval, 60_000)

    def _dispatch(self, message: Any) -> None:
        if not isinstance(message, str):
            return
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return
        if not isinstance(data, dict):
            return

        channel = data.get("channel", "")
        if channel == "allMids":
            for sym, cb in self._ticker_callbacks.items():
                if cb:
                    cb(data)
        elif channel == "l2Book":
            coin = data.get("data", {}).get("coin", "").upper()
            cb = self._orderbook_callbacks.get(coin)
            if cb:
                cb(data)
        elif channel == "userFills":
            if self._user_data_callback:
                self._user_data_callback(data)
        else:
            logger.debug(f"Unhandled Hyperliquid WebSocket message: {data}")


# Register adapter automatically when module is imported.
ExchangeFactory.register("hyperliquid", HyperliquidAdapter)
