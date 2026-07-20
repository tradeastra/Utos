"""
Generic WebSocket manager — Sprint 3.

Manages connection lifecycle, reconnect, send/receive, and message dispatch
for exchange WebSocket streams. No exchange-specific protocol logic.
"""

import asyncio
import contextlib
import json
from collections.abc import Callable
from typing import Any

import websockets
from core.logging import get_logger

from exchanges.rate_limiter import RateLimiter
from exchanges.retry import RetryPolicy

logger = get_logger(__name__)


class WebSocketManager:
    """Generic WebSocket manager with reconnect and callback dispatch."""

    def __init__(
        self,
        url: str = "",
        retry_policy: RetryPolicy | None = None,
        rate_limiter: RateLimiter | None = None,
        ping_interval: float = 20.0,
        pong_timeout: float = 10.0,
        reconnect_jitter: float = 1.0,
    ) -> None:
        self.url = url
        self.retry_policy = retry_policy or RetryPolicy(max_retries=5, base_delay=1.0)
        self.rate_limiter = rate_limiter
        self.ping_interval = ping_interval
        self.pong_timeout = pong_timeout
        self.reconnect_jitter = reconnect_jitter

        self._ws: websockets.WebSocketClientProtocol | None = None
        self._callbacks: list[Callable[[Any], None]] = []
        self._running = False
        self._receive_task: asyncio.Task | None = None
        # Per-URL active subscriptions: url -> {dedup_key: raw_message}
        self._subscriptions: dict[str, dict[str, str]] = {}

    @property
    def _subscribed_messages(self) -> list[str]:
        """Return active subscription messages for the current URL."""
        return list(self._subscriptions.get(self.url, {}).values())

    def _subscription_key(self, message: str) -> str:
        """Return a stable deduplication key for a subscription message.

        For messages containing a ``params`` field (e.g. Binance WS
        SUBSCRIBE/UNSUBSCRIBE), the key is derived from the sorted params so
        that two subscribe calls with the same logical stream are treated as
        duplicates regardless of the JSON ``id`` field.
        """
        try:
            data = json.loads(message)
        except Exception:
            return message
        if isinstance(data, dict) and "params" in data:
            params = data["params"]
            if isinstance(params, list):
                params = sorted(params)
            return json.dumps({"params": params}, separators=(",", ":"), sort_keys=True)
        return message

    def register_callback(self, callback: Callable[[Any], None]) -> None:
        """Register a callback for incoming messages."""
        self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[Any], None]) -> None:
        """Unregister a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _dispatch(self, message: Any) -> None:
        """Dispatch a message to all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"WebSocket callback error: {e}")

    async def connect(self, url: str | None = None) -> bool:
        """Connect to the WebSocket server with retry."""
        target_url = url or self.url
        if not target_url:
            raise ValueError("WebSocket URL is required")

        self.url = target_url
        self._running = True

        for attempt in range(1, self.retry_policy.max_retries + 1):
            try:
                if self.rate_limiter is not None:
                    await self.rate_limiter.acquire("websocket", 1.0)

                logger.info(f"Connecting WebSocket to {target_url} (attempt {attempt})")
                self._ws = await websockets.connect(
                    target_url,
                    ping_interval=self.ping_interval,
                    ping_timeout=self.pong_timeout,
                )
                logger.info("WebSocket connected")

                self._receive_task = asyncio.create_task(self._receive_loop())

                # Resubscribe to previous messages for this URL only
                for msg in self._subscriptions.get(target_url, {}).values():
                    await self.send(msg)

                return True

            except Exception as e:
                logger.warning(f"WebSocket connect attempt {attempt} failed: {e}")
                if not self.retry_policy.should_retry(attempt, e):
                    break
                delay = self.retry_policy.delay_for(attempt)
                if self.reconnect_jitter:
                    delay += asyncio.get_event_loop().time() % self.reconnect_jitter
                await asyncio.sleep(delay)

        return False

    async def _receive_loop(self) -> None:
        """Background receive loop."""
        if self._ws is None:
            return

        try:
            async for message in self._ws:
                if not self._running:
                    break
                self._dispatch(message)
        except websockets.ConnectionClosed as e:
            logger.warning(f"WebSocket closed: {e}")
        except Exception as e:
            logger.error(f"WebSocket receive error: {e}")
        finally:
            if self._running:
                asyncio.create_task(self._reconnect())

    async def _reconnect(self) -> None:
        """Attempt to reconnect the WebSocket."""
        if not self._running or not self.url:
            return

        logger.info("WebSocket reconnecting...")
        await self.connect(self.url)

    async def send(self, message: str) -> None:
        """Send a raw message to the WebSocket."""
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")
        await self._ws.send(message)

    async def send_json(self, data: Any) -> None:
        """Send a JSON-serializable message."""
        await self.send(json.dumps(data))

    async def receive(self) -> str:
        """Receive a single raw message (blocking)."""
        if self._ws is None:
            raise RuntimeError("WebSocket is not connected")
        return await self._ws.recv()

    async def subscribe(self, message: str) -> None:
        """Subscribe to a stream and remember the message for reconnects."""
        key = self._subscription_key(message)
        url_subs = self._subscriptions.setdefault(self.url, {})
        if key in url_subs:
            logger.debug(f"Duplicate WebSocket subscription ignored: {message}")
            return
        url_subs[key] = message
        await self.send(message)

    async def unsubscribe(self, message: str) -> None:
        """Unsubscribe from a stream and remove the message from reconnects."""
        key = self._subscription_key(message)
        url_subs = self._subscriptions.get(self.url, {})
        if key in url_subs:
            del url_subs[key]
            if not url_subs:
                del self._subscriptions[self.url]
        await self.send(message)

    async def disconnect(self) -> None:
        """Disconnect the WebSocket and stop the receive loop."""
        self._running = False
        self._subscriptions.pop(self.url, None)

        if self._receive_task is not None:
            self._receive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._receive_task
            self._receive_task = None

        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception as e:
                logger.error(f"WebSocket close error: {e}")
            self._ws = None

    @property
    def is_connected(self) -> bool:
        """Return True if the WebSocket is currently open."""
        return self._ws is not None and self._ws.open
