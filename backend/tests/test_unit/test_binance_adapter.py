"""Unit tests for Binance Spot Adapter and Exchange Certification — Sprint 4."""

import asyncio
import hashlib
import hmac
import json
import time
import urllib.parse
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import websockets

from core.exceptions import (
    AuthenticationError,
    ExchangeConnectionError,
    ExchangeError,
    ExchangeRateLimitError,
    InsufficientBalanceError,
    OrderNotFound,
    SymbolNotSupported,
    TimeoutError,
)
from core.types import (
    ExchangeAdapterConfig,
    ExchangeCredentials,
    OrderResult,
)
from exchanges.adapters.binance import BinanceAuthenticator, BinanceSpotAdapter
from exchanges.factory import ExchangeFactory
from exchanges.websocket_manager import WebSocketManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def response_200(data: Any) -> httpx.Response:
    return httpx.Response(200, json=data)


def response_error(status: int, code: int, msg: str) -> httpx.Response:
    return httpx.Response(status, json={"code": code, "msg": msg})


def expected_signature(secret: str, params: dict[str, Any]) -> str:
    """Recreate the Binance signature exactly as the adapter does."""
    without = {k: v for k, v in params.items() if k != "signature"}
    query = urllib.parse.urlencode(sorted(without.items()), doseq=True)
    return hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()


@pytest.fixture
def http_client():
    client = MagicMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.delete = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def ws_manager():
    ws = MagicMock()
    ws.connect = AsyncMock(return_value=True)
    ws.disconnect = AsyncMock()
    ws.subscribe = AsyncMock()
    ws.unsubscribe = AsyncMock()
    ws.send_json = AsyncMock()
    ws.send_text = AsyncMock()
    ws.register_callback = MagicMock()
    ws.is_connected = False
    return ws


@pytest.fixture
def ws_account_manager():
    ws = MagicMock()
    ws.connect = AsyncMock(return_value=True)
    ws.disconnect = AsyncMock()
    ws.subscribe = AsyncMock()
    ws.unsubscribe = AsyncMock()
    ws.send_json = AsyncMock()
    ws.send_text = AsyncMock()
    ws.register_callback = MagicMock()
    ws.is_connected = False
    return ws


@pytest.fixture
def config():
    return ExchangeAdapterConfig(
        exchange_name="binance",
        is_testnet=True,
        request_timeout=5.0,
        recv_window=5000,
    )


@pytest.fixture
def credentials():
    return ExchangeCredentials(
        exchange_name="binance",
        api_key="test_key",
        api_secret="test_secret",
    )


@pytest.fixture
def adapter(http_client, ws_manager, ws_account_manager):
    return BinanceSpotAdapter(
        http_client=http_client,
        ws_manager=ws_manager,
        ws_account_manager=ws_account_manager,
    )


# ---------------------------------------------------------------------------
# Construction and Factory
# ---------------------------------------------------------------------------


class TestBinanceAdapterConstruction:
    def test_factory_registration(self):
        assert ExchangeFactory.is_registered("binance")

    def test_factory_create_instance(self):
        adapter = ExchangeFactory.create("binance")
        assert isinstance(adapter, BinanceSpotAdapter)

    def test_default_instantiation(self):
        adapter = BinanceSpotAdapter()
        assert isinstance(adapter.authenticator, BinanceAuthenticator)

    def test_injected_dependencies(self, adapter):
        assert adapter.http is not None
        assert adapter.ws is not None


# ---------------------------------------------------------------------------
# BinanceAuthenticator
# ---------------------------------------------------------------------------


