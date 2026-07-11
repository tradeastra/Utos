"""
Unit tests for Sprint 3 infrastructure exchange layer.

Tests are independent and do not make real network calls.
"""

import asyncio
import json
import uuid
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest
import websockets

from core.exceptions import (
    AuthenticationError,
    ExchangeConnectionError,
    ExchangeError,
    ExchangeRateLimitError,
    TimeoutError,
)
from core.types import (
    ExchangeAdapterConfig,
    ExchangeCredentials,
)
from exchanges.adapter import IExchangeAdapter
from exchanges.credential_manager import CredentialManager
from exchanges.errors import ErrorMapper
from exchanges.factory import ExchangeFactory
from exchanges.http_client import HttpClient
from exchanges.rate_limiter import RateLimiter, RateLimitConfig
from exchanges.retry import RetryPolicy
from exchanges.websocket_manager import WebSocketManager


# -----------------------------------------------------------------------------
# IExchangeAdapter
# -----------------------------------------------------------------------------

class TestIExchangeAdapter:
    def test_instantiating_abstract_adapter_raises(self):
        with pytest.raises(TypeError):
            IExchangeAdapter()

    def test_methods_are_abstract(self):
        missing = {
            "initialize",
            "authenticate",
            "connect_market",
            "connect_account",
            "disconnect",
            "get_exchange_info",
            "get_balance",
            "get_account",
            "get_symbol_info",
            "get_positions",
            "place_order",
            "cancel_order",
            "cancel_all",
            "get_order",
            "get_open_orders",
            "get_ticker",
            "get_order_book",
            "get_candles",
            "get_trades",
            "health_check",
            "subscribe_market",
            "subscribe_account",
            "unsubscribe_market",
            "unsubscribe_account",
        }
        abstract = {m for m in dir(IExchangeAdapter) if getattr(IExchangeAdapter, m, None)}
        for m in missing:
            assert hasattr(IExchangeAdapter, m)


# -----------------------------------------------------------------------------
# ExchangeFactory
# -----------------------------------------------------------------------------

