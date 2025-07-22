"""Example test to verify the testing framework works."""

import pytest
from src.domain.value_objects.money import Money
from src.domain.value_objects.user_profile import UserProfile


class TestMoney:
    """Test Money value object."""

    def test_create_money(self):
        """Test creating money object."""
        money = Money.from_float(10.50, "USD")
        assert money.amount == 10.50
        assert money.currency == "USD"

    def test_add_money(self):
        """Test adding money objects."""
        money1 = Money.from_float(10.00, "USD")
        money2 = Money.from_float(5.50, "USD")
        result = money1 + money2
        assert result.amount == 15.50
        assert result.currency == "USD"

    def test_cannot_add_different_currencies(self):
        """Test that different currencies cannot be added."""
        money1 = Money.from_float(10.00, "USD")
        money2 = Money.from_float(5.50, "EUR")
        with pytest.raises(ValueError):
            money1 + money2


class TestUserProfile:
    """Test UserProfile value object."""

    def test_create_user_profile(self):
        """Test creating user profile."""
        profile = UserProfile(first_name="John", username="john_doe")
        assert profile.first_name == "John"
        assert profile.username == "john_doe"
        assert profile.display_name == "John (@john_doe)"

    def test_user_profile_without_username(self):
        """Test user profile without username."""
        profile = UserProfile(first_name="Jane")
        assert profile.first_name == "Jane"
        assert profile.username is None
        assert profile.display_name == "Jane"

    def test_invalid_first_name(self):
        """Test invalid first name."""
        with pytest.raises(ValueError):
            UserProfile(first_name="")

    def test_invalid_username(self):
        """Test invalid username."""
        with pytest.raises(ValueError):
            UserProfile(first_name="John", username="invalid-username!")