class TestBinanceAuthenticator:
    def test_sign(self):
        auth = BinanceAuthenticator(api_key="k", api_secret="s")
        signature = auth.sign("a=1&b=2")
        expected = hmac.new("s".encode(), b"a=1&b=2", hashlib.sha256).hexdigest()
        assert signature == expected

    def test_auth_headers(self):
        auth = BinanceAuthenticator(api_key="k", api_secret="s")
        assert auth.auth_headers()["X-MBX-APIKEY"] == "k"

    def test_timestamp_uses_offset(self):
        auth = BinanceAuthenticator()
        auth.update_time_offset(2000, 1000)
        before = int(time.time() * 1000)
        ts = auth.timestamp()
        after = int(time.time() * 1000)
        assert before + 1000 <= ts <= after + 1000

    def test_set_credentials(self):
        auth = BinanceAuthenticator()
        auth.set_credentials("k", "s")
        assert auth.api_key == "k"
        assert auth.api_secret == "s"


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestBinanceLifecycle:
    async def test_initialize_sets_urls(self, adapter, config):
        result = await adapter.initialize(config)
        assert result is True
        assert adapter.rest_url == "https://testnet.binance.vision"
        assert adapter.ws_url == "wss://testnet.binance.vision/ws"

    async def test_initialize_mainnet(self, adapter):
        config = ExchangeAdapterConfig(exchange_name="binance", is_testnet=False)
        await adapter.initialize(config)
        assert adapter.rest_url == "https://api.binance.com"
        assert adapter.ws_url == "wss://stream.binance.com:9443/ws"

    async def test_authenticate_syncs_time_and_checks_account(self, adapter, config, credentials):
        await adapter.initialize(config)
        adapter.http.get = AsyncMock(side_effect=[
            response_200({"serverTime": 1000}),
            response_200({"accountType": "SPOT"}),
        ])

        with patch("time.time", return_value=0.5):
            result = await adapter.authenticate(credentials)

        assert result is True
        assert adapter.authenticator.api_key == "test_key"
        assert adapter.authenticator._time_offset_ms == 1000 - 500

        assert adapter.http.get.await_count == 2
        time_call, account_call = adapter.http.get.await_args_list
        assert time_call[0][0] == "/api/v3/time"
        assert account_call[0][0] == "/api/v3/account"
        assert "X-MBX-APIKEY" in account_call.kwargs["headers"]

    async def test_authenticate_failure_raises(self, adapter, config, credentials):
        await adapter.initialize(config)
        adapter.http.get = AsyncMock(side_effect=[
            response_200({"serverTime": 1000}),
            response_error(401, -2015, "Invalid API-key"),
        ])

        with pytest.raises(AuthenticationError):
            await adapter.authenticate(credentials)

    async def test_connect_market(self, adapter, config):
        await adapter.initialize(config)
        assert await adapter.connect_market() is True
        adapter.ws.connect.assert_awaited_once_with("wss://testnet.binance.vision/ws")

    async def test_connect_account(self, adapter, config, credentials):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials(credentials.api_key, credentials.api_secret)
        adapter.http.post = AsyncMock(return_value=response_200({"listenKey": "key123"}))
        assert await adapter.connect_account() is True
        adapter.ws_account.connect.assert_awaited_once_with("wss://testnet.binance.vision/ws/key123")

    async def test_disconnect(self, adapter, config):
        await adapter.initialize(config)
        await adapter.disconnect()
        adapter.ws.disconnect.assert_awaited_once()
        adapter.ws_account.disconnect.assert_awaited_once()
        adapter.http.close.assert_awaited_once()

    async def test_health_check(self, adapter, config):
        await adapter.initialize(config)
        adapter.http.get = AsyncMock(return_value=response_200({"serverTime": 1000}))
        assert await adapter.health_check() is True

    async def test_health_check_failure(self, adapter, config):
        await adapter.initialize(config)
        adapter.http.get = AsyncMock(return_value=response_error(500, -1000, "Internal"))
        assert await adapter.health_check() is False


# ---------------------------------------------------------------------------
# Signature and timestamp
# ---------------------------------------------------------------------------


