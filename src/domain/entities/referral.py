"""Referral domain entity with complete functionality."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, validator

from ..events.referral_events import (
    ReferralCreated,
    ReferralRewardGranted,
    ReferralActivated
)
from .base import AggregateRoot


class ReferralStatus(str, Enum):
    """Referral status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    REWARDED = "rewarded"
    EXPIRED = "expired"


class Referral(AggregateRoot):
    """Referral aggregate root."""

    referrer_id: UUID
    referred_user_id: UUID
    
    # Reward tracking for referred user
    referred_rewarded_at: Optional[datetime] = None
    referred_bonus_days: int = Field(default=0, ge=0)
    
    # Reward tracking for referrer
    referrer_rewarded_at: Optional[datetime] = None
    referrer_bonus_days: int = Field(default=0, ge=0)
    
    # Additional tracking
    invite_source: Optional[str] = None
    status: ReferralStatus = Field(default=ReferralStatus.PENDING)
    first_purchase_at: Optional[datetime] = None
    total_referrer_rewards: int = Field(default=0, ge=0)

    @classmethod
    def create(
        cls,
        referrer_id: UUID,
        referred_user_id: UUID,
        invite_source: Optional[str] = None
    ) -> "Referral":
        """Create a new referral."""
        referral = cls(
            referrer_id=referrer_id,
            referred_user_id=referred_user_id,
            invite_source=invite_source
        )
        
        # Publish domain event
        event = ReferralCreated.create(
            referral_id=str(referral.id),
            referrer_id=str(referrer_id),
            referred_user_id=str(referred_user_id),
            invite_source=invite_source
        )
        referral.add_domain_event(event)
        
        return referral

    def activate(self) -> None:
        """Activate the referral."""
        if self.status != ReferralStatus.PENDING:
            return
            
        self.status = ReferralStatus.ACTIVE
        self.mark_updated()
        
        event = ReferralActivated.create(
            referral_id=str(self.id),
            referrer_id=str(self.referrer_id),
            referred_user_id=str(self.referred_user_id)
        )
        self.add_domain_event(event)

    def grant_referred_reward(self, bonus_days: int) -> None:
        """Grant reward to the referred user."""
        if self.referred_rewarded_at is not None:
            raise ValueError("Referred user already rewarded")
            
        if bonus_days <= 0:
            raise ValueError("Bonus days must be positive")
            
        self.referred_bonus_days = bonus_days
        self.referred_rewarded_at = datetime.utcnow()
        self.mark_updated()
        
        event = ReferralRewardGranted.create(
            referral_id=str(self.id),
            user_id=str(self.referred_user_id),
            reward_type="trial_extension",
            bonus_days=bonus_days
        )
        self.add_domain_event(event)

    def grant_referrer_reward(self, bonus_days: int) -> None:
        """Grant reward to the referrer."""
        if bonus_days <= 0:
            raise ValueError("Bonus days must be positive")
            
        self.referrer_bonus_days += bonus_days
        self.referrer_rewarded_at = datetime.utcnow()
        self.total_referrer_rewards += bonus_days
        
        if self.status == ReferralStatus.ACTIVE:
            self.status = ReferralStatus.REWARDED
            
        self.mark_updated()
        
        event = ReferralRewardGranted.create(
            referral_id=str(self.id),
            user_id=str(self.referrer_id),
            reward_type="referrer_bonus",
            bonus_days=bonus_days
        )
        self.add_domain_event(event)

    def record_first_purchase(self) -> None:
        """Record when referred user makes first purchase."""
        if self.first_purchase_at is not None:
            return  # Already recorded
            
        self.first_purchase_at = datetime.utcnow()
        self.mark_updated()

    @property
    def has_referred_been_rewarded(self) -> bool:
        """Check if referred user has been rewarded."""
        return self.referred_rewarded_at is not None

    @property
    def has_referrer_been_rewarded(self) -> bool:
        """Check if referrer has been rewarded."""
        return self.referrer_rewarded_at is not None

    @property
    def is_active(self) -> bool:
        """Check if referral is active."""
        return self.status == ReferralStatus.ACTIVE

    @property
    def days_since_creation(self) -> int:
        """Get days since referral was created."""
        delta = datetime.utcnow() - self.created_at
        return delta.days

    def can_grant_referrer_reward(self) -> bool:
        """Check if referrer reward can be granted."""
        return (
            self.status in [ReferralStatus.ACTIVE, ReferralStatus.REWARDED] and
            self.first_purchase_at is not None
        )

    @validator("referrer_id")
    def validate_referrer_id(cls, v, values):
        """Validate that referrer is not the same as referred user."""
        referred_user_id = values.get("referred_user_id")
        if v == referred_user_id:
            raise ValueError("Referrer cannot be the same as referred user")
        return v