class TestExchangeFactory:
    def setup_method(self):
        ExchangeFactory.clear()

    def teardown_method(self):
        ExchangeFactory.clear()

    def test_register_and_create(self):
        class DummyAdapter(IExchangeAdapter):
            name = "dummy"

            async def initialize(self, config): return True
            async def authenticate(self, credentials): return True
            async def connect_market(self): return True
            async def connect_account(self): return True
            async def disconnect(self): pass
            async def get_exchange_info(self): return None
            async def get_balance(self, asset=None): return []
            async def get_account(self): return None
            async def get_symbol_info(self, symbol): return None
            async def get_positions(self, symbol=None): return []
            async def place_order(self, *args, **kwargs): return None
            async def cancel_order(self, symbol, order_id): return None
            async def cancel_all(self, symbol=None): return []
            async def get_order(self, symbol, order_id): return None
            async def get_open_orders(self, symbol=None): return []
            async def get_ticker(self, symbol): return None
            async def get_order_book(self, symbol, limit=100): return None
            async def get_candles(self, symbol, interval, limit=100): return []
            async def get_trades(self, symbol, limit=100): return []
            async def health_check(self): return True
            async def subscribe_market(self, symbols, channel, callback): return True
            async def subscribe_account(self, channel, callback): return True
            async def unsubscribe_market(self, symbols, channel): return True
            async def unsubscribe_account(self, channel): return True

        ExchangeFactory.register("dummy", DummyAdapter)
        adapter = ExchangeFactory.create("dummy")
        assert isinstance(adapter, DummyAdapter)
        assert adapter.name == "dummy"

    def test_create_unknown_raises(self):
        with pytest.raises(ValueError):
            ExchangeFactory.create("missing")

    def test_is_registered(self):
        class DummyAdapter(IExchangeAdapter):
            async def initialize(self, config): return True
            async def authenticate(self, credentials): return True
            async def connect_market(self): return True
            async def connect_account(self): return True
            async def disconnect(self): pass
            async def get_exchange_info(self): return None
            async def get_balance(self, asset=None): return []
            async def get_account(self): return None
            async def get_symbol_info(self, symbol): return None
            async def get_positions(self, symbol=None): return []
            async def place_order(self, *args, **kwargs): return None
            async def cancel_order(self, symbol, order_id): return None
            async def cancel_all(self, symbol=None): return []
            async def get_order(self, symbol, order_id): return None
            async def get_open_orders(self, symbol=None): return []
            async def get_ticker(self, symbol): return None
            async def get_order_book(self, symbol, limit=100): return None
            async def get_candles(self, symbol, interval, limit=100): return []
            async def get_trades(self, symbol, limit=100): return []
            async def health_check(self): return True
            async def subscribe_market(self, symbols, channel, callback): return True
            async def subscribe_account(self, channel, callback): return True
            async def unsubscribe_market(self, symbols, channel): return True
            async def unsubscribe_account(self, channel): return True

        ExchangeFactory.register("dummy", DummyAdapter)
        assert ExchangeFactory.is_registered("dummy") is True
        assert ExchangeFactory.is_registered("other") is False

    def test_registered_exchanges_list(self):
        class DummyAdapter(IExchangeAdapter):
            async def initialize(self, config): return True
            async def authenticate(self, credentials): return True
            async def connect_market(self): return True
            async def connect_account(self): return True
            async def disconnect(self): pass
            async def get_exchange_info(self): return None
            async def get_balance(self, asset=None): return []
            async def get_account(self): return None
            async def get_symbol_info(self, symbol): return None
            async def get_positions(self, symbol=None): return []
            async def place_order(self, *args, **kwargs): return None
            async def cancel_order(self, symbol, order_id): return None
            async def cancel_all(self, symbol=None): return []
            async def get_order(self, symbol, order_id): return None
            async def get_open_orders(self, symbol=None): return []
            async def get_ticker(self, symbol): return None
            async def get_order_book(self, symbol, limit=100): return None
            async def get_candles(self, symbol, interval, limit=100): return []
            async def get_trades(self, symbol, limit=100): return []
            async def health_check(self): return True
            async def subscribe_market(self, symbols, channel, callback): return True
            async def subscribe_account(self, channel, callback): return True
            async def unsubscribe_market(self, symbols, channel): return True
            async def unsubscribe_account(self, channel): return True

        ExchangeFactory.register("binance", DummyAdapter)
        ExchangeFactory.register("bybit", DummyAdapter)
        assert set(ExchangeFactory.registered_exchanges()) == {"binance", "bybit"}

    def test_create_case_insensitive(self):
        class DummyAdapter(IExchangeAdapter):
            name = "Dummy"

            async def initialize(self, config): return True
            async def authenticate(self, credentials): return True
            async def connect_market(self): return True
            async def connect_account(self): return True
            async def disconnect(self): pass
            async def get_exchange_info(self): return None
            async def get_balance(self, asset=None): return []
            async def get_account(self): return None
            async def get_symbol_info(self, symbol): return None
            async def get_positions(self, symbol=None): return []
            async def place_order(self, *args, **kwargs): return None
            async def cancel_order(self, symbol, order_id): return None
            async def cancel_all(self, symbol=None): return []
            async def get_order(self, symbol, order_id): return None
            async def get_open_orders(self, symbol=None): return []
            async def get_ticker(self, symbol): return None
            async def get_order_book(self, symbol, limit=100): return None
            async def get_candles(self, symbol, interval, limit=100): return []
            async def get_trades(self, symbol, limit=100): return []
            async def health_check(self): return True
            async def subscribe_market(self, symbols, channel, callback): return True
            async def subscribe_account(self, channel, callback): return True
            async def unsubscribe_market(self, symbols, channel): return True
            async def unsubscribe_account(self, channel): return True

        ExchangeFactory.register("Dummy", DummyAdapter)
        assert ExchangeFactory.is_registered("dummy")
        assert ExchangeFactory.create("DUMMY").name == "DUMMY"


# -----------------------------------------------------------------------------
# ErrorMapper
# -----------------------------------------------------------------------------

