"""
Base interface for the Grid Engine.

This module defines the IGridEngine interface that manages grid levels,
calculates prices, and handles grid fills.
"""

from abc import ABC, abstractmethod
from decimal import Decimal

from core.domain_types import GridLevel, GridState


class IGridEngine(ABC):
    """Interface for the Grid Engine.

    The Grid Engine manages grid levels, calculates prices, and handles
    grid fills for grid trading strategies.
    """

    @abstractmethod
    async def initialize_grid(
        self,
        instance_id: str,
        upper_price: Decimal,
        lower_price: Decimal,
        grid_count: int,
        investment_per_grid: Decimal,
    ) -> GridState:
        """Initialize grid levels for a Trading Instance.

        Args:
            instance_id: Trading Instance ID
            upper_price: Upper grid price
            lower_price: Lower grid price
            grid_count: Number of grid levels
            investment_per_grid: Investment amount per grid level

        Returns:
            Initialized GridState

        Raises:
            ValidationError: If parameters are invalid
            GridError: If initialization fails
        """
        pass

    @abstractmethod
    async def activate_grid(self, instance_id: str) -> bool:
        """Activate all grid levels (place orders).

        Args:
            instance_id: Trading Instance ID

        Returns:
            True if activation successful

        Raises:
            GridError: If activation fails
            InvalidStateTransition: If grid is not in initialized state
        """
        pass

    @abstractmethod
    async def pause_grid(self, instance_id: str) -> bool:
        """Pause grid (cancel pending orders).

        Args:
            instance_id: Trading Instance ID

        Returns:
            True if pause successful

        Raises:
            GridError: If pause fails
            InvalidStateTransition: If grid is not in active state
        """
        pass

    @abstractmethod
    async def resume_grid(self, instance_id: str) -> bool:
        """Resume grid (re-place orders).

        Args:
            instance_id: Trading Instance ID

        Returns:
            True if resume successful

        Raises:
            GridError: If resume fails
            InvalidStateTransition: If grid is not in paused state
        """
        pass

    @abstractmethod
    async def on_buy_filled(
        self, instance_id: str, grid_level: int, fill_price: Decimal, quantity: Decimal
    ) -> None:
        """Handle buy order filled event. Place corresponding sell order.

        Args:
            instance_id: Trading Instance ID
            grid_level: Grid level that was filled
            fill_price: Actual fill price
            quantity: Filled quantity

        Raises:
            GridError: If handling fails
            ValidationError: If parameters are invalid
        """
        pass

    @abstractmethod
    async def on_sell_filled(
        self, instance_id: str, grid_level: int, fill_price: Decimal, quantity: Decimal
    ) -> None:
        """Handle sell order filled event. Place corresponding buy order.

        Args:
            instance_id: Trading Instance ID
            grid_level: Grid level that was filled
            fill_price: Actual fill price
            quantity: Filled quantity

        Raises:
            GridError: If handling fails
            ValidationError: If parameters are invalid
        """
        pass

    @abstractmethod
    async def update_grid_parameters(
        self,
        instance_id: str,
        upper_price: Decimal | None = None,
        lower_price: Decimal | None = None,
        grid_count: int | None = None,
    ) -> GridState:
        """Update grid parameters (only when paused).

        Args:
            instance_id: Trading Instance ID
            upper_price: New upper price (optional)
            lower_price: New lower price (optional)
            grid_count: New grid count (optional)

        Returns:
            Updated GridState

        Raises:
            GridError: If update fails
            InvalidStateTransition: If grid is not in paused state
            ValidationError: If parameters are invalid
        """
        pass

    @abstractmethod
    async def get_grid_state(self, instance_id: str) -> GridState:
        """Get current grid state.

        Args:
            instance_id: Trading Instance ID

        Returns:
            Current GridState

        Raises:
            GridError: If retrieval fails
        """
        pass

    @abstractmethod
    async def close_all_grid_orders(self, instance_id: str) -> bool:
        """Cancel all grid orders.

        Args:
            instance_id: Trading Instance ID

        Returns:
            True if cancellation successful

        Raises:
            GridError: If cancellation fails
        """
        pass

    @abstractmethod
    async def get_grid_level(self, instance_id: str, level: int) -> GridLevel | None:
        """Get specific grid level.

        Args:
            instance_id: Trading Instance ID
            level: Grid level number

        Returns:
            GridLevel if found, None otherwise

        Raises:
            GridError: If retrieval fails
        """
        pass

    @abstractmethod
    async def get_grid_levels(self, instance_id: str) -> list[GridLevel]:
        """Get all grid levels.

        Args:
            instance_id: Trading Instance ID

        Returns:
            List of GridLevel objects

        Raises:
            GridError: If retrieval fails
        """
        pass

    @abstractmethod
    async def calculate_grid_prices(
        self,
        upper_price: Decimal,
        lower_price: Decimal,
        grid_count: int,
    ) -> list[Decimal]:
        """Calculate grid prices.

        Args:
            upper_price: Upper grid price
            lower_price: Lower grid price
            grid_count: Number of grid levels

        Returns:
            List of grid prices

        Raises:
            ValidationError: If parameters are invalid
        """
        pass

    @abstractmethod
    async def calculate_investment_per_grid(
        self,
        total_investment: Decimal,
        grid_count: int,
    ) -> Decimal:
        """Calculate investment amount per grid level.

        Args:
            total_investment: Total investment amount
            grid_count: Number of grid levels

        Returns:
            Investment amount per grid level

        Raises:
            ValidationError: If parameters are invalid
        """
        pass

    @abstractmethod
    async def get_grid_performance(self, instance_id: str) -> dict:
        """Get grid performance metrics.

        Args:
            instance_id: Trading Instance ID

        Returns:
            Performance metrics dictionary

        Raises:
            GridError: If retrieval fails
        """
        pass

    @abstractmethod
    async def validate_grid_parameters(
        self,
        upper_price: Decimal,
        lower_price: Decimal,
        grid_count: int,
        investment_per_grid: Decimal,
    ) -> bool:
        """Validate grid parameters.

        Args:
            upper_price: Upper grid price
            lower_price: Lower grid price
            grid_count: Number of grid levels
            investment_per_grid: Investment amount per grid level

        Returns:
            True if parameters are valid

        Raises:
            ValidationError: If parameters are invalid
        """
        pass

    @abstractmethod
    async def get_grid_statistics(self, instance_id: str) -> dict:
        """Get grid statistics.

        Args:
            instance_id: Trading Instance ID

        Returns:
            Grid statistics dictionary

        Raises:
            GridError: If retrieval fails
        """
        pass

    @abstractmethod
    async def reset_grid(self, instance_id: str) -> GridState:
        """Reset grid to initial state.

        Args:
            instance_id: Trading Instance ID

        Returns:
            Reset GridState

        Raises:
            GridError: If reset fails
            InvalidStateTransition: If grid is not in paused state
        """
        pass

    @abstractmethod
    async def optimize_grid_parameters(
        self,
        instance_id: str,
        historical_data: list[dict],
    ) -> dict:
        """Optimize grid parameters based on historical data.

        Args:
            instance_id: Trading Instance ID
            historical_data: Historical price data

        Returns:
            Optimized parameters dictionary

        Raises:
            GridError: If optimization fails
            ValidationError: If historical data is invalid
        """
        pass
