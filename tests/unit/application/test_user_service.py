"""Unit tests for UserApplicationService."""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timedelta

from src.application.services.user_service import UserApplicationService
from src.domain.entities.user import User, SubscriptionType
from src.domain.repositories.user_repository import UserRepository
from src.domain.repositories.base import UnitOfWork


class TestUserApplicationService:
    """Test UserApplicationService."""
    
    @pytest.fixture
    def mock_user_repository(self):
        """Mock user repository."""
        return AsyncMock(spec=UserRepository)
    
    @pytest.fixture
    def mock_unit_of_work(self):
        """Mock unit of work."""
        uow = AsyncMock(spec=UnitOfWork)
        uow.__aenter__ = AsyncMock(return_value=uow)
        uow.__aexit__ = AsyncMock(return_value=None)
        return uow
    
    @pytest.fixture
    def user_service(self, mock_user_repository, mock_unit_of_work):
        """Create user service with mocked dependencies."""
        return UserApplicationService(
            user_repository=mock_user_repository,
            unit_of_work=mock_unit_of_work
        )
    
    @pytest.mark.asyncio
    async def test_register_new_user(
        self, 
        user_service, 
        mock_user_repository, 
        mock_unit_of_work,
        sample_user_data
    ):
        """Test registering a new user."""
        # Setup mocks
        mock_user_repository.get_by_telegram_id.return_value = None
        mock_user_repository.add.return_value = Mock(spec=User)
        
        # Call service
        result = await user_service.register_user(
            telegram_id=sample_user_data["telegram_id"],
            first_name=sample_user_data["first_name"],
            username=sample_user_data["username"],
            language_code=sample_user_data["language_code"]
        )
        
        # Verify calls
        mock_user_repository.get_by_telegram_id.assert_called_once_with(
            sample_user_data["telegram_id"]
        )
        mock_user_repository.add.assert_called_once()
        mock_unit_of_work.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_existing_user(
        self,
        user_service,
        mock_user_repository,
        mock_unit_of_work,
        sample_user,
        sample_user_data
    ):
        """Test registering an existing user updates profile."""
        # Setup mocks
        mock_user_repository.get_by_telegram_id.return_value = sample_user
        mock_user_repository.update.return_value = sample_user
        
        # Call service
        result = await user_service.register_user(
            telegram_id=sample_user_data["telegram_id"],
            first_name="Updated Name",
            username=sample_user_data["username"],
            language_code=sample_user_data["language_code"]
        )
        
        # Verify calls
        mock_user_repository.get_by_telegram_id.assert_called_once()
        mock_user_repository.update.assert_called_once()
        mock_unit_of_work.commit.assert_called_once()
        
        # Verify user was updated (would need to check the actual user object)
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_start_trial(
        self,
        user_service,
        mock_user_repository,
        mock_unit_of_work,
        sample_user
    ):
        """Test starting trial for user."""
        # Setup mocks
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.update.return_value = sample_user
        
        # Call service
        result = await user_service.start_trial(
            user_id=str(sample_user.id),
            trial_period_days=7
        )
        
        # Verify calls
        mock_user_repository.get_by_id.assert_called_once_with(str(sample_user.id))
        mock_user_repository.update.assert_called_once()
        mock_unit_of_work.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_trial_user_not_found(
        self,
        user_service,
        mock_user_repository,
        mock_unit_of_work
    ):
        """Test starting trial for non-existent user."""
        # Setup mocks
        mock_user_repository.get_by_id.return_value = None
        
        # Call service and expect error
        with pytest.raises(ValueError, match="User with ID .* not found"):
            await user_service.start_trial(
                user_id="nonexistent-id",
                trial_period_days=7
            )
        
        # Verify no update was attempted
        mock_user_repository.update.assert_not_called()
        mock_unit_of_work.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_extend_subscription(
        self,
        user_service,
        mock_user_repository,
        mock_unit_of_work,
        sample_user
    ):
        """Test extending user subscription."""
        # Setup mocks
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.update.return_value = sample_user
        
        # Call service
        result = await user_service.extend_subscription(
            user_id=str(sample_user.id),
            days=30,
            subscription_type=SubscriptionType.PREMIUM
        )
        
        # Verify calls
        mock_user_repository.get_by_id.assert_called_once()
        mock_user_repository.update.assert_called_once()
        mock_unit_of_work.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_block_user(
        self,
        user_service,
        mock_user_repository,
        mock_unit_of_work,
        sample_user
    ):
        """Test blocking a user."""
        # Setup mocks
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.update.return_value = sample_user
        
        reason = "Violation of terms"
        
        # Call service
        result = await user_service.block_user(
            user_id=str(sample_user.id),
            reason=reason
        )
        
        # Verify calls
        mock_user_repository.get_by_id.assert_called_once()
        mock_user_repository.update.assert_called_once()
        mock_unit_of_work.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_unblock_user(
        self,
        user_service,
        mock_user_repository,
        mock_unit_of_work,
        sample_user
    ):
        """Test unblocking a user."""
        # Setup mocks
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.update.return_value = sample_user
        
        # Call service
        result = await user_service.unblock_user(str(sample_user.id))
        
        # Verify calls
        mock_user_repository.get_by_id.assert_called_once()
        mock_user_repository.update.assert_called_once()
        mock_unit_of_work.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_by_telegram_id(
        self,
        user_service,
        mock_user_repository,
        sample_user
    ):
        """Test getting user by Telegram ID."""
        # Setup mocks
        mock_user_repository.get_by_telegram_id.return_value = sample_user
        
        # Call service
        result = await user_service.get_user_by_telegram_id(123456789)
        
        # Verify calls
        mock_user_repository.get_by_telegram_id.assert_called_once_with(123456789)
        assert result == sample_user
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(
        self,
        user_service,
        mock_user_repository,
        sample_user
    ):
        """Test getting user by ID."""
        # Setup mocks
        mock_user_repository.get_by_id.return_value = sample_user
        
        # Call service
        result = await user_service.get_user_by_id(str(sample_user.id))
        
        # Verify calls
        mock_user_repository.get_by_id.assert_called_once_with(str(sample_user.id))
        assert result == sample_user
    
    @pytest.mark.asyncio
    async def test_record_user_purchase(
        self,
        user_service,
        mock_user_repository,
        mock_unit_of_work,
        sample_user
    ):
        """Test recording user purchase."""
        # Setup mocks
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.update.return_value = sample_user
        
        # Call service
        result = await user_service.record_user_purchase(
            user_id=str(sample_user.id),
            amount=29.99,
            currency="USD"
        )
        
        # Verify calls
        mock_user_repository.get_by_id.assert_called_once()
        mock_user_repository.update.assert_called_once()
        mock_unit_of_work.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_increment_user_referrals(
        self,
        user_service,
        mock_user_repository,
        mock_unit_of_work,
        sample_user
    ):
        """Test incrementing user referrals."""
        # Setup mocks
        mock_user_repository.get_by_id.return_value = sample_user
        mock_user_repository.update.return_value = sample_user
        
        # Call service
        result = await user_service.increment_user_referrals(str(sample_user.id))
        
        # Verify calls
        mock_user_repository.get_by_id.assert_called_once()
        mock_user_repository.update.assert_called_once()
        mock_unit_of_work.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_find_premium_users(
        self,
        user_service,
        mock_user_repository
    ):
        """Test finding premium users."""
        # Setup mocks
        premium_users = [Mock(spec=User), Mock(spec=User)]
        mock_user_repository.find_premium_users.return_value = premium_users
        
        # Call service
        result = await user_service.find_premium_users()
        
        # Verify calls
        mock_user_repository.find_premium_users.assert_called_once()
        assert result == premium_users
    
    @pytest.mark.asyncio
    async def test_get_user_statistics(
        self,
        user_service,
        mock_user_repository
    ):
        """Test getting user statistics."""
        # Setup mocks
        stats = {"total_users": 100, "premium_users": 20}
        mock_user_repository.get_user_statistics.return_value = stats
        
        # Call service
        result = await user_service.get_user_statistics()
        
        # Verify calls
        mock_user_repository.get_user_statistics.assert_called_once()
        assert result == stats