class TestErrorMapper:
    def test_rate_limit_error(self):
        mapper = ErrorMapper("binance")
        err = mapper.map_http_error(429)
        assert isinstance(err, ExchangeRateLimitError)
        assert err.exchange_name == "binance"
        assert err.error_code == "RATE_LIMIT"

    def test_server_error(self):
        mapper = ErrorMapper("bybit")
        err = mapper.map_http_error(503)
        assert isinstance(err, ExchangeConnectionError)
        assert err.error_code == "SERVER_ERROR"

    def test_client_error(self):
        mapper = ErrorMapper("okx")
        err = mapper.map_http_error(400, body={"code": "1"})
        assert isinstance(err, ExchangeError)
        assert err.error_code == "HTTP_ERROR"

    def test_custom_message(self):
        mapper = ErrorMapper("mexc")
        err = mapper.map_http_error(404, message="not found")
        assert err.message == "not found"

    def test_network_error(self):
        mapper = ErrorMapper("hyperliquid")
        err = mapper.map_network_error(Exception("timeout"))
        assert isinstance(err, ExchangeConnectionError)
        assert err.error_code == "NETWORK_ERROR"

    def test_websocket_error(self):
        mapper = ErrorMapper("binance")
        err = mapper.map_websocket_error(Exception("closed"))
        assert isinstance(err, ExchangeError)
        assert err.error_code == "WEBSOCKET_ERROR"


# -----------------------------------------------------------------------------
# CredentialManager
# -----------------------------------------------------------------------------

class TestCredentialManager:
    def test_encrypt_decrypt_roundtrip(self):
        manager = CredentialManager(secret_key="test_secret_32_bytes_long_key")
        plaintext = "my_api_secret_key"
        ciphertext = manager.encrypt(plaintext)
        assert ciphertext != plaintext
        assert manager.decrypt(ciphertext) == plaintext

    def test_different_keys_cannot_decrypt(self):
        manager1 = CredentialManager(secret_key="secret_one")
        manager2 = CredentialManager(secret_key="secret_two")
        ciphertext = manager1.encrypt("data")
        with pytest.raises(AuthenticationError):
            manager2.decrypt(ciphertext)

    def test_mask(self):
        manager = CredentialManager(secret_key="secret")
        assert manager.mask("abcdefghij", visible=3) == "*******hij"
        assert manager.mask("ab", visible=3) == "ab"

    def test_decrypt_invalid_token(self):
        manager = CredentialManager(secret_key="secret")
        with pytest.raises(AuthenticationError):
            manager.decrypt("not_a_valid_token")


# -----------------------------------------------------------------------------
# RateLimiter
# -----------------------------------------------------------------------------

class TestRateLimiter:
    async def test_acquire_immediately(self):
        limiter = RateLimiter()
        assert await limiter.acquire("api", 1.0) == 0.0

    async def test_configure_and_refill(self):
        limiter = RateLimiter()
        limiter.configure("api", RateLimitConfig(max_tokens=2.0, refill_rate=2.0))
        await limiter.acquire("api", 1.0)
        await limiter.acquire("api", 1.0)
        assert limiter.can_acquire("api", 1.0) is False

    async def test_acquire_waits_for_refill(self):
        limiter = RateLimiter()
        limiter.configure("api", RateLimitConfig(max_tokens=1.0, refill_rate=10.0))
        await limiter.acquire("api", 1.0)
        waited = await limiter.acquire("api", 1.0)
        assert waited >= 0.0

    def test_can_acquire(self):
        limiter = RateLimiter()
        limiter.configure("api", RateLimitConfig(max_tokens=5.0, refill_rate=5.0))
        assert limiter.can_acquire("api", 3.0) is True
        assert limiter.can_acquire("api", 10.0) is False

    async def test_exceed_capacity_raises(self):
        limiter = RateLimiter()
        limiter.configure("api", RateLimitConfig(max_tokens=1.0, refill_rate=1.0))
        with pytest.raises(ValueError):
            await limiter.acquire("api", 5.0)

    async def test_zero_tokens_returns_zero(self):
        limiter = RateLimiter()
        assert await limiter.acquire("api", 0.0) == 0.0

    def test_reset_all(self):
        limiter = RateLimiter()
        limiter.configure("api", RateLimitConfig(max_tokens=1.0, refill_rate=1.0))
        limiter.can_acquire("api", 1.0)
        limiter.reset()
        assert limiter.can_acquire("api", 1.0) is True

    def test_reset_endpoint(self):
        limiter = RateLimiter()
        limiter.configure("api", RateLimitConfig(max_tokens=1.0, refill_rate=1.0))
        limiter.can_acquire("api", 1.0)
        limiter.reset("api")
        assert limiter.can_acquire("api", 1.0) is True


# -----------------------------------------------------------------------------
# RetryPolicy
# -----------------------------------------------------------------------------

