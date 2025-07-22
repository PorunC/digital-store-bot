"""SQLAlchemy User repository implementation."""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.user import User, UserStatus, SubscriptionType
from src.domain.repositories.user_repository import UserRepository
from src.domain.value_objects.user_profile import UserProfile
from ..models.user import UserModel


class SqlAlchemyUserRepository(UserRepository):
    """SQLAlchemy implementation of User repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, entity_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            user_uuid = uuid.UUID(entity_id)
        except ValueError:
            return None

        stmt = select(UserModel).where(UserModel.id == user_uuid)
        result = await self.session.execute(stmt)
        user_model = result.scalar_one_or_none()
        
        if user_model:
            return self._model_to_entity(user_model)
        return None

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        stmt = select(UserModel).where(UserModel.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        user_model = result.scalar_one_or_none()
        
        if user_model:
            return self._model_to_entity(user_model)
        return None

    async def get_all(self) -> List[User]:
        """Get all users."""
        stmt = select(UserModel).order_by(UserModel.created_at.desc())
        result = await self.session.execute(stmt)
        user_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in user_models]

    async def add(self, entity: User) -> User:
        """Add a new user."""
        user_model = self._entity_to_model(entity)
        self.session.add(user_model)
        await self.session.flush()
        await self.session.refresh(user_model)
        
        return self._model_to_entity(user_model)

    async def update(self, entity: User) -> User:
        """Update an existing user."""
        stmt = select(UserModel).where(UserModel.id == entity.id)
        result = await self.session.execute(stmt)
        user_model = result.scalar_one_or_none()
        
        if not user_model:
            raise ValueError(f"User with ID {entity.id} not found")

        # Update fields
        user_model.telegram_id = entity.telegram_id
        user_model.first_name = entity.profile.first_name
        user_model.username = entity.profile.username
        user_model.language_code = entity.language_code
        user_model.status = entity.status.value
        user_model.is_trial_used = entity.is_trial_used
        user_model.trial_expires_at = entity.trial_expires_at
        user_model.trial_type = entity.trial_type.value if entity.trial_type else None
        user_model.subscription_expires_at = entity.subscription_expires_at
        user_model.subscription_type = entity.subscription_type.value if entity.subscription_type else None
        user_model.total_subscription_days = entity.total_subscription_days
        user_model.referrer_id = entity.referrer_id
        user_model.invite_source = entity.invite_source
        user_model.total_referrals = entity.total_referrals
        user_model.total_orders = entity.total_orders
        user_model.total_spent_amount = entity.total_spent_amount
        user_model.total_spent_currency = entity.total_spent_currency
        user_model.last_active_at = entity.last_active_at
        user_model.version = entity.version
        user_model.updated_at = datetime.utcnow()

        await self.session.flush()
        return self._model_to_entity(user_model)

    async def delete(self, entity_id: str) -> bool:
        """Delete a user by ID."""
        try:
            user_uuid = uuid.UUID(entity_id)
        except ValueError:
            return False

        stmt = select(UserModel).where(UserModel.id == user_uuid)
        result = await self.session.execute(stmt)
        user_model = result.scalar_one_or_none()
        
        if user_model:
            await self.session.delete(user_model)
            return True
        return False

    async def exists(self, entity_id: str) -> bool:
        """Check if user exists."""
        try:
            user_uuid = uuid.UUID(entity_id)
        except ValueError:
            return False

        stmt = select(UserModel.id).where(UserModel.id == user_uuid)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def find_by_referrer_id(self, referrer_id: str) -> List[User]:
        """Find users referred by a specific user."""
        stmt = select(UserModel).where(UserModel.referrer_id == referrer_id)
        result = await self.session.execute(stmt)
        user_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in user_models]

    async def find_by_status(self, status: str) -> List[User]:
        """Find users by status."""
        stmt = select(UserModel).where(UserModel.status == status)
        result = await self.session.execute(stmt)
        user_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in user_models]

    async def find_premium_users(self) -> List[User]:
        """Find users with active premium subscriptions."""
        now = datetime.utcnow()
        stmt = select(UserModel).where(
            or_(
                UserModel.trial_expires_at > now,
                UserModel.subscription_expires_at > now
            )
        )
        result = await self.session.execute(stmt)
        user_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in user_models]

    async def find_expiring_users(self, days: int) -> List[User]:
        """Find users whose premium expires within specified days."""
        from datetime import timedelta
        
        now = datetime.utcnow()
        future_date = now + timedelta(days=days)
        
        stmt = select(UserModel).where(
            or_(
                UserModel.trial_expires_at.between(now, future_date),
                UserModel.subscription_expires_at.between(now, future_date)
            )
        )
        result = await self.session.execute(stmt)
        user_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in user_models]

    async def get_user_statistics(self) -> dict:
        """Get user statistics."""
        # Total users
        total_users_stmt = select(func.count(UserModel.id))
        total_users_result = await self.session.execute(total_users_stmt)
        total_users = total_users_result.scalar()

        # Active users
        active_users_stmt = select(func.count(UserModel.id)).where(
            UserModel.status == UserStatus.ACTIVE.value
        )
        active_users_result = await self.session.execute(active_users_stmt)
        active_users = active_users_result.scalar()

        # Premium users
        now = datetime.utcnow()
        premium_users_stmt = select(func.count(UserModel.id)).where(
            or_(
                UserModel.trial_expires_at > now,
                UserModel.subscription_expires_at > now
            )
        )
        premium_users_result = await self.session.execute(premium_users_stmt)
        premium_users = premium_users_result.scalar()

        # Trial users
        trial_users_stmt = select(func.count(UserModel.id)).where(
            UserModel.is_trial_used == True
        )
        trial_users_result = await self.session.execute(trial_users_stmt)
        trial_users = trial_users_result.scalar()

        return {
            "total_users": total_users,
            "active_users": active_users,
            "premium_users": premium_users,
            "trial_users": trial_users,
            "blocked_users": total_users - active_users,
        }

    def _model_to_entity(self, model: UserModel) -> User:
        """Convert UserModel to User entity."""
        profile = UserProfile(
            first_name=model.first_name,
            username=model.username
        )

        user = User(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
            telegram_id=model.telegram_id,
            profile=profile,
            language_code=model.language_code,
            status=UserStatus(model.status),
            is_trial_used=model.is_trial_used,
            trial_expires_at=model.trial_expires_at,
            trial_type=SubscriptionType(model.trial_type) if model.trial_type else None,
            subscription_expires_at=model.subscription_expires_at,
            subscription_type=SubscriptionType(model.subscription_type) if model.subscription_type else None,
            total_subscription_days=model.total_subscription_days,
            referrer_id=model.referrer_id,
            invite_source=model.invite_source,
            total_referrals=model.total_referrals,
            total_orders=model.total_orders,
            total_spent_amount=model.total_spent_amount,
            total_spent_currency=model.total_spent_currency,
            last_active_at=model.last_active_at,
        )

        # Clear domain events as they come from persistence
        user.clear_domain_events()
        return user

    def _entity_to_model(self, entity: User) -> UserModel:
        """Convert User entity to UserModel."""
        return UserModel(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            version=entity.version,
            telegram_id=entity.telegram_id,
            first_name=entity.profile.first_name,
            username=entity.profile.username,
            language_code=entity.language_code,
            status=entity.status.value,
            is_trial_used=entity.is_trial_used,
            trial_expires_at=entity.trial_expires_at,
            trial_type=entity.trial_type.value if entity.trial_type else None,
            subscription_expires_at=entity.subscription_expires_at,
            subscription_type=entity.subscription_type.value if entity.subscription_type else None,
            total_subscription_days=entity.total_subscription_days,
            referrer_id=entity.referrer_id,
            invite_source=entity.invite_source,
            total_referrals=entity.total_referrals,
            total_orders=entity.total_orders,
            total_spent_amount=entity.total_spent_amount,
            total_spent_currency=entity.total_spent_currency,
            last_active_at=entity.last_active_at,
        )