"""User repository interface."""

from abc import abstractmethod
from typing import List, Optional

from ..entities.user import User
from .base import Repository


class UserRepository(Repository[User]):
    """User repository interface."""

    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        pass

    @abstractmethod
    async def find_by_referrer_id(self, referrer_id: str) -> List[User]:
        """Find users referred by a specific user."""
        pass

    @abstractmethod
    async def find_by_status(self, status: str) -> List[User]:
        """Find users by status."""
        pass

    @abstractmethod
    async def find_premium_users(self) -> List[User]:
        """Find users with active premium subscriptions."""
        pass

    @abstractmethod
    async def find_expiring_users(self, days: int) -> List[User]:
        """Find users whose premium expires within specified days."""
        pass

    @abstractmethod
    async def get_user_statistics(self) -> dict:
        """Get user statistics."""
        pass