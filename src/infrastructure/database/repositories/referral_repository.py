"""SQLAlchemy Referral repository implementation."""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.referral import Referral, ReferralStatus, RewardType
from src.domain.repositories.referral_repository import ReferralRepository
from ..models.referral import ReferralModel


class SqlAlchemyReferralRepository(ReferralRepository):
    """SQLAlchemy implementation of Referral repository."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, entity_id: str) -> Optional[Referral]:
        """Get referral by ID."""
        try:
            referral_uuid = uuid.UUID(entity_id)
        except ValueError:
            return None

        stmt = select(ReferralModel).where(ReferralModel.id == referral_uuid)
        result = await self.session.execute(stmt)
        referral_model = result.scalar_one_or_none()
        
        if referral_model:
            return self._model_to_entity(referral_model)
        return None

    async def get_all(self) -> List[Referral]:
        """Get all referrals."""
        stmt = select(ReferralModel).order_by(ReferralModel.created_at.desc())
        result = await self.session.execute(stmt)
        referral_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in referral_models]

    async def add(self, entity: Referral) -> Referral:
        """Add a new referral."""
        referral_model = self._entity_to_model(entity)
        self.session.add(referral_model)
        await self.session.flush()
        await self.session.refresh(referral_model)
        
        return self._model_to_entity(referral_model)

    async def update(self, entity: Referral) -> Referral:
        """Update an existing referral."""
        stmt = select(ReferralModel).where(ReferralModel.id == entity.id)
        result = await self.session.execute(stmt)
        referral_model = result.scalar_one_or_none()
        
        if not referral_model:
            raise ValueError(f"Referral with ID {entity.id} not found")

        # Update fields with safe enum handling
        referral_model.referrer_id = entity.referrer_id
        referral_model.referred_user_id = entity.referred_user_id
        referral_model.status = entity.status.value if hasattr(entity.status, 'value') else str(entity.status)
        referral_model.first_level_reward_granted = entity.first_level_reward_granted
        referral_model.second_level_reward_granted = entity.second_level_reward_granted
        referral_model.activated_at = entity.activated_at
        referral_model.first_purchase_at = entity.first_purchase_at
        referral_model.invite_source = entity.invite_source
        referral_model.tracking_data = entity.metadata
        referral_model.version = entity.version

        await self.session.flush()
        return self._model_to_entity(referral_model)

    async def delete(self, entity_id: str) -> bool:
        """Delete a referral by ID."""
        try:
            referral_uuid = uuid.UUID(entity_id)
        except ValueError:
            return False

        stmt = select(ReferralModel).where(ReferralModel.id == referral_uuid)
        result = await self.session.execute(stmt)
        referral_model = result.scalar_one_or_none()
        
        if referral_model:
            await self.session.delete(referral_model)
            return True
        return False

    async def exists(self, entity_id: str) -> bool:
        """Check if referral exists."""
        try:
            referral_uuid = uuid.UUID(entity_id)
        except ValueError:
            return False

        stmt = select(ReferralModel.id).where(ReferralModel.id == referral_uuid)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def find_by_referrer(self, referrer_id: uuid.UUID) -> List[Referral]:
        """Find referrals by referrer ID."""
        stmt = select(ReferralModel).where(
            ReferralModel.referrer_id == referrer_id
        ).order_by(ReferralModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        referral_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in referral_models]

    async def find_by_referred_user(self, referred_user_id: uuid.UUID) -> Optional[Referral]:
        """Find referral by referred user ID."""
        stmt = select(ReferralModel).where(
            ReferralModel.referred_user_id == referred_user_id
        )
        result = await self.session.execute(stmt)
        referral_model = result.scalar_one_or_none()
        
        if referral_model:
            return self._model_to_entity(referral_model)
        return None

    async def find_active_referrals(self, referrer_id: uuid.UUID) -> List[Referral]:
        """Find active referrals for a referrer."""
        stmt = select(ReferralModel).where(
            and_(
                ReferralModel.referrer_id == referrer_id,
                ReferralModel.status == ReferralStatus.ACTIVE.value
            )
        ).order_by(ReferralModel.created_at.desc())
        
        result = await self.session.execute(stmt)
        referral_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in referral_models]

    async def find_pending_rewards(self, reward_type: RewardType) -> List[Referral]:
        """Find referrals with pending rewards."""
        if reward_type == RewardType.FIRST_LEVEL:
            filter_condition = and_(
                ReferralModel.status == ReferralStatus.ACTIVE.value,
                ReferralModel.first_level_reward_granted == False,
                ReferralModel.activated_at.is_not(None)
            )
        else:  # SECOND_LEVEL
            filter_condition = and_(
                ReferralModel.status == ReferralStatus.ACTIVE.value,
                ReferralModel.second_level_reward_granted == False,
                ReferralModel.first_purchase_at.is_not(None)
            )

        stmt = select(ReferralModel).where(filter_condition).order_by(ReferralModel.created_at)
        
        result = await self.session.execute(stmt)
        referral_models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in referral_models]

    async def get_referral_stats(self, referrer_id: uuid.UUID) -> dict:
        """Get referral statistics for a user."""
        # Total referrals count
        total_stmt = select(func.count(ReferralModel.id)).where(
            ReferralModel.referrer_id == referrer_id
        )
        total_result = await self.session.execute(total_stmt)
        total_referrals = total_result.scalar() or 0

        # Active referrals count
        active_stmt = select(func.count(ReferralModel.id)).where(
            and_(
                ReferralModel.referrer_id == referrer_id,
                ReferralModel.status == ReferralStatus.ACTIVE.value
            )
        )
        active_result = await self.session.execute(active_stmt)
        active_referrals = active_result.scalar() or 0

        # Converted referrals (made first purchase)
        converted_stmt = select(func.count(ReferralModel.id)).where(
            and_(
                ReferralModel.referrer_id == referrer_id,
                ReferralModel.first_purchase_at.is_not(None)
            )
        )
        converted_result = await self.session.execute(converted_stmt)
        converted_referrals = converted_result.scalar() or 0

        # Rewards granted counts
        first_level_rewards_stmt = select(func.count(ReferralModel.id)).where(
            and_(
                ReferralModel.referrer_id == referrer_id,
                ReferralModel.first_level_reward_granted == True
            )
        )
        first_level_result = await self.session.execute(first_level_rewards_stmt)
        first_level_rewards = first_level_result.scalar() or 0

        second_level_rewards_stmt = select(func.count(ReferralModel.id)).where(
            and_(
                ReferralModel.referrer_id == referrer_id,
                ReferralModel.second_level_reward_granted == True
            )
        )
        second_level_result = await self.session.execute(second_level_rewards_stmt)
        second_level_rewards = second_level_result.scalar() or 0

        return {
            "total_referrals": total_referrals,
            "active_referrals": active_referrals,
            "converted_referrals": converted_referrals,
            "first_level_rewards_granted": first_level_rewards,
            "second_level_rewards_granted": second_level_rewards,
            "conversion_rate": (converted_referrals / total_referrals * 100) if total_referrals > 0 else 0
        }

    def _model_to_entity(self, model: ReferralModel) -> Referral:
        """Convert ReferralModel to Referral entity."""
        referral = Referral(
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
            referrer_id=model.referrer_id,
            referred_user_id=model.referred_user_id,
            status=ReferralStatus(model.status),
            first_level_reward_granted=model.first_level_reward_granted,
            second_level_reward_granted=model.second_level_reward_granted,
            activated_at=model.activated_at,
            first_purchase_at=model.first_purchase_at,
            invite_source=model.invite_source,
            metadata=model.tracking_data or {}
        )

        # Clear domain events as they come from persistence
        referral.clear_domain_events()
        return referral

    def _entity_to_model(self, entity: Referral) -> ReferralModel:
        """Convert Referral entity to ReferralModel."""
        return ReferralModel(
            id=entity.id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            version=entity.version,
            referrer_id=entity.referrer_id,
            referred_user_id=entity.referred_user_id,
            status=entity.status.value if hasattr(entity.status, 'value') else str(entity.status),
            first_level_reward_granted=entity.first_level_reward_granted,
            second_level_reward_granted=entity.second_level_reward_granted,
            activated_at=entity.activated_at,
            first_purchase_at=entity.first_purchase_at,
            invite_source=entity.invite_source,
            tracking_data=entity.metadata
        )