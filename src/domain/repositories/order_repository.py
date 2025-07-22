"""Order repository interface."""

from abc import abstractmethod
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from ..entities.order import Order, OrderStatus
from .base import Repository


class OrderRepository(Repository[Order]):
    """Order repository interface."""

    @abstractmethod
    async def find_by_user_id(self, user_id: UUID) -> List[Order]:
        """Find orders by user ID."""
        pass

    @abstractmethod
    async def find_by_status(self, status: OrderStatus) -> List[Order]:
        """Find orders by status."""
        pass

    @abstractmethod
    async def find_by_payment_id(self, payment_id: str) -> Optional[Order]:
        """Find order by payment ID."""
        pass

    @abstractmethod
    async def find_expired(self) -> List[Order]:
        """Find expired orders."""
        pass

    @abstractmethod
    async def find_pending_orders(self, user_id: UUID) -> List[Order]:
        """Find pending orders for a user."""
        pass

    @abstractmethod
    async def get_revenue_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Get revenue statistics."""
        pass

    @abstractmethod
    async def get_order_stats(self) -> dict:
        """Get order statistics."""
        pass