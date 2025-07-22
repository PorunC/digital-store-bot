"""Enhanced user domain events."""

from datetime import datetime
from typing import Optional

from .base import DomainEvent


class UserRegistered(DomainEvent):
    """Event published when a user registers."""

    @classmethod
    def create(
        cls,
        user_id: str,
        telegram_id: int,
        first_name: str,
        username: Optional[str] = None,
        referrer_id: Optional[str] = None,
        invite_source: Optional[str] = None
    ) -> "UserRegistered":
        """Create UserRegistered event."""
        return super().create(
            aggregate_id=user_id,
            aggregate_type="User",
            telegram_id=telegram_id,
            first_name=first_name,
            username=username,
            referrer_id=referrer_id,
            invite_source=invite_source
        )


class UserTrialStarted(DomainEvent):
    """Event published when a user starts a trial."""

    @classmethod
    def create(
        cls,
        user_id: str,
        trial_type: str,
        trial_expires_at: datetime,
        trial_period_days: int
    ) -> "UserTrialStarted":
        """Create UserTrialStarted event."""
        return super().create(
            aggregate_id=user_id,
            aggregate_type="User",
            trial_type=trial_type,
            trial_expires_at=trial_expires_at.isoformat(),
            trial_period_days=trial_period_days
        )


class UserSubscriptionExtended(DomainEvent):
    """Event published when a user's subscription is extended."""

    @classmethod
    def create(
        cls,
        user_id: str,
        days_extended: int,
        subscription_type: str,
        old_expiry_date: Optional[datetime],
        new_expiry_date: datetime
    ) -> "UserSubscriptionExtended":
        """Create UserSubscriptionExtended event."""
        return super().create(
            aggregate_id=user_id,
            aggregate_type="User",
            days_extended=days_extended,
            subscription_type=subscription_type,
            old_expiry_date=old_expiry_date.isoformat() if old_expiry_date else None,
            new_expiry_date=new_expiry_date.isoformat()
        )


class UserBlocked(DomainEvent):
    """Event published when a user is blocked."""

    @classmethod
    def create(
        cls,
        user_id: str,
        reason: Optional[str] = None
    ) -> "UserBlocked":
        """Create UserBlocked event."""
        return super().create(
            aggregate_id=user_id,
            aggregate_type="User",
            reason=reason
        )


class UserUnblocked(DomainEvent):
    """Event published when a user is unblocked."""

    @classmethod
    def create(cls, user_id: str) -> "UserUnblocked":
        """Create UserUnblocked event."""
        return super().create(
            aggregate_id=user_id,
            aggregate_type="User"
        )


class UserProfileUpdated(DomainEvent):
    """Event published when a user's profile is updated."""

    @classmethod
    def create(
        cls,
        user_id: str,
        old_first_name: str,
        new_first_name: str,
        old_username: Optional[str],
        new_username: Optional[str],
        old_language_code: Optional[str],
        new_language_code: Optional[str]
    ) -> "UserProfileUpdated":
        """Create UserProfileUpdated event."""
        return super().create(
            aggregate_id=user_id,
            aggregate_type="User",
            old_first_name=old_first_name,
            new_first_name=new_first_name,
            old_username=old_username,
            new_username=new_username,
            old_language_code=old_language_code,
            new_language_code=new_language_code
        )


class UserActivityRecorded(DomainEvent):
    """Event published when user activity is recorded."""

    @classmethod
    def create(
        cls,
        user_id: str,
        activity_type: str,
        activity_data: Optional[dict] = None
    ) -> "UserActivityRecorded":
        """Create UserActivityRecorded event."""
        return super().create(
            aggregate_id=user_id,
            aggregate_type="User",
            activity_type=activity_type,
            activity_data=activity_data or {}
        )


class UserPurchaseRecorded(DomainEvent):
    """Event published when a user makes a purchase."""

    @classmethod
    def create(
        cls,
        user_id: str,
        order_id: str,
        amount: float,
        currency: str,
        product_id: str
    ) -> "UserPurchaseRecorded":
        """Create UserPurchaseRecorded event."""
        return super().create(
            aggregate_id=user_id,
            aggregate_type="User",
            order_id=order_id,
            amount=amount,
            currency=currency,
            product_id=product_id
        )


class UserReferralRecorded(DomainEvent):
    """Event published when a user makes a referral."""

    @classmethod
    def create(
        cls,
        referrer_id: str,
        referred_user_id: str,
        invite_source: Optional[str] = None
    ) -> "UserReferralRecorded":
        """Create UserReferralRecorded event."""
        return super().create(
            aggregate_id=referrer_id,
            aggregate_type="User",
            referred_user_id=referred_user_id,
            invite_source=invite_source
        )