class TestRetryPolicy:
    def test_should_retry_until_max(self):
        policy = RetryPolicy(max_retries=3)
        assert policy.should_retry(1) is True
        assert policy.should_retry(2) is True
        assert policy.should_retry(3) is False

    def test_should_retry_exception_type(self):
        policy = RetryPolicy(retryable_exceptions=(ValueError,))
        assert policy.should_retry(1, ValueError("bad")) is True
        assert policy.should_retry(1, TypeError("bad")) is False

    def test_should_retry_status(self):
        policy = RetryPolicy()
        assert policy.should_retry_status(500) is True
        assert policy.should_retry_status(200) is False

    def test_delay_grows_exponentially(self):
        policy = RetryPolicy(base_delay=1.0, exponential_base=2.0)
        assert policy.delay_for(1) == 1.0
        assert policy.delay_for(2) == 2.0
        assert policy.delay_for(3) == 4.0

    def test_delay_capped_at_max(self):
        policy = RetryPolicy(base_delay=1.0, exponential_base=2.0, max_delay=3.0)
        assert policy.delay_for(3) == 3.0

    def test_with_overrides(self):
        policy = RetryPolicy(max_retries=3, base_delay=1.0)
        new = policy.with_overrides(max_retries=5, base_delay=2.0)
        assert new.max_retries == 5
        assert new.base_delay == 2.0


# -----------------------------------------------------------------------------
# HttpClient
# -----------------------------------------------------------------------------

