"""Referral domain events."""

from typing import Optional

from .base import DomainEvent


class ReferralCreated(DomainEvent):
    """Event published when a referral is created."""

    @classmethod
    def create(
        cls,
        referral_id: str,
        referrer_id: str,
        referred_user_id: str,
        invite_source: Optional[str] = None
    ) -> "ReferralCreated":
        """Create ReferralCreated event."""
        return super().create(
            aggregate_id=referral_id,
            aggregate_type="Referral",
            referrer_id=referrer_id,
            referred_user_id=referred_user_id,
            invite_source=invite_source
        )


class ReferralActivated(DomainEvent):
    """Event published when a referral is activated."""

    @classmethod
    def create(
        cls,
        referral_id: str,
        referrer_id: str,
        referred_user_id: str
    ) -> "ReferralActivated":
        """Create ReferralActivated event."""
        return super().create(
            aggregate_id=referral_id,
            aggregate_type="Referral",
            referrer_id=referrer_id,
            referred_user_id=referred_user_id
        )


class ReferralRewardGranted(DomainEvent):
    """Event published when a referral reward is granted."""

    @classmethod
    def create(
        cls,
        referral_id: str,
        user_id: str,
        reward_type: str,
        bonus_days: int
    ) -> "ReferralRewardGranted":
        """Create ReferralRewardGranted event."""
        return super().create(
            aggregate_id=referral_id,
            aggregate_type="Referral",
            user_id=user_id,
            reward_type=reward_type,
            bonus_days=bonus_days
        )


class ReferralPurchaseMade(DomainEvent):
    """Event published when referred user makes first purchase."""

    @classmethod
    def create(
        cls,
        referral_id: str,
        referrer_id: str,
        referred_user_id: str,
        order_id: str,
        amount: float,
        currency: str
    ) -> "ReferralPurchaseMade":
        """Create ReferralPurchaseMade event."""
        return super().create(
            aggregate_id=referral_id,
            aggregate_type="Referral",
            referrer_id=referrer_id,
            referred_user_id=referred_user_id,
            order_id=order_id,
            amount=amount,
            currency=currency
        )