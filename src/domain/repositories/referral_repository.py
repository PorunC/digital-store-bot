"""Referral repository interface."""

import uuid
from abc import abstractmethod
from typing import List, Optional

from ..entities.referral import Referral, RewardType
from .base import Repository


class ReferralRepository(Repository[Referral]):
    """Referral repository interface."""

    @abstractmethod
    async def find_by_referrer(self, referrer_id: uuid.UUID) -> List[Referral]:
        """Find referrals by referrer ID."""
        pass

    @abstractmethod
    async def find_by_referred_user(self, referred_user_id: uuid.UUID) -> Optional[Referral]:
        """Find referral by referred user ID."""
        pass

    @abstractmethod
    async def find_active_referrals(self, referrer_id: uuid.UUID) -> List[Referral]:
        """Find active referrals by referrer ID."""
        pass

    @abstractmethod
    async def find_pending_rewards(self, reward_type: RewardType) -> List[Referral]:
        """Find referrals with pending rewards."""
        pass

    @abstractmethod
    async def get_referral_stats(self, referrer_id: uuid.UUID) -> dict:
        """Get referral statistics for a user."""
        pass