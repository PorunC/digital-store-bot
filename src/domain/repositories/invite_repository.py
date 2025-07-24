"""Invite repository interface."""

from abc import abstractmethod
from typing import List, Optional

from ..entities.invite import Invite
from .base import Repository


class InviteRepository(Repository[Invite]):
    """Invite repository interface."""

    @abstractmethod
    async def find_by_hash(self, hash_code: str) -> Optional[Invite]:
        """Find invite by hash code."""
        pass

    @abstractmethod
    async def find_by_name(self, name: str) -> Optional[Invite]:
        """Find invite by name."""
        pass

    @abstractmethod
    async def find_active_invites(self) -> List[Invite]:
        """Find active invites."""
        pass

    @abstractmethod
    async def find_by_campaign(self, campaign: str) -> List[Invite]:
        """Find invites by campaign."""
        pass

    @abstractmethod
    async def find_expired_invites(self) -> List[Invite]:
        """Find expired invites."""
        pass

    @abstractmethod
    async def search_invites(self, query: str) -> List[Invite]:
        """Search invites by query."""
        pass

    @abstractmethod
    async def get_top_performing_invites(self, limit: int = 10, days: int = 30) -> List[Invite]:
        """Get top performing invites."""
        pass

    @abstractmethod
    async def get_invite_stats(self) -> dict:
        """Get invite statistics."""
        pass