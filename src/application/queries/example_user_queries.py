"""Example query handlers for CQRS pattern implementation.

This module demonstrates query handlers that retrieve data without modifying state.
Queries are used for read operations and data retrieval.
"""

from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

from src.domain.entities.user import User
from src.domain.entities.order import Order
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.infrastructure.database.repositories.order_repository import OrderRepository


# Query Data Transfer Objects (DTOs)
@dataclass
class GetUserByIdQuery:
    """Query to get user by ID."""
    user_id: str


@dataclass
class GetUserOrdersQuery:
    """Query to get user's orders."""
    user_id: str
    limit: Optional[int] = 50
    offset: Optional[int] = 0


@dataclass
class GetActiveUsersQuery:
    """Query to get active users."""
    since_date: datetime
    limit: Optional[int] = 100


@dataclass
class UserStatsQuery:
    """Query to get user statistics."""
    user_id: Optional[str] = None  # If None, get global stats


# Query Result DTOs
@dataclass
class UserStatsResult:
    """Result for user statistics query."""
    total_orders: int
    total_spent: float
    currency: str
    registration_date: datetime
    last_activity: Optional[datetime]
    subscription_type: Optional[str]
    subscription_expires: Optional[datetime]


# Query Handlers
class UserQueryHandler:
    """Handler for user-related queries."""
    
    def __init__(
        self,
        user_repository: UserRepository,
        order_repository: OrderRepository
    ):
        self.user_repository = user_repository
        self.order_repository = order_repository
    
    async def handle_get_user_by_id(self, query: GetUserByIdQuery) -> Optional[User]:
        """Handle get user by ID query."""
        return await self.user_repository.get_by_id(query.user_id)
    
    async def handle_get_user_orders(self, query: GetUserOrdersQuery) -> List[Order]:
        """Handle get user orders query."""
        return await self.order_repository.get_by_user_id(
            query.user_id,
            limit=query.limit,
            offset=query.offset
        )
    
    async def handle_get_active_users(self, query: GetActiveUsersQuery) -> List[User]:
        """Handle get active users query."""
        return await self.user_repository.get_active_users_since(
            query.since_date,
            limit=query.limit
        )
    
    async def handle_user_stats(self, query: UserStatsQuery) -> UserStatsResult:
        """Handle user statistics query."""
        if query.user_id:
            user = await self.user_repository.get_by_id(query.user_id)
            if not user:
                raise ValueError(f"User {query.user_id} not found")
            
            orders = await self.order_repository.get_by_user_id(user.id)
            total_spent = sum(order.amount.amount for order in orders)
            
            return UserStatsResult(
                total_orders=len(orders),
                total_spent=total_spent,
                currency="USD",  # Get from user settings
                registration_date=user.created_at,
                last_activity=user.last_activity_at,
                subscription_type=user.subscription.type if user.subscription else None,
                subscription_expires=user.subscription.expires_at if user.subscription else None
            )
        else:
            # Global stats implementation
            total_users = await self.user_repository.count_all()
            return UserStatsResult(
                total_orders=0,  # Implement global stats
                total_spent=0.0,
                currency="USD",
                registration_date=datetime.now(),
                last_activity=None,
                subscription_type=None,
                subscription_expires=None
            )


# Example usage:
"""
# In your service layer or controller:

query_handler = UserQueryHandler(user_repository, order_repository)

# Get user by ID
user_query = GetUserByIdQuery(user_id="123")
user = await query_handler.handle_get_user_by_id(user_query)

# Get user orders
orders_query = GetUserOrdersQuery(user_id="123", limit=10)
orders = await query_handler.handle_get_user_orders(orders_query)

# Get user statistics
stats_query = UserStatsQuery(user_id="123")
stats = await query_handler.handle_user_stats(stats_query)
"""