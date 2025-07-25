"""User application service with complete functionality."""

from typing import List, Optional

from src.domain.entities.user import User, SubscriptionType
from src.domain.repositories.user_repository import UserRepository
from src.domain.repositories.base import UnitOfWork
from src.shared.events import event_bus


class UserApplicationService:
    """User application service handling user-related operations."""

    def __init__(
        self,
        unit_of_work: UnitOfWork,
        user_repository_factory = None
    ):
        self.unit_of_work = unit_of_work
        self._user_repository_factory = user_repository_factory
        
    def _get_user_repository(self) -> UserRepository:
        """Get user repository using factory or fallback to direct creation."""
        if self._user_repository_factory and hasattr(self.unit_of_work, 'session') and self.unit_of_work.session:
            return self._user_repository_factory(self.unit_of_work.session)
            
        # Fallback to anti-pattern during transition period
        from src.infrastructure.database.repositories.user_repository import SqlAlchemyUserRepository
        if hasattr(self.unit_of_work, 'session') and self.unit_of_work.session:
            return SqlAlchemyUserRepository(self.unit_of_work.session)
        else:
            raise RuntimeError("Unit of work session not available")

    async def register_user(
        self,
        telegram_id: int,
        first_name: str,
        username: Optional[str] = None,
        language_code: str = "en",
        referrer_id: Optional[str] = None,
        invite_source: Optional[str] = None,
    ) -> User:
        """Register a new user."""
        # Sanitize input data to prevent validation errors
        first_name = self._sanitize_name(first_name)
        username = self._sanitize_username(username)
        language_code = self._sanitize_language_code(language_code)
        
        async with self.unit_of_work:
            # Check if user already exists
            existing_user = await self._get_user_repository().get_by_telegram_id(telegram_id)
            if existing_user:
                # Update profile if needed
                existing_user.update_profile(
                    first_name=first_name,
                    username=username,
                    language_code=language_code
                )
                existing_user.record_activity()
                
                user = await self._get_user_repository().update(existing_user)
                await self._publish_events(user)
                await self.unit_of_work.commit()
                return user

            # Create new user
            user = User.create(
                telegram_id=telegram_id,
                first_name=first_name,
                username=username,
                language_code=language_code,
                referrer_id=referrer_id,
                invite_source=invite_source,
            )

            user = await self._get_user_repository().add(user)
            await self._publish_events(user)
            await self.unit_of_work.commit()
            return user

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        async with self.unit_of_work:
            return await self._get_user_repository().get_by_telegram_id(telegram_id)

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        async with self.unit_of_work:
            return await self._get_user_repository().get_by_id(user_id)

    async def start_trial(
        self,
        user_id: str,
        trial_period_days: int,
        trial_type: SubscriptionType = SubscriptionType.TRIAL
    ) -> User:
        """Start trial for a user."""
        async with self.unit_of_work:
            user = await self._get_user_repository().get_by_id(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")

            user.start_trial(trial_period_days, trial_type)
            user.record_activity()

            user = await self._get_user_repository().update(user)
            await self._publish_events(user)
            await self.unit_of_work.commit()
            return user

    async def extend_subscription(
        self,
        user_id: str,
        days: int,
        subscription_type: SubscriptionType = SubscriptionType.PREMIUM
    ) -> User:
        """Extend user subscription."""
        async with self.unit_of_work:
            user = await self._get_user_repository().get_by_id(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")

            user.extend_subscription(days, subscription_type)
            user.record_activity()

            user = await self._get_user_repository().update(user)
            await self._publish_events(user)
            await self.unit_of_work.commit()
            return user

    async def block_user(self, user_id: str, reason: Optional[str] = None) -> User:
        """Block a user."""
        async with self.unit_of_work:
            user = await self._get_user_repository().get_by_id(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")

            user.block(reason)

            user = await self._get_user_repository().update(user)
            await self._publish_events(user)
            await self.unit_of_work.commit()
            return user

    async def unblock_user(self, user_id: str) -> User:
        """Unblock a user."""
        async with self.unit_of_work:
            user = await self._get_user_repository().get_by_id(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")

            user.unblock()

            user = await self._get_user_repository().update(user)
            await self._publish_events(user)
            await self.unit_of_work.commit()
            return user

    async def update_user_profile(
        self,
        user_id: str,
        first_name: Optional[str] = None,
        username: Optional[str] = None,
        language_code: Optional[str] = None
    ) -> User:
        """Update user profile."""
        # Sanitize input data to prevent validation errors
        if first_name is not None:
            first_name = self._sanitize_name(first_name)
        if username is not None:
            username = self._sanitize_username(username)
        if language_code is not None:
            language_code = self._sanitize_language_code(language_code)
            
        async with self.unit_of_work:
            user = await self._get_user_repository().get_by_id(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")

            user.update_profile(first_name, username, language_code)
            user.record_activity()

            user = await self._get_user_repository().update(user)
            await self._publish_events(user)
            await self.unit_of_work.commit()
            return user

    async def record_user_activity(self, user_id: str) -> User:
        """Record user activity."""
        async with self.unit_of_work:
            user = await self._get_user_repository().get_by_id(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")

            user.record_activity()

            user = await self._get_user_repository().update(user)
            await self.unit_of_work.commit()
            return user

    async def record_user_purchase(
        self,
        user_id: str,
        amount: float,
        currency: str
    ) -> User:
        """Record a user purchase."""
        async with self.unit_of_work:
            user = await self._get_user_repository().get_by_id(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")

            user.record_purchase(amount, currency)

            user = await self._get_user_repository().update(user)
            await self._publish_events(user)
            await self.unit_of_work.commit()
            return user

    async def increment_user_referrals(self, user_id: str) -> User:
        """Increment user referrals count."""
        async with self.unit_of_work:
            user = await self._get_user_repository().get_by_id(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")

            user.increment_referrals()

            user = await self._get_user_repository().update(user)
            await self.unit_of_work.commit()
            return user

    async def find_users_by_referrer(self, referrer_id: str) -> List[User]:
        """Find users referred by a specific user."""
        async with self.unit_of_work:
            return await self._get_user_repository().find_by_referrer_id(referrer_id)

    async def find_premium_users(self) -> List[User]:
        """Find users with active premium subscriptions."""
        async with self.unit_of_work:
            return await self._get_user_repository().find_premium_users()

    async def find_expiring_users(self, days: int) -> List[User]:
        """Find users whose premium expires within specified days."""
        async with self.unit_of_work:
            return await self._get_user_repository().find_expiring_users(days)

    async def get_user_statistics(self) -> dict:
        """Get user statistics."""
        async with self.unit_of_work:
            return await self._get_user_repository().get_user_statistics()

    async def _publish_events(self, user: User) -> None:
        """Publish domain events."""
        events = user.get_domain_events()
        for event in events:
            await event_bus.publish(event)
        user.clear_domain_events()

    def _sanitize_name(self, name: str) -> str:
        """Sanitize name input to prevent validation errors."""
        if not name:
            return "User"
        name = name.strip()
        if len(name) > 64:
            name = name[:61] + "..."
        return name

    def _sanitize_username(self, username: Optional[str]) -> Optional[str]:
        """Sanitize username input to prevent validation errors."""
        if not username:
            return None
        username = username.strip()
        if not username:
            return None
        if len(username) > 32:
            username = username[:29] + "..."
        return username

    def _sanitize_language_code(self, language_code: str) -> str:
        """Sanitize language code input."""
        if not language_code or len(language_code) < 2:
            return "en"
        return language_code[:5].lower()