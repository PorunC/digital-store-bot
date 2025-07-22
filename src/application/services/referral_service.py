"""Referral application service with complete functionality."""

import uuid
from typing import List, Optional

from src.domain.entities.referral import Referral, ReferralStatus, RewardType
from src.domain.entities.user import User, SubscriptionType
from src.domain.repositories.referral_repository import ReferralRepository
from src.domain.repositories.user_repository import UserRepository
from src.domain.repositories.base import UnitOfWork
from src.shared.events import event_bus


class ReferralApplicationService:
    """Referral application service handling referral-related operations."""

    def __init__(
        self,
        referral_repository: ReferralRepository,
        user_repository: UserRepository,
        unit_of_work: UnitOfWork
    ):
        self.referral_repository = referral_repository
        self.user_repository = user_repository
        self.unit_of_work = unit_of_work

    async def create_referral(
        self,
        referrer_id: str,
        referred_user_id: str,
        invite_source: Optional[str] = None
    ) -> Referral:
        """Create a new referral relationship."""
        async with self.unit_of_work:
            # Validate users exist
            referrer = await self.user_repository.get_by_id(referrer_id)
            if not referrer:
                raise ValueError(f"Referrer with ID {referrer_id} not found")

            referred_user = await self.user_repository.get_by_id(referred_user_id)
            if not referred_user:
                raise ValueError(f"Referred user with ID {referred_user_id} not found")

            # Check if user already has a referrer
            existing_referral = await self.referral_repository.find_by_referred_user(
                uuid.UUID(referred_user_id)
            )
            if existing_referral:
                raise ValueError(f"User {referred_user_id} already has a referrer")

            # Users cannot refer themselves
            if referrer_id == referred_user_id:
                raise ValueError("Users cannot refer themselves")

            # Create referral
            referral = Referral.create(
                referrer_id=uuid.UUID(referrer_id),
                referred_user_id=uuid.UUID(referred_user_id),
                invite_source=invite_source
            )

            referral = await self.referral_repository.add(referral)
            
            # Update referrer's referral count
            referrer.increment_referrals()
            await self.user_repository.update(referrer)

            await self._publish_events(referral)
            await self.unit_of_work.commit()
            return referral

    async def activate_referral(
        self,
        referred_user_id: str,
        first_level_reward_days: int = 7,
        reward_subscription_type: SubscriptionType = SubscriptionType.PREMIUM
    ) -> Optional[Referral]:
        """Activate a referral when referred user takes qualifying action."""
        async with self.unit_of_work:
            referral = await self.referral_repository.find_by_referred_user(
                uuid.UUID(referred_user_id)
            )
            
            if not referral or referral.status != ReferralStatus.PENDING:
                return None

            # Activate the referral
            referral.activate()

            # Grant first level reward to referrer
            referrer = await self.user_repository.get_by_id(str(referral.referrer_id))
            if referrer:
                referrer.extend_subscription(first_level_reward_days, reward_subscription_type)
                await self.user_repository.update(referrer)

            # Mark first level reward as granted
            referral.grant_first_level_reward()

            referral = await self.referral_repository.update(referral)
            await self._publish_events(referral)
            await self.unit_of_work.commit()
            return referral

    async def process_referral_purchase(
        self,
        referred_user_id: str,
        order_id: str,
        amount: float,
        currency: str,
        second_level_reward_days: int = 14,
        reward_subscription_type: SubscriptionType = SubscriptionType.PREMIUM
    ) -> Optional[Referral]:
        """Process referral when referred user makes first purchase."""
        async with self.unit_of_work:
            referral = await self.referral_repository.find_by_referred_user(
                uuid.UUID(referred_user_id)
            )
            
            if not referral or referral.status != ReferralStatus.ACTIVE:
                return None

            if referral.first_purchase_at is not None:
                return referral  # Already processed

            # Record the purchase
            referral.record_first_purchase(order_id, amount, currency)

            # Grant second level reward to referrer
            if not referral.second_level_reward_granted:
                referrer = await self.user_repository.get_by_id(str(referral.referrer_id))
                if referrer:
                    referrer.extend_subscription(second_level_reward_days, reward_subscription_type)
                    await self.user_repository.update(referrer)

                referral.grant_second_level_reward()

            referral = await self.referral_repository.update(referral)
            await self._publish_events(referral)
            await self.unit_of_work.commit()
            return referral

    async def get_referral_by_id(self, referral_id: str) -> Optional[Referral]:
        """Get referral by ID."""
        return await self.referral_repository.get_by_id(referral_id)

    async def get_user_referrals(self, referrer_id: str) -> List[Referral]:
        """Get all referrals for a user."""
        return await self.referral_repository.find_by_referrer(uuid.UUID(referrer_id))

    async def get_active_referrals(self, referrer_id: str) -> List[Referral]:
        """Get active referrals for a user."""
        return await self.referral_repository.find_active_referrals(uuid.UUID(referrer_id))

    async def get_user_referrer(self, user_id: str) -> Optional[Referral]:
        """Get the referral record for a user (who referred them)."""
        return await self.referral_repository.find_by_referred_user(uuid.UUID(user_id))

    async def get_referral_chain(self, user_id: str, max_depth: int = 5) -> List[User]:
        """Get the referral chain for a user."""
        chain = []
        current_user_id = user_id
        
        for _ in range(max_depth):
            referral = await self.referral_repository.find_by_referred_user(
                uuid.UUID(current_user_id)
            )
            
            if not referral:
                break
                
            referrer = await self.user_repository.get_by_id(str(referral.referrer_id))
            if not referrer:
                break
                
            chain.append(referrer)
            current_user_id = str(referrer.id)
        
        return chain

    async def process_pending_rewards(
        self,
        reward_type: RewardType,
        reward_days: int = 7,
        batch_size: int = 100
    ) -> List[Referral]:
        """Process pending rewards for referrals."""
        pending_referrals = await self.referral_repository.find_pending_rewards(reward_type)
        processed_referrals = []
        
        for referral in pending_referrals[:batch_size]:
            try:
                async with self.unit_of_work:
                    referrer = await self.user_repository.get_by_id(str(referral.referrer_id))
                    if not referrer:
                        continue

                    # Grant reward
                    referrer.extend_subscription(reward_days)
                    await self.user_repository.update(referrer)

                    # Mark reward as granted
                    if reward_type == RewardType.FIRST_LEVEL:
                        referral.grant_first_level_reward()
                    else:
                        referral.grant_second_level_reward()

                    referral = await self.referral_repository.update(referral)
                    await self._publish_events(referral)
                    await self.unit_of_work.commit()
                    
                    processed_referrals.append(referral)
                    
            except Exception as e:
                # Log error but continue processing
                print(f"Error processing reward for referral {referral.id}: {e}")
        
        return processed_referrals

    async def deactivate_referral(
        self,
        referral_id: str,
        reason: Optional[str] = None
    ) -> Referral:
        """Deactivate a referral."""
        async with self.unit_of_work:
            referral = await self.referral_repository.get_by_id(referral_id)
            if not referral:
                raise ValueError(f"Referral with ID {referral_id} not found")

            referral.deactivate(reason)

            referral = await self.referral_repository.update(referral)
            await self._publish_events(referral)
            await self.unit_of_work.commit()
            return referral

    async def get_referral_statistics(self, referrer_id: str) -> dict:
        """Get referral statistics for a user."""
        return await self.referral_repository.get_referral_stats(uuid.UUID(referrer_id))

    async def get_top_referrers(self, limit: int = 10) -> List[dict]:
        """Get top referrers by number of active referrals."""
        # This would require a more complex query, implementing a basic version
        all_referrals = await self.referral_repository.get_all()
        
        referrer_stats = {}
        for referral in all_referrals:
            referrer_id = str(referral.referrer_id)
            if referrer_id not in referrer_stats:
                referrer_stats[referrer_id] = {
                    "referrer_id": referrer_id,
                    "total_referrals": 0,
                    "active_referrals": 0,
                    "converted_referrals": 0
                }
            
            referrer_stats[referrer_id]["total_referrals"] += 1
            
            if referral.status == ReferralStatus.ACTIVE:
                referrer_stats[referrer_id]["active_referrals"] += 1
                
            if referral.first_purchase_at:
                referrer_stats[referrer_id]["converted_referrals"] += 1

        # Sort by active referrals and return top N
        top_referrers = sorted(
            referrer_stats.values(),
            key=lambda x: x["active_referrals"],
            reverse=True
        )[:limit]

        # Enrich with user information
        enriched_referrers = []
        for stats in top_referrers:
            user = await self.user_repository.get_by_id(stats["referrer_id"])
            if user:
                stats["user_info"] = {
                    "telegram_id": user.telegram_id,
                    "first_name": user.profile.first_name,
                    "username": user.profile.username
                }
                enriched_referrers.append(stats)

        return enriched_referrers

    async def validate_referral_eligibility(
        self,
        referrer_id: str,
        referred_user_id: str
    ) -> dict:
        """Validate if a referral is eligible."""
        errors = []
        
        # Check if users exist
        referrer = await self.user_repository.get_by_id(referrer_id)
        if not referrer:
            errors.append("Referrer not found")
            
        referred_user = await self.user_repository.get_by_id(referred_user_id)
        if not referred_user:
            errors.append("Referred user not found")
            
        # Check self-referral
        if referrer_id == referred_user_id:
            errors.append("Users cannot refer themselves")
            
        # Check existing referral
        if referred_user:
            existing_referral = await self.referral_repository.find_by_referred_user(
                uuid.UUID(referred_user_id)
            )
            if existing_referral:
                errors.append("User already has a referrer")
        
        return {
            "eligible": len(errors) == 0,
            "errors": errors
        }

    async def _publish_events(self, referral: Referral) -> None:
        """Publish domain events."""
        events = referral.get_domain_events()
        for event in events:
            await event_bus.publish(event)
        referral.clear_domain_events()