class TestHttpClient:
    async def test_get_success(self):
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        response.text = "ok"

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=response)

        client = HttpClient(
            base_url="https://example.com",
            client=mock_client,
        )
        resp = await client.get("/test")
        assert resp.status_code == 200
        mock_client.request.assert_called_once()

    async def test_get_with_retry(self):
        response_ok = MagicMock(spec=httpx.Response)
        response_ok.status_code = 200

        response_500 = MagicMock(spec=httpx.Response)
        response_500.status_code = 500

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(side_effect=[response_500, response_ok])

        client = HttpClient(
            base_url="https://example.com",
            client=mock_client,
            retry_policy=RetryPolicy(max_retries=2, base_delay=0.0),
        )
        resp = await client.get("/test")
        assert resp.status_code == 200
        assert mock_client.request.call_count == 2

    async def test_post_success(self):
        response = MagicMock(spec=httpx.Response)
        response.status_code = 201

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=response)

        client = HttpClient(
            base_url="https://example.com",
            client=mock_client,
        )
        resp = await client.post("/orders", json={"symbol": "BTCUSDT"})
        assert resp.status_code == 201

    async def test_put_success(self):
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=response)

        client = HttpClient(
            base_url="https://example.com",
            client=mock_client,
        )
        resp = await client.put("/orders/1", json={"status": "cancel"})
        assert resp.status_code == 200

    async def test_delete_success(self):
        response = MagicMock(spec=httpx.Response)
        response.status_code = 204

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=response)

        client = HttpClient(
            base_url="https://example.com",
            client=mock_client,
        )
        resp = await client.delete("/orders/1")
        assert resp.status_code == 204

    async def test_rate_limited_request_waits(self):
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=response)

        limiter = RateLimiter()
        limiter.configure("api", RateLimitConfig(max_tokens=2.0, refill_rate=2.0))

        client = HttpClient(
            base_url="https://example.com",
            client=mock_client,
            rate_limiter=limiter,
        )
        await client.get("/test", endpoint_key="api")
        await client.get("/test", endpoint_key="api")
        assert mock_client.request.call_count == 2

    async def test_timeout_becomes_timeout_error(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        client = HttpClient(
            base_url="https://example.com",
            client=mock_client,
            retry_policy=RetryPolicy(max_retries=0),
        )
        with pytest.raises(TimeoutError):
            await client.get("/test")

    async def test_network_error_maps_to_exchange_connection_error(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(side_effect=httpx.ConnectError("refused"))

        client = HttpClient(
            base_url="https://example.com",
            client=mock_client,
            retry_policy=RetryPolicy(max_retries=0),
        )
        with pytest.raises(ExchangeConnectionError):
            await client.get("/test")

    async def test_close(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        client = HttpClient(client=mock_client)
        await client.close()
        mock_client.aclose.assert_awaited_once()


# -----------------------------------------------------------------------------
# WebSocketManager
# -----------------------------------------------------------------------------

class TestWebSocketManager:
    async def test_register_unregister_callback(self):
        manager = WebSocketManager()
        cb = MagicMock()
        manager.register_callback(cb)
        assert cb in manager._callbacks
        manager.unregister_callback(cb)
        assert cb not in manager._callbacks

    async def test_dispatch_calls_callback(self):
        manager = WebSocketManager()
        cb = MagicMock()
        manager.register_callback(cb)
        manager._dispatch(json.dumps({"p": "BTCUSDT"}))
        cb.assert_called_once()

    async def test_connect_without_url_raises(self):
        manager = WebSocketManager()
        with pytest.raises(ValueError):
            await manager.connect()

    async def test_connect_success(self):
        mock_ws = AsyncMock(spec=websockets.WebSocketClientProtocol)
        mock_ws.open = True

        with patch("websockets.connect", new=AsyncMock(return_value=mock_ws)) as mock_connect:
            manager = WebSocketManager(retry_policy=RetryPolicy(max_retries=1, base_delay=0.0))
            # Prevent background receive loop from running in this test
            with patch.object(manager, "_receive_loop", new=AsyncMock()):
                result = await manager.connect("wss://example.com/ws")

        assert result is True
        assert manager.is_connected is True

    async def test_send_and_receive(self):
        mock_ws = AsyncMock(spec=websockets.WebSocketClientProtocol)
        mock_ws.recv = AsyncMock(return_value='{"p":"BTCUSDT"}')

        manager = WebSocketManager()
        manager._ws = mock_ws
        await manager.send('{"sub":"BTCUSDT"}')
        mock_ws.send.assert_awaited_once_with('{"sub":"BTCUSDT"}')

        msg = await manager.receive()
        assert msg == '{"p":"BTCUSDT"}'

    async def test_send_json(self):
        mock_ws = AsyncMock(spec=websockets.WebSocketClientProtocol)
        manager = WebSocketManager()
        manager._ws = mock_ws
        await manager.send_json({"sub": "BTCUSDT"})
        mock_ws.send.assert_awaited_once_with('{"sub": "BTCUSDT"}')

    async def test_subscribe_remembered(self):
        mock_ws = AsyncMock(spec=websockets.WebSocketClientProtocol)
        manager = WebSocketManager()
        manager._ws = mock_ws
        await manager.subscribe('{"sub":"BTCUSDT"}')
        assert '{"sub":"BTCUSDT"}' in manager._subscribed_messages

    async def test_unsubscribe_removes_message(self):
        mock_ws = AsyncMock(spec=websockets.WebSocketClientProtocol)
        manager = WebSocketManager()
        manager._ws = mock_ws
        await manager.subscribe('{"sub":"BTCUSDT"}')
        await manager.unsubscribe('{"sub":"BTCUSDT"}')
        assert '{"sub":"BTCUSDT"}' not in manager._subscribed_messages

    async def test_disconnect(self):
        mock_ws = AsyncMock(spec=websockets.WebSocketClientProtocol)
        manager = WebSocketManager()
        manager._ws = mock_ws
        manager._running = True
        await manager.disconnect()
        assert manager._running is False
        mock_ws.close.assert_awaited_once()

    async def test_send_when_not_connected_raises(self):
        manager = WebSocketManager()
        with pytest.raises(RuntimeError):
            await manager.send("message")

    async def test_receive_when_not_connected_raises(self):
        manager = WebSocketManager()
        with pytest.raises(RuntimeError):
            await manager.receive()


# -----------------------------------------------------------------------------
# Integration / helper behavior
# -----------------------------------------------------------------------------

class TestIntegration:
    async def test_factory_creates_adapter_with_http_and_ws(self):
        class TestAdapter(IExchangeAdapter):
            def __init__(self):
                self.http = HttpClient()
                self.ws = WebSocketManager()

            async def initialize(self, config): return True
            async def authenticate(self, credentials): return True
            async def connect_market(self): return True
            async def connect_account(self): return True
            async def disconnect(self): pass
            async def get_exchange_info(self): return None
            async def get_balance(self, asset=None): return []
            async def get_account(self): return None
            async def get_symbol_info(self, symbol): return None
            async def get_positions(self, symbol=None): return []
            async def place_order(self, *args, **kwargs): return None
            async def cancel_order(self, symbol, order_id): return None
            async def cancel_all(self, symbol=None): return []
            async def get_order(self, symbol, order_id): return None
            async def get_open_orders(self, symbol=None): return []
            async def get_ticker(self, symbol): return None
            async def get_order_book(self, symbol, limit=100): return None
            async def get_candles(self, symbol, interval, limit=100): return []
            async def get_trades(self, symbol, limit=100): return []
            async def health_check(self): return True
            async def subscribe_market(self, symbols, channel, callback): return True
            async def subscribe_account(self, channel, callback): return True
            async def unsubscribe_market(self, symbols, channel): return True
            async def unsubscribe_account(self, channel): return True

        ExchangeFactory.clear()
        ExchangeFactory.register("test", TestAdapter)
        adapter = ExchangeFactory.create("test")
        assert isinstance(adapter.http, HttpClient)
        assert isinstance(adapter.ws, WebSocketManager)
        ExchangeFactory.clear()

    async def test_http_client_maps_error_with_error_mapper(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=MagicMock(status_code=502, text="bad gateway"))

        client = HttpClient(
            base_url="https://example.com",
            client=mock_client,
            retry_policy=RetryPolicy(max_retries=0),
        )
        response = await client.get("/test")
        assert response.status_code == 502

    async def test_rate_limiter_blocks_then_refills(self):
        limiter = RateLimiter()
        limiter.configure("fast", RateLimitConfig(max_tokens=1.0, refill_rate=10.0))
        await limiter.acquire("fast", 1.0)
        assert limiter.can_acquire("fast", 1.0) is False
        await asyncio.sleep(0.15)
        assert limiter.can_acquire("fast", 1.0) is True

    async def test_credential_manager_long_secret_works(self):
        manager = CredentialManager(secret_key="x" * 64)
        cipher = manager.encrypt("secret")
        assert manager.decrypt(cipher) == "secret"


# -----------------------------------------------------------------------------
# Additional edge cases to meet Sprint 3 test target
# -----------------------------------------------------------------------------

class TestErrorMapperEdgeCases:
    def test_400_error(self):
        mapper = ErrorMapper("binance")
        err = mapper.map_http_error(400, body={"msg": "bad request"})
        assert err.error_code == "HTTP_ERROR"

    def test_401_error(self):
        mapper = ErrorMapper("bybit")
        err = mapper.map_http_error(401)
        assert isinstance(err, ExchangeError)

    def test_403_error(self):
        mapper = ErrorMapper("okx")
        err = mapper.map_http_error(403)
        assert err.error_code == "HTTP_ERROR"

    def test_404_error(self):
        mapper = ErrorMapper("mexc")
        err = mapper.map_http_error(404)
        assert err.error_code == "HTTP_ERROR"

    def test_418_ip_ban(self):
        mapper = ErrorMapper("binance")
        err = mapper.map_http_error(418)
        assert err.error_code == "HTTP_ERROR"

    def test_502_status_is_connection_error(self):
        mapper = ErrorMapper("binance")
        err = mapper.map_http_error(502)
        assert isinstance(err, ExchangeConnectionError)

    def test_504_status_is_connection_error(self):
        mapper = ErrorMapper("hyperliquid")
        err = mapper.map_http_error(504)
        assert isinstance(err, ExchangeConnectionError)


class TestRetryPolicyEdgeCases:
    def test_default_retryable_status_codes(self):
        policy = RetryPolicy()
        assert policy.should_retry_status(429) is True
        assert policy.should_retry_status(500) is True
        assert policy.should_retry_status(502) is True
        assert policy.should_retry_status(503) is True
        assert policy.should_retry_status(504) is True
        assert policy.should_retry_status(200) is False
        assert policy.should_retry_status(400) is False

    def test_retry_delay_first_attempt(self):
        policy = RetryPolicy(base_delay=0.5, exponential_base=2.0)
        assert policy.delay_for(1) == 0.5

    def test_max_delay_zero(self):
        policy = RetryPolicy(base_delay=0.0, max_delay=0.0)
        assert policy.delay_for(1) == 0.0


class TestRateLimiterEdgeCases:
    def test_default_config_used(self):
        limiter = RateLimiter()
        assert limiter.get_config("unknown").max_tokens == 120.0

    def test_configure_sets_initial_tokens(self):
        limiter = RateLimiter()
        limiter.configure("api", RateLimitConfig(max_tokens=10.0, refill_rate=5.0))
        assert limiter.can_acquire("api", 10.0) is True

    async def test_acquire_multiple_tokens(self):
        limiter = RateLimiter()
        limiter.configure("api", RateLimitConfig(max_tokens=5.0, refill_rate=5.0))
        await limiter.acquire("api", 3.0)
        assert limiter.can_acquire("api", 3.0) is False
        assert limiter.can_acquire("api", 2.0) is True


class TestHttpClientEdgeCases:
    async def test_request_with_custom_endpoint_key(self):
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=response)

        client = HttpClient(client=mock_client, retry_policy=RetryPolicy(max_retries=1))
        resp = await client.request("GET", "/test", endpoint_key="custom", rate_limit_tokens=0.5)
        assert resp.status_code == 200

    async def test_http_client_without_retry(self):
        response = MagicMock(spec=httpx.Response)
        response.status_code = 500

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=response)

        client = HttpClient(client=mock_client, retry_policy=RetryPolicy(max_retries=0))
        resp = await client.get("/test")
        assert resp.status_code == 500

    async def test_http_client_returns_client_error(self):
        response = MagicMock(spec=httpx.Response)
        response.status_code = 400

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=response)

        client = HttpClient(client=mock_client, retry_policy=RetryPolicy(max_retries=0))
        resp = await client.get("/test")
        assert resp.status_code == 400


