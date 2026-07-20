"""
Base interface for the Trading Engine.

This module defines the ITradingEngine interface that orchestrates
Trading Instances and manages their lifecycle.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal

from core.context import TradingContext
from core.domain_types import TradingInstance, TradingInstanceStatus


class ITradingEngine(ABC):
    """Interface for the Trading Engine.

    The Trading Engine orchestrates Trading Instances, manages lifecycle,
    and coordinates between different components.
    """

    @abstractmethod
    async def create_instance(
        self,
        context: TradingContext,
    ) -> TradingInstance:
        """Create a new Trading Instance in CREATED state.

        Does NOT allocate worker or subscribe market yet.

        Args:
            context: Trading context with all instance configuration

        Returns:
            Created TradingInstance

        Raises:
            ValidationError: If context is invalid
            DatabaseError: If creation fails
        """
        pass

    @abstractmethod
    async def prepare_instance(self, context: TradingContext) -> bool:
        """Transition CREATED -> READY.

        Performs:
        - API key validation
        - Balance check
        - Grid calculation
        - Order/position sync
        - Market subscription
        - Worker allocation
        - ProcessMemory initialization

        Args:
            context: Trading context

        Returns:
            True if preparation successful

        Raises:
            InvalidStateTransition: If instance is not in CREATED
            InsufficientBalanceError: If balance is insufficient
            ExchangeError: If exchange operations fail
            ValidationError: If configuration is invalid
        """
        pass

    @abstractmethod
    async def start_instance(self, context: TradingContext) -> bool:
        """Transition READY -> RUNNING.

        Args:
            context: Trading context

        Returns:
            True if start successful

        Raises:
            InvalidStateTransition: If instance is not in READY
            ExchangeError: If exchange operations fail
        """
        pass

    @abstractmethod
    async def stop_instance(
        self, context: TradingContext, reason: str = "user_requested"
    ) -> bool:
        """Transition RUNNING -> STOPPING -> STOPPED.

        Args:
            context: Trading context
            reason: Reason for stopping

        Returns:
            True if stop successful

        Raises:
            InvalidStateTransition: If instance is not in RUNNING
            ExchangeError: If exchange operations fail
        """
        pass

    @abstractmethod
    async def pause_instance(self, context: TradingContext) -> bool:
        """Transition RUNNING -> PAUSED.

        Args:
            context: Trading context

        Returns:
            True if pause successful

        Raises:
            InvalidStateTransition: If instance is not in RUNNING
            ExchangeError: If exchange operations fail
        """
        pass

    @abstractmethod
    async def resume_instance(self, context: TradingContext) -> bool:
        """Transition PAUSED -> RUNNING.

        Args:
            context: Trading context

        Returns:
            True if resume successful

        Raises:
            InvalidStateTransition: If instance is not in PAUSED
            ExchangeError: If exchange operations fail
        """
        pass

    @abstractmethod
    async def get_instance(self, instance_id: str) -> TradingInstance:
        """Get Trading Instance details.

        Args:
            instance_id: Trading Instance ID

        Returns:
            TradingInstance details

        Raises:
            TradingInstanceNotFound: If instance not found
            DatabaseError: If retrieval fails
        """
        pass

    @abstractmethod
    async def list_instances(
        self,
        user_id: str,
        status: TradingInstanceStatus | None = None,
    ) -> list[TradingInstance]:
        """List Trading Instances for a user.

        Args:
            user_id: User ID
            status: Optional status filter

        Returns:
            List of TradingInstances

        Raises:
            DatabaseError: If retrieval fails
        """
        pass

    @abstractmethod
    async def update_instance(
        self,
        instance_id: str,
        updates: dict,
    ) -> TradingInstance:
        """Update Trading Instance.

        Args:
            instance_id: Trading Instance ID
            updates: Dictionary of fields to update

        Returns:
            Updated TradingInstance

        Raises:
            TradingInstanceNotFound: If instance not found
            ValidationError: If updates are invalid
            DatabaseError: If update fails
        """
        pass

    @abstractmethod
    async def delete_instance(self, instance_id: str) -> bool:
        """Delete Trading Instance.

        Args:
            instance_id: Trading Instance ID

        Returns:
            True if deletion successful

        Raises:
            TradingInstanceNotFound: If instance not found
            InvalidStateTransition: If instance is not in stopped state
            DatabaseError: If deletion fails
        """
        pass

    @abstractmethod
    async def recover_instance(self, context: TradingContext) -> bool:
        """Recover a Trading Instance from ERROR state.

        Args:
            context: Trading context

        Returns:
            True if recovery successful

        Raises:
            TradingInstanceNotFound: If instance not found
            InvalidStateTransition: If instance is not in ERROR
            ExchangeError: If exchange operations fail
        """
        pass

    @abstractmethod
    async def sync_instance_state(self, context: TradingContext) -> bool:
        """Synchronize instance state with exchange.

        Args:
            context: Trading context

        Returns:
            True if sync successful

        Raises:
            TradingInstanceNotFound: If instance not found
            ExchangeError: If exchange operations fail
        """
        pass

    @abstractmethod
    async def get_instance_performance(
        self,
        instance_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        """Get performance metrics for a Trading Instance.

        Args:
            instance_id: Trading Instance ID
            start_date: Start date for performance period
            end_date: End date for performance period

        Returns:
            Performance metrics dictionary

        Raises:
            TradingInstanceNotFound: If instance not found
            DatabaseError: If retrieval fails
        """
        pass

    @abstractmethod
    async def get_instance_positions(self, instance_id: str) -> list[dict]:
        """Get positions for a Trading Instance.

        Args:
            instance_id: Trading Instance ID

        Returns:
            List of position dictionaries

        Raises:
            TradingInstanceNotFound: If instance not found
            DatabaseError: If retrieval fails
        """
        pass

    @abstractmethod
    async def get_instance_orders(
        self,
        instance_id: str,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Get orders for a Trading Instance.

        Args:
            instance_id: Trading Instance ID
            status: Optional order status filter
            limit: Maximum number of orders to return

        Returns:
            List of order dictionaries

        Raises:
            TradingInstanceNotFound: If instance not found
            DatabaseError: If retrieval fails
        """
        pass

    @abstractmethod
    async def validate_instance_config(self, config: dict) -> bool:
        """Validate Trading Instance configuration.

        Args:
            config: Configuration dictionary

        Returns:
            True if configuration is valid

        Raises:
            ValidationError: If configuration is invalid
        """
        pass

    @abstractmethod
    async def calculate_grid_parameters(
        self,
        upper_price: Decimal,
        lower_price: Decimal,
        grid_count: int,
        total_investment: Decimal,
    ) -> dict:
        """Calculate grid parameters.

        Args:
            upper_price: Upper grid price
            lower_price: Lower grid price
            grid_count: Number of grid levels
            total_investment: Total investment amount

        Returns:
            Grid parameters dictionary

        Raises:
            ValidationError: If parameters are invalid
        """
        pass

    @abstractmethod
    async def health_check(self) -> dict:
        """Check Trading Engine health.

        Returns:
            Health status dictionary
        """
        pass

    @abstractmethod
    async def get_engine_stats(self) -> dict:
        """Get Trading Engine statistics.

        Returns:
            Engine statistics dictionary
        """
        pass
