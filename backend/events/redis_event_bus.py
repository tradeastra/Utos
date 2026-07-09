"""
Redis-based event bus implementation for UTOS Trading Engine.

This module implements the IEventBus interface using Redis pub/sub.
"""

import asyncio
import json
import uuid
from typing import Optional, Callable, Dict, Any, List
from datetime import datetime, timedelta
import redis.asyncio as aioredis
from concurrent.futures import ThreadPoolExecutor

from events.base import IEventBus
from core.types import Event
from core.exceptions import EventError, TimeoutError
from core.logging import get_logger
from database.redis_client import get_redis_url

logger = get_logger(__name__)


class RedisEventBus(IEventBus):
    """Redis-based event bus implementation."""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.subscriptions: Dict[str, Callable] = {}
        self.pubsub: Optional[aioredis.PubSub] = None
        self.listener_task: Optional[asyncio.Task] = None
        self.response_handlers: Dict[str, Callable] = {}
        self.response_waiters: Dict[str, asyncio.Future] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
    
    async def _get_redis(self) -> aioredis.Redis:
        """Get Redis client."""
        if self.redis is None:
            self.redis = aioredis.from_url(
                get_redis_url(),
                encoding="utf-8",
                decode_responses=True,
                max_connections=100,
            )
        return self.redis
    
    async def _ensure_listener(self):
        """Ensure event listener is running."""
        if self.listener_task is None:
            self.listener_task = asyncio.create_task(self._listen_events())
    
    async def _listen_events(self):
        """Listen for events from Redis."""
        try:
            redis = await self._get_redis()
            self.pubsub = redis.pubsub()
            
            # Subscribe to all channels
            if self.subscriptions:
                await self.pubsub.subscribe(*self.subscriptions.keys())
            
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    await self._handle_message(message)
                    
        except Exception as e:
            logger.error(f"Event listener error: {e}")
            # Restart listener after delay
            await asyncio.sleep(5)
            self.listener_task = None
            await self._ensure_listener()
    
    async def _handle_message(self, message: dict):
        """Handle incoming message."""
        try:
            channel = message["channel"]
            data = message["data"]
            
            # Parse event
            if isinstance(data, str):
                event_data = json.loads(data)
            else:
                event_data = data
            
            # Check if it's a response
            if channel.startswith("response:"):
                response_id = channel.split(":", 1)[1]
                if response_id in self.response_waiters:
                    future = self.response_waiters.pop(response_id)
                    if not future.done():
                        future.set_result(event_data)
                return
            
            # Handle regular event
            if channel in self.subscriptions:
                handler = self.subscriptions[channel]
                event = Event(
                    event_type=event_data.get("event_type"),
                    event_id=event_data.get("event_id"),
                    timestamp=datetime.fromisoformat(event_data.get("timestamp")),
                    data=event_data.get("data", {}),
                    metadata=event_data.get("metadata", {}),
                )
                
                # Run handler in thread pool to avoid blocking
                asyncio.get_event_loop().run_in_executor(
                    self.executor, handler, event
                )
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def publish(self, event_type: str, data: dict, metadata: Optional[dict] = None) -> str:
        """Publish an event."""
        try:
            redis = await self._get_redis()
            
            event_id = str(uuid.uuid4())
            event = {
                "event_type": event_type,
                "event_id": event_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data,
                "metadata": metadata or {},
            }
            
            # Publish to general channel
            await redis.publish("events", json.dumps(event))
            
            # Publish to specific event type channel
            await redis.publish(f"event:{event_type}", json.dumps(event))
            
            logger.debug(f"Published event {event_type} with ID {event_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Error publishing event: {e}")
            raise EventError(f"Failed to publish event: {e}")
    
    async def subscribe(
        self,
        channel: str,
        handler: Callable[[Event], None],
    ) -> str:
        """Subscribe to a channel."""
        try:
            subscription_id = str(uuid.uuid4())
            self.subscriptions[channel] = handler
            
            # Start listener if not running
            await self._ensure_listener()
            
            # Subscribe to channel in Redis
            if self.pubsub:
                await self.pubsub.subscribe(channel)
            
            logger.debug(f"Subscribed to channel {channel}")
            return subscription_id
            
        except Exception as e:
            logger.error(f"Error subscribing to channel: {e}")
            raise EventError(f"Failed to subscribe to channel: {e}")
    
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from a channel."""
        try:
            # Find channel by subscription ID
            channel_to_remove = None
            for channel, handler in self.subscriptions.items():
                if id(handler) == subscription_id:
                    channel_to_remove = channel
                    break
            
            if channel_to_remove:
                del self.subscriptions[channel_to_remove]
                
                # Unsubscribe from Redis
                if self.pubsub:
                    await self.pubsub.unsubscribe(channel_to_remove)
                
                logger.debug(f"Unsubscribed from channel {channel_to_remove}")
            
        except Exception as e:
            logger.error(f"Error unsubscribing from channel: {e}")
            raise EventError(f"Failed to unsubscribe from channel: {e}")
    
    async def publish_to_user(self, user_id: str, event_type: str, data: dict) -> str:
        """Publish event to a specific user's channel."""
        try:
            redis = await self._get_redis()
            
            event_id = str(uuid.uuid4())
            event = {
                "event_type": event_type,
                "event_id": event_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data,
                "metadata": {"user_id": user_id},
            }
            
            # Publish to user-specific channel
            await redis.publish(f"user:{user_id}", json.dumps(event))
            
            logger.debug(f"Published event {event_type} to user {user_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Error publishing to user: {e}")
            raise EventError(f"Failed to publish to user: {e}")
    
    async def request(self, channel: str, data: dict, timeout: float = 5.0) -> dict:
        """Request-response pattern."""
        try:
            redis = await self._get_redis()
            
            request_id = str(uuid.uuid4())
            response_channel = f"response:{request_id}"
            
            # Create future for response
            future = asyncio.get_event_loop().create_future()
            self.response_waiters[request_id] = future
            
            # Subscribe to response channel
            await self._ensure_listener()
            if self.pubsub:
                await self.pubsub.subscribe(response_channel)
            
            # Publish request
            request_data = {
                "request_id": request_id,
                "channel": channel,
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            await redis.publish(f"request:{channel}", json.dumps(request_data))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(future, timeout=timeout)
                return response
            except asyncio.TimeoutError:
                self.response_waiters.pop(request_id, None)
                raise TimeoutError(f"Request timed out after {timeout} seconds", timeout)
            
        except Exception as e:
            logger.error(f"Error making request: {e}")
            raise EventError(f"Failed to make request: {e}")
    
    async def respond(self, channel: str, handler: Callable[[dict], dict]) -> str:
        """Set up response handler for request-response pattern."""
        try:
            handler_id = str(uuid.uuid4())
            request_channel = f"request:{channel}"
            
            # Subscribe to request channel
            async def request_handler(message):
                try:
                    request_data = json.loads(message["data"])
                    response_data = handler(request_data["data"])
                    
                    # Send response
                    response_channel = f"response:{request_data['request_id']}"
                    redis = await self._get_redis()
                    await redis.publish(response_channel, json.dumps(response_data))
                    
                except Exception as e:
                    logger.error(f"Error handling request: {e}")
            
            await self.subscribe(request_channel, request_handler)
            
            logger.debug(f"Set up response handler for channel {channel}")
            return handler_id
            
        except Exception as e:
            logger.error(f"Error setting up response handler: {e}")
            raise EventError(f"Failed to set up response handler: {e}")
    
    async def publish_instance_event(
        self,
        instance_id: str,
        event_type: str,
        data: dict,
    ) -> str:
        """Publish event to a specific trading instance's channel."""
        try:
            redis = await self._get_redis()
            
            event_id = str(uuid.uuid4())
            event = {
                "event_type": event_type,
                "event_id": event_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data,
                "metadata": {"instance_id": instance_id},
            }
            
            # Publish to instance-specific channel
            await redis.publish(f"instance:{instance_id}", json.dumps(event))
            
            logger.debug(f"Published event {event_type} to instance {instance_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Error publishing to instance: {e}")
            raise EventError(f"Failed to publish to instance: {e}")
    
    async def publish_market_event(
        self,
        symbol: str,
        exchange: str,
        event_type: str,
        data: dict,
    ) -> str:
        """Publish market data event."""
        try:
            redis = await self._get_redis()
            
            event_id = str(uuid.uuid4())
            event = {
                "event_type": event_type,
                "event_id": event_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data,
                "metadata": {"symbol": symbol, "exchange": exchange},
            }
            
            # Publish to market-specific channel
            await redis.publish(f"market:{exchange}:{symbol}", json.dumps(event))
            
            logger.debug(f"Published market event {event_type} for {exchange}:{symbol}")
            return event_id
            
        except Exception as e:
            logger.error(f"Error publishing market event: {e}")
            raise EventError(f"Failed to publish market event: {e}")
    
    async def publish_system_event(self, event_type: str, data: dict) -> str:
        """Publish system-wide event."""
        try:
            redis = await self._get_redis()
            
            event_id = str(uuid.uuid4())
            event = {
                "event_type": event_type,
                "event_id": event_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data,
                "metadata": {"scope": "system"},
            }
            
            # Publish to system channel
            await redis.publish("system", json.dumps(event))
            
            logger.debug(f"Published system event {event_type}")
            return event_id
            
        except Exception as e:
            logger.error(f"Error publishing system event: {e}")
            raise EventError(f"Failed to publish system event: {e}")
    
    async def get_event(self, event_id: str) -> Optional[Event]:
        """Get event by ID."""
        # Note: Redis pub/sub doesn't store events, so this would need
        # to be implemented with a separate event store
        logger.warning("Event retrieval not implemented for Redis pub/sub")
        return None
    
    async def get_events(
        self,
        channel: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Event]:
        """Get events with optional filtering."""
        # Note: Redis pub/sub doesn't store events, so this would need
        # to be implemented with a separate event store
        logger.warning("Event retrieval not implemented for Redis pub/sub")
        return []
    
    async def create_event_stream(
        self,
        channels: List[str],
        callback: Callable[[Event], None],
    ) -> str:
        """Create event stream for multiple channels."""
        try:
            stream_id = str(uuid.uuid4())
            
            # Subscribe to all channels
            for channel in channels:
                await self.subscribe(channel, callback)
            
            logger.debug(f"Created event stream {stream_id} for channels {channels}")
            return stream_id
            
        except Exception as e:
            logger.error(f"Error creating event stream: {e}")
            raise EventError(f"Failed to create event stream: {e}")
    
    async def close_event_stream(self, stream_id: str) -> None:
        """Close event stream."""
        # Note: This would need to track which channels belong to which stream
        logger.warning("Event stream closing not fully implemented")
    
    async def health_check(self) -> bool:
        """Check event bus health."""
        try:
            redis = await self._get_redis()
            return await redis.ping()
        except Exception as e:
            logger.error(f"Event bus health check failed: {e}")
            return False
    
    async def get_stats(self) -> dict:
        """Get event bus statistics."""
        try:
            redis = await self._get_redis()
            info = await redis.info()
            
            return {
                "subscriptions": len(self.subscriptions),
                "active_listeners": 1 if self.listener_task else 0,
                "response_waiters": len(self.response_waiters),
                "redis_connected_clients": info.get("connected_clients", 0),
                "redis_memory_usage": info.get("used_memory_human", "unknown"),
            }
            
        except Exception as e:
            logger.error(f"Error getting event bus stats: {e}")
            return {}
    
    async def close(self):
        """Close event bus connections."""
        try:
            # Stop listener
            if self.listener_task:
                self.listener_task.cancel()
                self.listener_task = None
            
            # Close pubsub
            if self.pubsub:
                await self.pubsub.close()
                self.pubsub = None
            
            # Close Redis connection
            if self.redis:
                await self.redis.close()
                self.redis = None
            
            # Close thread pool
            self.executor.shutdown(wait=True)
            
            logger.info("Event bus closed")
            
        except Exception as e:
            logger.error(f"Error closing event bus: {e}")


# Create global event bus instance
event_bus = RedisEventBus()
