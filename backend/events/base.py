"""
Base interface for the Event Bus.

This module defines the IEventBus interface that handles event publishing
and subscription via Redis.
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from core.types import Event
from core.exceptions import EventError


class IEventBus(ABC):
    """Interface for the Event Bus.
    
    The Event Bus handles event publishing and subscription via Redis,
    enabling event-driven architecture throughout the system.
    """

    @abstractmethod
    async def publish(self, event_type: str, data: dict, metadata: Optional[dict] = None) -> str:
        """Publish an event.
        
        Args:
            event_type: Type of event (e.g., "ORDER_FILLED", "INSTANCE_CREATED")
            data: Event data payload
            metadata: Optional metadata (e.g., user_id, instance_id)
            
        Returns:
            Event ID
            
        Raises:
            EventError: If publishing fails
        """
        pass

    @abstractmethod
    async def subscribe(
        self,
        channel: str,
        handler: Callable[[Event], None],
    ) -> str:
        """Subscribe to a channel.
        
        Args:
            channel: Channel name (e.g., "trading_instance:{id}", "market:BTCUSDT")
            handler: Callback function to handle events
            
        Returns:
            Subscription ID
            
        Raises:
            EventError: If subscription fails
        """
        pass

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from a channel.
        
        Args:
            subscription_id: Subscription ID returned by subscribe
            
        Raises:
            EventError: If unsubscription fails
        """
        pass

    @abstractmethod
    async def publish_to_user(self, user_id: str, event_type: str, data: dict) -> str:
        """Publish event to a specific user's channel.
        
        Args:
            user_id: User ID
            event_type: Type of event
            data: Event data payload
            
        Returns:
            Event ID
            
        Raises:
            EventError: If publishing fails
        """
        pass

    @abstractmethod
    async def request(self, channel: str, data: dict, timeout: float = 5.0) -> dict:
        """Request-response pattern.
        
        Args:
            channel: Channel name
            data: Request data
            timeout: Timeout in seconds
            
        Returns:
            Response data from responder
            
        Raises:
            EventError: If request fails
            TimeoutError: If request times out
        """
        pass

    @abstractmethod
    async def respond(self, channel: str, handler: Callable[[dict], dict]) -> str:
        """Set up response handler for request-response pattern.
        
        Args:
            channel: Channel name
            handler: Response handler function
            
        Returns:
            Response handler ID
            
        Raises:
            EventError: If setup fails
        """
        pass

    @abstractmethod
    async def publish_instance_event(
        self,
        instance_id: str,
        event_type: str,
        data: dict,
    ) -> str:
        """Publish event to a specific trading instance's channel.
        
        Args:
            instance_id: Trading Instance ID
            event_type: Type of event
            data: Event data payload
            
        Returns:
            Event ID
            
        Raises:
            EventError: If publishing fails
        """
        pass

    @abstractmethod
    async def publish_market_event(
        self,
        symbol: str,
        exchange: str,
        event_type: str,
        data: dict,
    ) -> str:
        """Publish market data event.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name
            event_type: Type of event
            data: Event data payload
            
        Returns:
            Event ID
            
        Raises:
            EventError: If publishing fails
        """
        pass

    @abstractmethod
    async def publish_system_event(self, event_type: str, data: dict) -> str:
        """Publish system-wide event.
        
        Args:
            event_type: Type of event
            data: Event data payload
            
        Returns:
            Event ID
            
        Raises:
            EventError: If publishing fails
        """
        pass

    @abstractmethod
    async def get_event(self, event_id: str) -> Optional[Event]:
        """Get event by ID.
        
        Args:
            event_id: Event ID
            
        Returns:
            Event if found, None otherwise
            
        Raises:
            EventError: If retrieval fails
        """
        pass

    @abstractmethod
    async def get_events(
        self,
        channel: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[Event]:
        """Get events with optional filtering.
        
        Args:
            channel: Channel filter (optional)
            event_type: Event type filter (optional)
            start_time: Start time filter (optional)
            end_time: End time filter (optional)
            limit: Maximum number of events to return
            
        Returns:
            List of events
            
        Raises:
            EventError: If retrieval fails
        """
        pass

    @abstractmethod
    async def create_event_stream(
        self,
        channels: list[str],
        callback: Callable[[Event], None],
    ) -> str:
        """Create event stream for multiple channels.
        
        Args:
            channels: List of channel names
            callback: Callback function for events
            
        Returns:
            Stream ID
            
        Raises:
            EventError: If stream creation fails
        """
        pass

    @abstractmethod
    async def close_event_stream(self, stream_id: str) -> None:
        """Close event stream.
        
        Args:
            stream_id: Stream ID
            
        Raises:
            EventError: If stream closing fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check event bus health.
        
        Returns:
            True if event bus is healthy
        """
        pass

    @abstractmethod
    async def get_stats(self) -> dict:
        """Get event bus statistics.
        
        Returns:
            Statistics dictionary
        """
        pass
