"""Enhanced User domain entity with complete feature set."""

from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from pydantic import Field, validator

from ..events.user_events import (
    UserRegistered,
    UserTrialStarted,
    UserSubscriptionExtended,
    UserBlocked,
    UserUnblocked,
    UserProfileUpdated
)
from ..value_objects.user_profile import UserProfile
from .base import AggregateRoot


class UserStatus(str, Enum):
    """User status enumeration."""
    ACTIVE = "active"
    BLOCKED = "blocked"
    INACTIVE = "inactive"


class SubscriptionType(str, Enum):
    """Subscription type enumeration."""
    TRIAL = "trial"
    PREMIUM = "premium"
    EXTENDED = "extended"


class User(AggregateRoot):
    """Enhanced User aggregate root with complete functionality."""

    telegram_id: int = Field(..., gt=0)
    profile: UserProfile
    language_code: str = Field(default="en", max_length=5)
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    
    # Trial system
    is_trial_used: bool = Field(default=False)
    trial_expires_at: Optional[datetime] = None
    trial_type: Optional[SubscriptionType] = None
    
    # Subscription system
    subscription_expires_at: Optional[datetime] = None
    subscription_type: Optional[SubscriptionType] = None
    total_subscription_days: int = Field(default=0, ge=0)
    
    # Referral system
    referrer_id: Optional[str] = None
    invite_source: Optional[str] = None  # For tracking invite attribution
    total_referrals: int = Field(default=0, ge=0)
    
    # Statistics
    total_orders: int = Field(default=0, ge=0)
    total_spent_amount: float = Field(default=0.0, ge=0)
    total_spent_currency: str = Field(default="USD")
    last_active_at: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        telegram_id: int,
        first_name: str,
        username: Optional[str] = None,
        language_code: str = "en",
        referrer_id: Optional[str] = None,
        invite_source: Optional[str] = None,
    ) -> "User":
        """Create a new user with proper event publishing."""
        profile = UserProfile(
            first_name=first_name,
            username=username
        )
        
        user = cls(
            telegram_id=telegram_id,
            profile=profile,
            language_code=language_code,
            referrer_id=referrer_id,
            invite_source=invite_source,
            last_active_at=datetime.utcnow()
        )
        
        # Publish domain event
        event = UserRegistered.create(
            user_id=str(user.id),
            telegram_id=telegram_id,
            first_name=first_name,
            username=username,
            referrer_id=referrer_id,
            invite_source=invite_source
        )
        user.add_domain_event(event)
        
        return user

    def start_trial(
        self,
        trial_period_days: int,
        trial_type: SubscriptionType = SubscriptionType.TRIAL
    ) -> None:
        """Start trial period for the user."""
        if self.is_trial_used and trial_type == SubscriptionType.TRIAL:
            raise ValueError("Regular trial has already been used")
        
        if trial_type == SubscriptionType.TRIAL:
            self.is_trial_used = True
            
        # Set trial expiration to end of day
        expires_at = datetime.utcnow().replace(
            hour=23, minute=59, second=59, microsecond=999999
        ) + timedelta(days=trial_period_days)
        
        self.trial_expires_at = expires_at
        self.trial_type = trial_type
        self.mark_updated()
        
        # Publish domain event
        event = UserTrialStarted.create(
            user_id=str(self.id),
            trial_type=trial_type.value,
            trial_expires_at=expires_at,
            trial_period_days=trial_period_days
        )
        self.add_domain_event(event)

    def extend_subscription(
        self,
        days: int,
        subscription_type: SubscriptionType = SubscriptionType.PREMIUM
    ) -> None:
        """Extend user subscription."""
        if days <= 0:
            raise ValueError("Extension days must be positive")
            
        # Calculate new expiration date
        now = datetime.utcnow()
        if self.subscription_expires_at and self.subscription_expires_at > now:
            # Extend from current expiration
            new_expiry = self.subscription_expires_at + timedelta(days=days)
        else:
            # Start from now
            new_expiry = now.replace(
                hour=23, minute=59, second=59, microsecond=999999
            ) + timedelta(days=days)
        
        old_expiry = self.subscription_expires_at
        self.subscription_expires_at = new_expiry
        self.subscription_type = subscription_type
        self.total_subscription_days += days
        self.mark_updated()
        
        # Publish domain event
        event = UserSubscriptionExtended.create(
            user_id=str(self.id),
            days_extended=days,
            subscription_type=subscription_type.value,
            old_expiry_date=old_expiry,
            new_expiry_date=new_expiry
        )
        self.add_domain_event(event)

    def block(self, reason: Optional[str] = None) -> None:
        """Block the user."""
        if self.status == UserStatus.BLOCKED:
            return
            
        self.status = UserStatus.BLOCKED
        self.mark_updated()
        
        event = UserBlocked.create(
            user_id=str(self.id),
            reason=reason
        )
        self.add_domain_event(event)

    def unblock(self) -> None:
        """Unblock the user."""
        if self.status != UserStatus.BLOCKED:
            return
            
        self.status = UserStatus.ACTIVE
        self.mark_updated()
        
        event = UserUnblocked.create(user_id=str(self.id))
        self.add_domain_event(event)

    def update_profile(
        self,
        first_name: Optional[str] = None,
        username: Optional[str] = None,
        language_code: Optional[str] = None
    ) -> None:
        """Update user profile."""
        old_profile = self.profile
        
        if first_name is not None or username is not None:
            self.profile = UserProfile(
                first_name=first_name or self.profile.first_name,
                username=username or self.profile.username
            )
            
        if language_code is not None:
            self.language_code = language_code
            
        self.mark_updated()
        
        # Publish domain event
        event = UserProfileUpdated.create(
            user_id=str(self.id),
            old_first_name=old_profile.first_name,
            new_first_name=self.profile.first_name,
            old_username=old_profile.username,
            new_username=self.profile.username,
            old_language_code=self.language_code if language_code else None,
            new_language_code=language_code
        )
        self.add_domain_event(event)

    def record_activity(self) -> None:
        """Record user activity."""
        self.last_active_at = datetime.utcnow()
        self.mark_updated()

    def increment_referrals(self) -> None:
        """Increment total referrals count."""
        self.total_referrals += 1
        self.mark_updated()

    def record_purchase(self, amount: float, currency: str) -> None:
        """Record a purchase."""
        self.total_orders += 1
        
        # Convert to base currency if needed (simplified)
        if currency == self.total_spent_currency:
            self.total_spent_amount += amount
        else:
            # In a real system, you'd convert currencies
            self.total_spent_amount += amount
            self.total_spent_currency = currency
            
        self.mark_updated()

    def can_use_trial(self, trial_type: SubscriptionType = SubscriptionType.TRIAL) -> bool:
        """Check if user can use trial."""
        if trial_type == SubscriptionType.TRIAL:
            return not self.is_trial_used
        return True  # Other trial types (like referred) can be used multiple times

    @property
    def has_active_trial(self) -> bool:
        """Check if user has active trial."""
        if not self.trial_expires_at:
            return False
        return datetime.utcnow() < self.trial_expires_at

    @property
    def has_active_subscription(self) -> bool:
        """Check if user has active subscription."""
        if not self.subscription_expires_at:
            return False
        return datetime.utcnow() < self.subscription_expires_at

    @property
    def is_premium(self) -> bool:
        """Check if user has premium access (trial or subscription)."""
        return self.has_active_trial or self.has_active_subscription

    @property
    def is_blocked(self) -> bool:
        """Check if user is blocked."""
        return self.status == UserStatus.BLOCKED

    @property
    def is_new_user(self) -> bool:
        """Check if user is new (no orders)."""
        return self.total_orders == 0

    @property
    def premium_expires_at(self) -> Optional[datetime]:
        """Get when premium access expires (trial or subscription)."""
        trial_expiry = self.trial_expires_at
        subscription_expiry = self.subscription_expires_at
        
        # Return the latest expiry date
        if trial_expiry and subscription_expiry:
            return max(trial_expiry, subscription_expiry)
        return trial_expiry or subscription_expiry

    @property
    def days_until_expiry(self) -> Optional[int]:
        """Get days until premium access expires."""
        expiry = self.premium_expires_at
        if not expiry:
            return None
            
        now = datetime.utcnow()
        if expiry <= now:
            return 0
            
        return (expiry - now).days

    @property
    def is_vip(self) -> bool:
        """Check if user is VIP (high value customer)."""
        return (
            self.total_orders >= 5 or
            self.total_spent_amount >= 1000 or
            self.total_referrals >= 10
        )

    @validator("telegram_id")
    def validate_telegram_id(cls, v):
        """Validate Telegram ID."""
        if v <= 0:
            raise ValueError("Telegram ID must be positive")
        return v

    @validator("language_code")
    def validate_language_code(cls, v):
        """Validate language code."""
        if not v or len(v) < 2:
            raise ValueError("Language code must be at least 2 characters")
        return v.lower()

    @validator("total_spent_amount")
    def validate_total_spent_amount(cls, v):
        """Validate total spent amount."""
        if v < 0:
            raise ValueError("Total spent amount cannot be negative")
        return v