class TestCredentialManagerEdgeCases:
    def test_empty_string_encryption(self):
        manager = CredentialManager(secret_key="secret")
        cipher = manager.encrypt("")
        assert manager.decrypt(cipher) == ""

    def test_unicode_secret(self):
        manager = CredentialManager(secret_key="unïcôdé_key")
        cipher = manager.encrypt("api🔑key")
        assert manager.decrypt(cipher) == "api🔑key"

    def test_mask_visible_zero_masks_all(self):
        manager = CredentialManager(secret_key="secret")
        assert manager.mask("abcd", visible=0) == "****"

    def test_mask_visible_equals_length_shows_all(self):
        manager = CredentialManager(secret_key="secret")
        assert manager.mask("abcd", visible=4) == "abcd"


class TestWebSocketManagerEdgeCases:
    async def test_callback_exception_does_not_propagate(self):
        manager = WebSocketManager()

        def bad_callback(msg):
            raise RuntimeError("callback error")

        manager.register_callback(bad_callback)
        manager._dispatch("{}")
        # no exception should escape

    async def test_disconnect_without_connect_is_safe(self):
        manager = WebSocketManager()
        await manager.disconnect()
        assert manager._running is False

    async def test_connect_failure_with_retries(self):
        with patch("websockets.connect", new=AsyncMock(side_effect=Exception("refused"))):
            manager = WebSocketManager(retry_policy=RetryPolicy(max_retries=2, base_delay=0.0))
            result = await manager.connect("wss://example.com/ws")
        assert result is False

    async def test_send_json_with_complex_data(self):
        mock_ws = AsyncMock(spec=websockets.WebSocketClientProtocol)
        manager = WebSocketManager()
        manager._ws = mock_ws
        await manager.send_json({"method": "SUBSCRIBE", "params": ["btcusdt@aggTrade"]})
        sent = mock_ws.send.call_args[0][0]
        data = json.loads(sent)
        assert data["method"] == "SUBSCRIBE"
        assert "btcusdt@aggTrade" in data["params"]