class TestBinanceSignatureAndTimestamp:
    async def test_get_account_includes_signature_and_api_key(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.get = AsyncMock(return_value=response_200({"balances": []}))

        with patch("time.time", return_value=1000.0):
            await adapter.get_account()

        call = adapter.http.get.call_args
        assert call[0][0] == "/api/v3/account"
        assert call.kwargs["headers"]["X-MBX-APIKEY"] == "test_key"
        params = call.kwargs["params"]
        assert "timestamp" in params
        assert "signature" in params
        assert params["signature"] == expected_signature("test_secret", params)

    async def test_place_order_body_includes_signature(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.post = AsyncMock(return_value=response_200({"orderId": 1, "status": "NEW"}))

        with patch("time.time", return_value=1000.0):
            await adapter.place_order("BTCUSDT", "buy", "limit", Decimal("1"), Decimal("50000"))

        call = adapter.http.post.call_args
        body = call.kwargs["content"]
        assert "X-MBX-APIKEY" in call.kwargs["headers"]
        assert "signature" in body
        assert "symbol=BTCUSDT" in body

    async def test_cancel_order_includes_signature(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.delete = AsyncMock(return_value=response_200({"orderId": 1, "status": "CANCELED"}))

        with patch("time.time", return_value=1000.0):
            await adapter.cancel_order("BTCUSDT", "123")

        call = adapter.http.delete.call_args
        params = call.kwargs["params"]
        assert params["signature"] == expected_signature("test_secret", params)

    async def test_timestamp_increases_with_offset(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.authenticator.update_time_offset(1_000_000, 0)
        adapter.http.get = AsyncMock(return_value=response_200({"balances": []}))

        with patch("time.time", return_value=1.0):
            await adapter.get_account()

        call = adapter.http.get.call_args
        params = call.kwargs["params"]
        assert params["timestamp"] == 1_001_000

    async def test_get_account_includes_default_recv_window(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.get = AsyncMock(return_value=response_200({"balances": []}))

        with patch("time.time", return_value=1000.0):
            await adapter.get_account()

        params = adapter.http.get.call_args.kwargs["params"]
        assert params["recvWindow"] == 5000

    async def test_custom_recv_window_from_config(self, adapter):
        config = ExchangeAdapterConfig(
            exchange_name="binance", is_testnet=True, recv_window=10000
        )
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.get = AsyncMock(return_value=response_200({"balances": []}))

        with patch("time.time", return_value=1000.0):
            await adapter.get_account()

        assert adapter.http.get.call_args.kwargs["params"]["recvWindow"] == 10000

    async def test_unauthenticated_call_raises(self, adapter, config):
        await adapter.initialize(config)
        with pytest.raises(AuthenticationError):
            await adapter.get_account()


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------


class TestBinanceErrorMapping:
    @pytest.mark.parametrize(
        "status,code,msg,expected",
        [
            (429, -1003, "Rate limit", ExchangeRateLimitError),
            (418, -1000, "IP ban", ExchangeRateLimitError),
            (401, -1022, "Invalid signature", AuthenticationError),
            (401, -2014, "API key invalid", AuthenticationError),
            (401, -2015, "Rejected API key", AuthenticationError),
            (400, -2013, "Order does not exist", OrderNotFound),
            (400, -2010, "Account has insufficient balance", InsufficientBalanceError),
            (400, -2010, "Order rejected", ExchangeError),
            (400, -1021, "Timestamp outside recvWindow", ExchangeError),
            (400, -1120, "Invalid symbol", SymbolNotSupported),
            (500, -1000, "Server error", ExchangeConnectionError),
            (400, -9999, "Unknown", ExchangeError),
        ],
    )
    async def test_error_mapping(self, adapter, config, status, code, msg, expected):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.get = AsyncMock(return_value=response_error(status, code, msg))

        with pytest.raises(expected):
            await adapter.get_account()

    async def test_network_timeout_raises(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.get = AsyncMock(side_effect=TimeoutError("Request timed out"))

        with pytest.raises(TimeoutError):
            await adapter.get_account()


class TestBinanceTimestampResync:
    async def test_auto_resync_on_timestamp_drift(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.get = AsyncMock(side_effect=[
            response_error(400, -1021, "Timestamp outside recvWindow"),
            response_200({"serverTime": 2_000}),
            response_200({"balances": [{"asset": "BTC", "free": "1", "locked": "0"}]}),
        ])

        with patch("time.time", return_value=1000.0):
            result = await adapter.get_account()

        assert result["balances"][0]["asset"] == "BTC"
        assert adapter.http.get.await_count == 3
        calls = adapter.http.get.await_args_list
        assert calls[0][0][0] == "/api/v3/account"
        assert calls[1][0][0] == "/api/v3/time"
        assert calls[2][0][0] == "/api/v3/account"

    async def test_timestamp_drift_persists_after_resync(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        # /api/v3/time succeeds, but /api/v3/account keeps returning -1021.
        adapter.http.get = AsyncMock(side_effect=[
            response_error(400, -1021, "Timestamp outside recvWindow"),
            response_200({"serverTime": 2_000}),
            response_error(400, -1021, "Timestamp outside recvWindow"),
        ])

        with pytest.raises(ExchangeError):
            await adapter.get_account()


# ---------------------------------------------------------------------------
# Account and exchange info
# ---------------------------------------------------------------------------


class TestBinanceAccount:
    async def test_get_account(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.get = AsyncMock(return_value=response_200({
            "accountType": "SPOT",
            "balances": [
                {"asset": "BTC", "free": "1.5", "locked": "0.5"},
                {"asset": "USDT", "free": "100.0", "locked": "0.0"},
            ],
        }))

        result = await adapter.get_account()
        assert result["accountType"] == "SPOT"
        assert len(result["balances"]) == 2

    async def test_get_balance(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.get = AsyncMock(return_value=response_200({
            "balances": [
                {"asset": "BTC", "free": "1.5", "locked": "0.5"},
                {"asset": "USDT", "free": "100.0", "locked": "0.0"},
            ],
        }))

        balances = await adapter.get_balance()
        assert len(balances) == 2
        assert balances[0].currency == "BTC"
        assert balances[0].available == Decimal("1.5")
        assert balances[0].locked == Decimal("0.5")
        assert balances[0].total == Decimal("2.0")

    async def test_get_balance_filtered(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.get = AsyncMock(return_value=response_200({
            "balances": [
                {"asset": "BTC", "free": "1.5", "locked": "0.5"},
                {"asset": "USDT", "free": "100.0", "locked": "0.0"},
            ],
        }))

        balances = await adapter.get_balance("usdt")
        assert len(balances) == 1
        assert balances[0].currency == "USDT"

    async def test_get_exchange_info(self, adapter, config):
        await adapter.initialize(config)
        adapter.http.get = AsyncMock(return_value=response_200({
            "serverTime": 1_000_000,
            "symbols": [
                {"symbol": "BTCUSDT", "status": "TRADING"},
                {"symbol": "ETHUSDT", "status": "TRADING"},
            ],
            "rateLimits": [{"rateLimitType": "REQUEST_WEIGHT", "limit": 1200}],
        }))

        info = await adapter.get_exchange_info()
        assert info.name == "binance"
        assert "BTCUSDT" in info.supported_symbols
        assert info.rate_limits

    async def test_get_symbol_info(self, adapter, config):
        await adapter.initialize(config)
        adapter.http.get = AsyncMock(return_value=response_200({
            "symbols": [
                {"symbol": "BTCUSDT", "status": "TRADING", "filters": []},
            ],
        }))

        symbol = await adapter.get_symbol_info("BTCUSDT")
        assert symbol["symbol"] == "BTCUSDT"

    async def test_get_symbol_info_unknown(self, adapter, config):
        await adapter.initialize(config)
        adapter.http.get = AsyncMock(return_value=response_200({"symbols": []}))

        with pytest.raises(SymbolNotSupported):
            await adapter.get_symbol_info("MISSING")


# ---------------------------------------------------------------------------
# Market data
# ---------------------------------------------------------------------------


class TestBinanceMarketData:
    async def test_get_ticker(self, adapter, config):
        await adapter.initialize(config)
        adapter.http.get = AsyncMock(side_effect=[
            response_200({"bidPrice": "50000.0", "askPrice": "50001.0", "bidQty": "1", "askQty": "1"}),
            response_200({"lastPrice": "50000.5", "volume": "100.0", "closeTime": 1_000_000}),
        ])

        ticker = await adapter.get_ticker("BTCUSDT")
        assert ticker.symbol == "BTCUSDT"
        assert ticker.bid == Decimal("50000.0")
        assert ticker.ask == Decimal("50001.0")
        assert ticker.last == Decimal("50000.5")
        assert ticker.volume == Decimal("100.0")

    async def test_get_order_book(self, adapter, config):
        await adapter.initialize(config)
        adapter.http.get = AsyncMock(return_value=response_200({
            "lastUpdateId": 100,
            "bids": [["50000.0", "1.0"], ["49999.0", "2.0"]],
            "asks": [["50001.0", "1.0"], ["50002.0", "2.0"]],
        }))

        book = await adapter.get_order_book("BTCUSDT", 5)
        assert book.symbol == "BTCUSDT"
        assert len(book.bids) == 2
        assert book.bids[0] == (Decimal("50000.0"), Decimal("1.0"))
        assert len(book.asks) == 2

    async def test_get_candles(self, adapter, config):
        await adapter.initialize(config)
        adapter.http.get = AsyncMock(return_value=response_200([
            [1_000_000, "50000", "51000", "49000", "50500", "100"],
            [1_008_000, "50500", "51500", "50000", "51000", "200"],
        ]))

        candles = await adapter.get_candles("BTCUSDT", "1m", 2)
        assert len(candles) == 2
        assert candles[0].symbol == "BTCUSDT"
        assert candles[0].open == Decimal("50000")
        assert candles[0].high == Decimal("51000")
        assert candles[0].low == Decimal("49000")
        assert candles[0].close == Decimal("50500")
        assert candles[0].volume == Decimal("100")

    async def test_get_trades(self, adapter, config):
        await adapter.initialize(config)
        adapter.http.get = AsyncMock(return_value=response_200([
            {"id": 1, "price": "50000", "qty": "1", "time": 1_000_000, "isBuyerMaker": True},
            {"id": 2, "price": "50001", "qty": "2", "time": 1_000_001, "isBuyerMaker": False},
        ]))

        trades = await adapter.get_trades("BTCUSDT", 2)
        assert len(trades) == 2
        assert trades[0].trade_id == "1"
        assert trades[0].side == "sell"
        assert trades[1].side == "buy"


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


class TestBinanceOrders:
    def order_response(self, order_id: int = 123, status: str = "NEW") -> dict[str, Any]:
        return {
            "orderId": order_id,
            "clientOrderId": "cid-123",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "type": "LIMIT",
            "origQty": "1.0",
            "price": "50000.0",
            "executedQty": "0.0",
            "cummulativeQuoteQty": "0.0",
            "status": status,
            "time": 1_000_000,
            "updateTime": 1_000_000,
        }

    async def test_place_order(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.post = AsyncMock(return_value=response_200(self.order_response()))

        result = await adapter.place_order("BTCUSDT", "buy", "limit", Decimal("1"), Decimal("50000"))
        assert isinstance(result, OrderResult)
        assert result.exchange_order_id == "123"
        assert result.status == "open"

    async def test_place_market_order(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.post = AsyncMock(return_value=response_200(self.order_response()))

        result = await adapter.place_order("BTCUSDT", "buy", "market", Decimal("1"))
        body = adapter.http.post.call_args.kwargs["content"]
        assert "type=MARKET" in body
        assert "price" not in body

    async def test_get_order(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.get = AsyncMock(return_value=response_200(self.order_response(123, "FILLED")))

        result = await adapter.get_order("BTCUSDT", "123")
        assert result.exchange_order_id == "123"
        assert result.status == "filled"

    async def test_cancel_order(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.delete = AsyncMock(return_value=response_200(self.order_response(123, "CANCELED")))

        result = await adapter.cancel_order("BTCUSDT", "123")
        assert result.status == "cancelled"

    async def test_get_open_orders(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.get = AsyncMock(return_value=response_200([self.order_response(1), self.order_response(2)]))

        orders = await adapter.get_open_orders("BTCUSDT")
        assert len(orders) == 2
        assert orders[0].exchange_order_id == "1"

    async def test_cancel_all_with_symbol(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.delete = AsyncMock(return_value=response_200([self.order_response(1, "CANCELED"), self.order_response(2, "CANCELED")]))

        orders = await adapter.cancel_all("BTCUSDT")
        assert len(orders) == 2
        assert orders[0].status == "cancelled"

    async def test_cancel_all_without_symbol(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.get = AsyncMock(return_value=response_200([self.order_response(1), self.order_response(2)]))
        adapter.http.delete = AsyncMock(return_value=response_200(self.order_response(1, "CANCELED")))

        orders = await adapter.cancel_all()
        assert len(orders) == 2


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------


class TestBinanceWebSocket:
    async def test_subscribe_ticker_sends_subscribe_message(self, adapter, config):
        await adapter.initialize(config)
        await adapter.connect_market()

        callback = MagicMock()
        await adapter.subscribe_ticker("BTCUSDT", callback)

        adapter.ws.subscribe.assert_awaited_once()
        call = adapter.ws.subscribe.call_args[0][0]
        msg = json.loads(call)
        assert msg["method"] == "SUBSCRIBE"
        assert "btcusdt@ticker" in msg["params"]

    async def test_subscribe_orderbook_sends_subscribe_message(self, adapter, config):
        await adapter.initialize(config)
        await adapter.connect_market()

        callback = MagicMock()
        await adapter.subscribe_orderbook("BTCUSDT", callback)

        call = adapter.ws.subscribe.call_args[0][0]
        msg = json.loads(call)
        assert "btcusdt@depth" in msg["params"]

    async def test_subscribe_ticker_connects_if_not_connected(self, adapter, config):
        await adapter.initialize(config)
        await adapter.subscribe_ticker("BTCUSDT", MagicMock())
        adapter.ws.connect.assert_awaited_with(adapter.ws_url)

    async def test_unsubscribe_ticker_sends_unsubscribe(self, adapter, config):
        await adapter.initialize(config)
        await adapter.connect_market()

        callback = MagicMock()
        await adapter.subscribe_ticker("BTCUSDT", callback)
        await adapter.unsubscribe_ticker("BTCUSDT")

        adapter.ws.unsubscribe.assert_awaited_once()
        call = adapter.ws.unsubscribe.call_args[0][0]
        msg = json.loads(call)
        assert msg["method"] == "UNSUBSCRIBE"

    async def test_subscribe_user_data(self, adapter, config, credentials):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials(credentials.api_key, credentials.api_secret)
        adapter.http.post = AsyncMock(return_value=response_200({"listenKey": "lk"}))

        callback = MagicMock()
        await adapter.subscribe_user_data(callback)

        adapter.ws_account.connect.assert_awaited_with("wss://testnet.binance.vision/ws/lk")
        assert adapter._user_data_callback is callback

    async def test_market_and_user_stream_use_separate_websocket_managers(self, adapter, config, credentials):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials(credentials.api_key, credentials.api_secret)
        adapter.http.post = AsyncMock(return_value=response_200({"listenKey": "lk"}))

        await adapter.connect_market()
        await adapter.connect_account()

        assert adapter.ws is not adapter.ws_account
        adapter.ws.connect.assert_awaited_once_with(adapter.ws_url)
        adapter.ws_account.connect.assert_awaited_once_with(f"{adapter.ws_url}/lk")

    async def test_subscribe_ticker_deduplicates(self, adapter, config):
        await adapter.initialize(config)
        real_ws = WebSocketManager()
        mock_ws = AsyncMock(spec=websockets.WebSocketClientProtocol)
        mock_ws.open = True
        real_ws._ws = mock_ws
        real_ws.url = adapter.ws_url
        adapter.ws = real_ws

        callback = MagicMock()
        await adapter.subscribe_ticker("BTCUSDT", callback)
        await adapter.subscribe_ticker("BTCUSDT", callback)

        assert mock_ws.send.await_count == 1

    async def test_subscribe_orderbook_different_channel_not_duplicate(self, adapter, config):
        await adapter.initialize(config)
        real_ws = WebSocketManager()
        mock_ws = AsyncMock(spec=websockets.WebSocketClientProtocol)
        mock_ws.open = True
        real_ws._ws = mock_ws
        real_ws.url = adapter.ws_url
        adapter.ws = real_ws

        await adapter.subscribe_ticker("BTCUSDT", MagicMock())
        await adapter.subscribe_orderbook("BTCUSDT", MagicMock())

        assert mock_ws.send.await_count == 2

    async def test_dispatch_ticker_calls_callback(self, adapter, config):
        await adapter.initialize(config)
        callback = MagicMock()
        adapter._ticker_callbacks["BTCUSDT"] = callback
        adapter._dispatch(json.dumps({"e": "24hrTicker", "s": "BTCUSDT"}))
        callback.assert_called_once()

    async def test_dispatch_orderbook_calls_callback(self, adapter, config):
        await adapter.initialize(config)
        callback = MagicMock()
        adapter._orderbook_callbacks["BTCUSDT"] = callback
        adapter._dispatch(json.dumps({"e": "depthUpdate", "s": "BTCUSDT"}))
        callback.assert_called_once()

    async def test_dispatch_user_data_calls_callback(self, adapter, config):
        await adapter.initialize(config)
        callback = MagicMock()
        adapter._user_data_callback = callback
        adapter._dispatch(json.dumps({"e": "outboundAccountPosition"}))
        callback.assert_called_once()

    async def test_dispatch_unhandled_is_ignored(self, adapter, config):
        await adapter.initialize(config)
        adapter._dispatch(json.dumps({"e": "unknown"}))


# ---------------------------------------------------------------------------
# Exchange Certification
# ---------------------------------------------------------------------------


class TestBinanceCertification:
    async def test_rest_api_success(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.get = AsyncMock(return_value=response_200({"serverTime": 1_000_000}))
        assert await adapter.health_check() is True

    async def test_websocket_success(self, adapter, config):
        await adapter.initialize(config)
        await adapter.connect_market()
        adapter.ws.connect.assert_awaited_once()

    async def test_reconnect_success(self, adapter, config):
        await adapter.initialize(config)
        await adapter.connect_market()
        adapter.ws.is_connected = False
        await adapter.connect_market()
        assert adapter.ws.connect.await_count == 2

    async def test_cancel_order_success(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.delete = AsyncMock(return_value=response_200({
            "orderId": 1, "clientOrderId": "cid", "symbol": "BTCUSDT",
            "side": "BUY", "type": "LIMIT", "origQty": "1", "price": "50000",
            "executedQty": "0", "cummulativeQuoteQty": "0", "status": "CANCELED",
            "time": 1_000_000, "updateTime": 1_000_000,
        }))
        result = await adapter.cancel_order("BTCUSDT", "1")
        assert result.status == "cancelled"

    async def test_rate_limit_handling(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.get = AsyncMock(return_value=response_error(429, -1003, "Rate limit"))
        with pytest.raises(ExchangeRateLimitError):
            await adapter.get_account()

    async def test_error_mapping_correctness(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.get = AsyncMock(return_value=response_error(401, -1022, "Invalid signature"))
        with pytest.raises(AuthenticationError):
            await adapter.get_account()

    async def test_network_timeout_handling(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.get = AsyncMock(side_effect=TimeoutError("timeout"))
        with pytest.raises(TimeoutError):
            await adapter.get_account()

    async def test_api_key_invalid(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.get = AsyncMock(return_value=response_error(401, -2014, "API key invalid"))
        with pytest.raises(AuthenticationError):
            await adapter.get_account()

    async def test_timestamp_drift_handling(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.get = AsyncMock(return_value=response_error(400, -1021, "Timestamp drift"))
        with pytest.raises(ExchangeError):
            await adapter.get_account()

    async def test_signature_invalid_handling(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.get = AsyncMock(return_value=response_error(400, -1022, "Invalid signature"))
        with pytest.raises(AuthenticationError):
            await adapter.get_account()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestBinanceEdgeCases:
    async def test_initialize_custom_urls(self, adapter):
        config = ExchangeAdapterConfig(
            exchange_name="binance",
            is_testnet=False,
            rest_url="https://custom.binance.com",
            market_stream_url="wss://custom.binance.com/ws",
        )
        await adapter.initialize(config)
        assert adapter.rest_url == "https://custom.binance.com"
        assert adapter.ws_url == "wss://custom.binance.com/ws"

    async def test_order_result_filled_computes_avg_price(self, adapter, config):
        await adapter.initialize(config)
        adapter.authenticator.set_credentials("test_key", "test_secret")
        adapter.http.post = AsyncMock(return_value=response_200({
            "orderId": 1, "clientOrderId": "cid", "symbol": "BTCUSDT",
            "side": "BUY", "type": "LIMIT", "origQty": "2", "price": "50000",
            "executedQty": "2", "cummulativeQuoteQty": "100000",
            "status": "FILLED", "time": 1_000_000, "updateTime": 1_000_000,
        }))
        result = await adapter.place_order("BTCUSDT", "buy", "limit", Decimal("2"), Decimal("50000"))
        assert result.average_fill_price == Decimal("50000")

    async def test_exchange_info_caches(self, adapter, config):
        await adapter.initialize(config)
        adapter.http.get = AsyncMock(return_value=response_200({
            "serverTime": 1_000_000,
            "symbols": [{"symbol": "BTCUSDT"}],
        }))
        await adapter.get_exchange_info()
        await adapter.get_exchange_info()
        assert adapter.http.get.await_count == 1

    async def test_get_positions_returns_empty(self, adapter, config):
        await adapter.initialize(config)
        positions = await adapter.get_positions()
        assert positions == []
