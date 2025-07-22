"""Unit tests for User domain entity."""

import pytest
from datetime import datetime, timedelta

from src.domain.entities.user import User, SubscriptionType, UserStatus
from src.domain.events.user_events import (
    UserRegistered,
    SubscriptionExtended,
    TrialStarted,
    UserBlocked
)


class TestUser:
    """Test User entity."""
    
    def test_create_user(self, sample_user_data):
        """Test user creation."""
        user = User.create(
            telegram_id=sample_user_data["telegram_id"],
            first_name=sample_user_data["first_name"],
            last_name=sample_user_data["last_name"],
            username=sample_user_data["username"],
            language_code=sample_user_data["language_code"]
        )
        
        assert user.telegram_id == sample_user_data["telegram_id"]
        assert user.profile.first_name == sample_user_data["first_name"]
        assert user.profile.last_name == sample_user_data["last_name"]
        assert user.profile.username == sample_user_data["username"]
        assert user.profile.language_code == sample_user_data["language_code"]
        assert user.subscription_type == SubscriptionType.FREE
        assert user.status == UserStatus.ACTIVE
        assert user.total_spent == 0.0
        assert user.total_referrals == 0
        
        # Check domain events
        events = user.get_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], UserRegistered)
    
    def test_start_trial(self, sample_user):
        """Test starting trial subscription."""
        sample_user.start_trial(7, SubscriptionType.TRIAL)
        
        assert sample_user.subscription_type == SubscriptionType.TRIAL
        assert sample_user.subscription_expires_at is not None
        
        # Check expiry is approximately 7 days from now
        expected_expiry = datetime.utcnow() + timedelta(days=7)
        time_diff = abs((sample_user.subscription_expires_at - expected_expiry).total_seconds())
        assert time_diff < 60  # Within 1 minute tolerance
        
        # Check domain events
        events = sample_user.get_domain_events()
        trial_events = [e for e in events if isinstance(e, TrialStarted)]
        assert len(trial_events) == 1
    
    def test_extend_subscription(self, sample_user):
        """Test extending subscription."""
        initial_expiry = datetime.utcnow() + timedelta(days=10)
        sample_user.subscription_expires_at = initial_expiry
        sample_user.subscription_type = SubscriptionType.PREMIUM
        
        sample_user.extend_subscription(30, SubscriptionType.PREMIUM)
        
        expected_expiry = initial_expiry + timedelta(days=30)
        time_diff = abs((sample_user.subscription_expires_at - expected_expiry).total_seconds())
        assert time_diff < 60  # Within 1 minute tolerance
        
        # Check domain events
        events = sample_user.get_domain_events()
        extension_events = [e for e in events if isinstance(e, SubscriptionExtended)]
        assert len(extension_events) == 1
    
    def test_extend_subscription_from_free(self, sample_user):
        """Test extending subscription from free account."""
        assert sample_user.subscription_type == SubscriptionType.FREE
        
        sample_user.extend_subscription(30, SubscriptionType.PREMIUM)
        
        assert sample_user.subscription_type == SubscriptionType.PREMIUM
        expected_expiry = datetime.utcnow() + timedelta(days=30)
        time_diff = abs((sample_user.subscription_expires_at - expected_expiry).total_seconds())
        assert time_diff < 60
    
    def test_has_active_subscription(self, sample_user):
        """Test subscription status checking."""
        # Free user has no active subscription
        assert not sample_user.has_active_subscription()
        
        # Start trial
        sample_user.start_trial(7)
        assert sample_user.has_active_subscription()
        
        # Expire the trial
        sample_user.subscription_expires_at = datetime.utcnow() - timedelta(days=1)
        assert not sample_user.has_active_subscription()
        
        # Grant premium
        sample_user.extend_subscription(30, SubscriptionType.PREMIUM)
        assert sample_user.has_active_subscription()
    
    def test_block_user(self, sample_user):
        """Test blocking user."""
        reason = "Violation of terms"
        sample_user.block(reason)
        
        assert sample_user.status == UserStatus.BLOCKED
        assert sample_user.metadata.get("block_reason") == reason
        assert sample_user.metadata.get("blocked_at") is not None
        
        # Check domain events
        events = sample_user.get_domain_events()
        block_events = [e for e in events if isinstance(e, UserBlocked)]
        assert len(block_events) == 1
    
    def test_unblock_user(self, sample_user):
        """Test unblocking user."""
        # First block the user
        sample_user.block("Test block")
        assert sample_user.status == UserStatus.BLOCKED
        
        # Then unblock
        sample_user.unblock()
        assert sample_user.status == UserStatus.ACTIVE
        assert sample_user.metadata.get("unblocked_at") is not None
    
    def test_record_purchase(self, sample_user):
        """Test recording purchase."""
        amount = 29.99
        currency = "USD"
        
        initial_spent = sample_user.total_spent
        sample_user.record_purchase(amount, currency)
        
        assert sample_user.total_spent == initial_spent + amount
        assert sample_user.metadata.get("last_purchase_amount") == amount
        assert sample_user.metadata.get("last_purchase_currency") == currency
        assert sample_user.metadata.get("last_purchase_at") is not None
    
    def test_record_activity(self, sample_user):
        """Test recording user activity."""
        initial_activity = sample_user.last_activity_at
        sample_user.record_activity()
        
        assert sample_user.last_activity_at != initial_activity
        assert sample_user.last_activity_at is not None
    
    def test_increment_referrals(self, sample_user):
        """Test incrementing referral count."""
        initial_count = sample_user.total_referrals
        sample_user.increment_referrals()
        
        assert sample_user.total_referrals == initial_count + 1
    
    def test_update_profile(self, sample_user):
        """Test updating user profile."""
        new_first_name = "Updated"
        new_username = "updated_user"
        new_language = "ru"
        
        sample_user.update_profile(
            first_name=new_first_name,
            username=new_username,
            language_code=new_language
        )
        
        assert sample_user.profile.first_name == new_first_name
        assert sample_user.profile.username == new_username
        assert sample_user.profile.language_code == new_language
    
    def test_user_equality(self, sample_user_data):
        """Test user equality comparison."""
        user1 = User.create(**sample_user_data)
        user2 = User.create(**sample_user_data)
        
        # Different instances with same ID should be equal
        user2.id = user1.id
        assert user1 == user2
        
        # Different IDs should not be equal
        user3 = User.create(telegram_id=999999, first_name="Other", last_name="User")
        assert user1 != user3
    
    def test_subscription_type_validation(self, sample_user):
        """Test subscription type validation."""
        # Valid subscription types should work
        for sub_type in SubscriptionType:
            sample_user.subscription_type = sub_type
            assert sample_user.subscription_type == sub_type
    
    def test_trial_used_tracking(self, sample_user):
        """Test trial usage tracking."""
        # Initially no trial used
        assert not sample_user.metadata.get("trial_used", False)
        
        # Start trial
        sample_user.start_trial(7)
        
        # Should mark trial as used
        assert sample_user.metadata.get("trial_used", False)
    
    def test_cannot_start_trial_twice(self, sample_user):
        """Test that trial cannot be started twice."""
        # Start first trial
        sample_user.start_trial(7)
        assert sample_user.subscription_type == SubscriptionType.TRIAL
        
        # Try to start another trial should raise error
        with pytest.raises(ValueError, match="User has already used their trial"):
            sample_user.start_trial(7)
    
    def test_cannot_start_trial_with_active_subscription(self, premium_user):
        """Test that trial cannot be started with active subscription."""
        with pytest.raises(ValueError, match="User already has an active subscription"):
            premium_user.start_trial(7)