class TestFactoryEdgeCases:
    def test_clear_removes_all(self):
        class DummyAdapter(IExchangeAdapter):
            async def initialize(self, config): return True
            async def authenticate(self, credentials): return True
            async def connect_market(self): return True
            async def connect_account(self): return True
            async def disconnect(self): pass
            async def get_exchange_info(self): return None
            async def get_balance(self, asset=None): return []
            async def get_account(self): return None
            async def get_symbol_info(self, symbol): return None
            async def get_positions(self, symbol=None): return []
            async def place_order(self, *args, **kwargs): return None
            async def cancel_order(self, symbol, order_id): return None
            async def cancel_all(self, symbol=None): return []
            async def get_order(self, symbol, order_id): return None
            async def get_open_orders(self, symbol=None): return []
            async def get_ticker(self, symbol): return None
            async def get_order_book(self, symbol, limit=100): return None
            async def get_candles(self, symbol, interval, limit=100): return []
            async def get_trades(self, symbol, limit=100): return []
            async def health_check(self): return True
            async def subscribe_market(self, symbols, channel, callback): return True
            async def subscribe_account(self, channel, callback): return True
            async def unsubscribe_market(self, symbols, channel): return True
            async def unsubscribe_account(self, channel): return True

        ExchangeFactory.register("a", DummyAdapter)
        ExchangeFactory.clear()
        assert ExchangeFactory.registered_exchanges() == []

    def test_multiple_instances_are_independent(self):
        class DummyAdapter(IExchangeAdapter):
            async def initialize(self, config): return True
            async def authenticate(self, credentials): return True
            async def connect_market(self): return True
            async def connect_account(self): return True
            async def disconnect(self): pass
            async def get_exchange_info(self): return None
            async def get_balance(self, asset=None): return []
            async def get_account(self): return None
            async def get_symbol_info(self, symbol): return None
            async def get_positions(self, symbol=None): return []
            async def place_order(self, *args, **kwargs): return None
            async def cancel_order(self, symbol, order_id): return None
            async def cancel_all(self, symbol=None): return []
            async def get_order(self, symbol, order_id): return None
            async def get_open_orders(self, symbol=None): return []
            async def get_ticker(self, symbol): return None
            async def get_order_book(self, symbol, limit=100): return None
            async def get_candles(self, symbol, interval, limit=100): return []
            async def get_trades(self, symbol, limit=100): return []
            async def health_check(self): return True
            async def subscribe_market(self, symbols, channel, callback): return True
            async def subscribe_account(self, channel, callback): return True
            async def unsubscribe_market(self, symbols, channel): return True
            async def unsubscribe_account(self, channel): return True

        ExchangeFactory.clear()
        ExchangeFactory.register("dummy", DummyAdapter)
        a1 = ExchangeFactory.create("dummy")
        a2 = ExchangeFactory.create("dummy")
        assert a1 is not a2

    def test_register_overwrites_existing(self):
        class DummyAdapter(IExchangeAdapter):
            async def initialize(self, config): return True
            async def authenticate(self, credentials): return True
            async def connect_market(self): return True
            async def connect_account(self): return True
            async def disconnect(self): pass
            async def get_exchange_info(self): return None
            async def get_balance(self, asset=None): return []
            async def get_account(self): return None
            async def get_symbol_info(self, symbol): return None
            async def get_positions(self, symbol=None): return []
            async def place_order(self, *args, **kwargs): return None
            async def cancel_order(self, symbol, order_id): return None
            async def cancel_all(self, symbol=None): return []
            async def get_order(self, symbol, order_id): return None
            async def get_open_orders(self, symbol=None): return []
            async def get_ticker(self, symbol): return None
            async def get_order_book(self, symbol, limit=100): return None
            async def get_candles(self, symbol, interval, limit=100): return []
            async def get_trades(self, symbol, limit=100): return []
            async def health_check(self): return True
            async def subscribe_market(self, symbols, channel, callback): return True
            async def subscribe_account(self, channel, callback): return True
            async def unsubscribe_market(self, symbols, channel): return True
            async def unsubscribe_account(self, channel): return True

        class DummyAdapter2(IExchangeAdapter):
            async def initialize(self, config): return True
            async def authenticate(self, credentials): return True
            async def connect_market(self): return True
            async def connect_account(self): return True
            async def disconnect(self): pass
            async def get_exchange_info(self): return None
            async def get_balance(self, asset=None): return []
            async def get_account(self): return None
            async def get_symbol_info(self, symbol): return None
            async def get_positions(self, symbol=None): return []
            async def place_order(self, *args, **kwargs): return None
            async def cancel_order(self, symbol, order_id): return None
            async def cancel_all(self, symbol=None): return []
            async def get_order(self, symbol, order_id): return None
            async def get_open_orders(self, symbol=None): return []
            async def get_ticker(self, symbol): return None
            async def get_order_book(self, symbol, limit=100): return None
            async def get_candles(self, symbol, interval, limit=100): return []
            async def get_trades(self, symbol, limit=100): return []
            async def health_check(self): return True
            async def subscribe_market(self, symbols, channel, callback): return True
            async def subscribe_account(self, channel, callback): return True
            async def unsubscribe_market(self, symbols, channel): return True
            async def unsubscribe_account(self, channel): return True

        ExchangeFactory.register("dummy", DummyAdapter)
        ExchangeFactory.register("dummy", DummyAdapter2)
        adapter = ExchangeFactory.create("dummy")
        assert isinstance(adapter, DummyAdapter2)
