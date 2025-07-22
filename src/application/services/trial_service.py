"""Trial application service with complete functionality."""

from datetime import datetime, timedelta
from typing import List, Optional

from src.domain.entities.user import User, SubscriptionType, UserStatus
from src.domain.repositories.user_repository import UserRepository
from src.domain.repositories.base import UnitOfWork
from src.shared.events import event_bus


class TrialApplicationService:
    """Trial application service handling trial-related operations."""

    def __init__(
        self,
        user_repository: UserRepository,
        unit_of_work: UnitOfWork
    ):
        self.user_repository = user_repository
        self.unit_of_work = unit_of_work

    async def start_trial(
        self,
        user_id: str,
        trial_period_days: int = 7,
        trial_type: SubscriptionType = SubscriptionType.TRIAL
    ) -> User:
        """Start a trial for a user."""
        async with self.unit_of_work:
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")

            # Check if user is eligible for trial
            eligibility = await self.check_trial_eligibility(user_id)
            if not eligibility["eligible"]:
                raise ValueError(f"User not eligible for trial: {eligibility['reason']}")

            user.start_trial(trial_period_days, trial_type)

            user = await self.user_repository.update(user)
            await self._publish_events(user)
            await self.unit_of_work.commit()
            return user

    async def extend_trial(
        self,
        user_id: str,
        extension_days: int,
        reason: Optional[str] = None
    ) -> User:
        """Extend an existing trial."""
        async with self.unit_of_work:
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")

            if user.subscription_type != SubscriptionType.TRIAL:
                raise ValueError(f"User {user_id} does not have an active trial")

            # Extend the trial
            user.extend_subscription(extension_days, SubscriptionType.TRIAL)

            # Add metadata about the extension
            if reason:
                metadata = user.metadata or {}
                extensions = metadata.get("trial_extensions", [])
                extensions.append({
                    "extended_at": datetime.utcnow().isoformat(),
                    "days": extension_days,
                    "reason": reason
                })
                metadata["trial_extensions"] = extensions
                user.metadata = metadata

            user = await self.user_repository.update(user)
            await self._publish_events(user)
            await self.unit_of_work.commit()
            return user

    async def end_trial(
        self,
        user_id: str,
        reason: Optional[str] = None,
        promote_to_premium: bool = False
    ) -> User:
        """End a user's trial."""
        async with self.unit_of_work:
            user = await self.user_repository.get_by_id(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found")

            if user.subscription_type != SubscriptionType.TRIAL:
                raise ValueError(f"User {user_id} does not have an active trial")

            if promote_to_premium:
                # Convert trial to premium with remaining time
                remaining_days = (user.subscription_expires_at - datetime.utcnow()).days
                if remaining_days > 0:
                    user.extend_subscription(remaining_days, SubscriptionType.PREMIUM)
                else:
                    # Trial already expired, start fresh premium
                    user.subscription_type = SubscriptionType.FREE
                    user.subscription_expires_at = None
            else:
                # End trial and revert to free
                user.subscription_type = SubscriptionType.FREE
                user.subscription_expires_at = None

            # Record trial end reason
            if reason:
                metadata = user.metadata or {}
                metadata["trial_ended_at"] = datetime.utcnow().isoformat()
                metadata["trial_end_reason"] = reason
                user.metadata = metadata

            user = await self.user_repository.update(user)
            await self._publish_events(user)
            await self.unit_of_work.commit()
            return user

    async def check_trial_eligibility(self, user_id: str) -> dict:
        """Check if a user is eligible for a trial."""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            return {
                "eligible": False,
                "reason": "User not found"
            }

        # Check if user is blocked
        if user.status == UserStatus.BLOCKED:
            return {
                "eligible": False,
                "reason": "User is blocked"
            }

        # Check if user already has an active subscription
        if user.has_active_subscription():
            return {
                "eligible": False,
                "reason": f"User already has active {user.subscription_type.value} subscription"
            }

        # Check if user has already used a trial
        if user.metadata and user.metadata.get("trial_used"):
            return {
                "eligible": False,
                "reason": "User has already used their trial"
            }

        return {
            "eligible": True,
            "reason": None
        }

    async def get_trial_users(self) -> List[User]:
        """Get all users with active trials."""
        return await self.user_repository.find_trial_users()

    async def get_expiring_trials(self, days: int = 3) -> List[User]:
        """Get users whose trials expire within specified days."""
        return await self.user_repository.find_expiring_users(days)

    async def process_expired_trials(self) -> List[User]:
        """Process users whose trials have expired."""
        expired_users = await self.user_repository.find_expired_users()
        processed_users = []

        for user in expired_users:
            if user.subscription_type == SubscriptionType.TRIAL:
                try:
                    processed_user = await self.end_trial(
                        str(user.id),
                        reason="Trial expired automatically"
                    )
                    processed_users.append(processed_user)
                except Exception as e:
                    # Log error but continue processing
                    print(f"Error processing expired trial for user {user.id}: {e}")

        return processed_users

    async def send_trial_reminders(self, days_before_expiry: int = 1) -> List[User]:
        """Get users who need trial expiry reminders."""
        expiring_users = await self.get_expiring_trials(days_before_expiry)
        
        # Filter to only trial users who haven't been reminded recently
        users_to_remind = []
        for user in expiring_users:
            if user.subscription_type != SubscriptionType.TRIAL:
                continue
                
            # Check if reminder was sent recently
            metadata = user.metadata or {}
            last_reminder = metadata.get("last_trial_reminder")
            
            if not last_reminder:
                users_to_remind.append(user)
            else:
                last_reminder_date = datetime.fromisoformat(last_reminder)
                if (datetime.utcnow() - last_reminder_date).days >= 1:
                    users_to_remind.append(user)

        # Mark users as reminded
        for user in users_to_remind:
            try:
                async with self.unit_of_work:
                    metadata = user.metadata or {}
                    metadata["last_trial_reminder"] = datetime.utcnow().isoformat()
                    user.metadata = metadata
                    
                    await self.user_repository.update(user)
                    await self.unit_of_work.commit()
            except Exception as e:
                print(f"Error updating reminder timestamp for user {user.id}: {e}")

        return users_to_remind

    async def get_trial_statistics(self) -> dict:
        """Get trial usage statistics."""
        all_users = await self.user_repository.get_all()
        
        stats = {
            "total_users": len(all_users),
            "active_trials": 0,
            "completed_trials": 0,
            "expired_trials": 0,
            "trial_to_premium_conversions": 0,
            "trial_conversion_rate": 0.0,
            "average_trial_duration": 0.0
        }

        trial_durations = []
        total_trials = 0

        for user in all_users:
            if user.subscription_type == SubscriptionType.TRIAL:
                stats["active_trials"] += 1
                total_trials += 1
                
                # Calculate trial duration so far
                if user.subscription_expires_at:
                    trial_start = user.subscription_expires_at - timedelta(days=7)  # Assuming 7-day trials
                    duration = (datetime.utcnow() - trial_start).days
                    trial_durations.append(duration)
            
            elif user.metadata and user.metadata.get("trial_used"):
                total_trials += 1
                
                if user.subscription_type == SubscriptionType.PREMIUM:
                    stats["trial_to_premium_conversions"] += 1
                    stats["completed_trials"] += 1
                else:
                    stats["expired_trials"] += 1

        # Calculate conversion rate
        if total_trials > 0:
            stats["trial_conversion_rate"] = (stats["trial_to_premium_conversions"] / total_trials) * 100

        # Calculate average trial duration
        if trial_durations:
            stats["average_trial_duration"] = sum(trial_durations) / len(trial_durations)

        return stats

    async def bulk_grant_trial_extensions(
        self,
        user_ids: List[str],
        extension_days: int,
        reason: str
    ) -> List[User]:
        """Grant trial extensions to multiple users."""
        extended_users = []
        
        for user_id in user_ids:
            try:
                user = await self.extend_trial(user_id, extension_days, reason)
                extended_users.append(user)
            except Exception as e:
                # Log error but continue processing
                print(f"Error extending trial for user {user_id}: {e}")

        return extended_users

    async def get_trial_usage_patterns(self) -> dict:
        """Get patterns of trial usage."""
        trial_users = await self.get_trial_users()
        
        patterns = {
            "by_signup_source": {},
            "by_referrer": {},
            "by_language": {},
            "activity_levels": {
                "high": 0,    # Last active < 1 day
                "medium": 0,  # Last active 1-3 days
                "low": 0,     # Last active > 3 days
                "inactive": 0 # Never active
            }
        }

        for user in trial_users:
            # Group by invite source
            source = user.invite_source or "direct"
            patterns["by_signup_source"][source] = patterns["by_signup_source"].get(source, 0) + 1
            
            # Group by referrer presence
            referrer_type = "referred" if user.referrer_id else "organic"
            patterns["by_referrer"][referrer_type] = patterns["by_referrer"].get(referrer_type, 0) + 1
            
            # Group by language
            lang = user.profile.language_code or "unknown"
            patterns["by_language"][lang] = patterns["by_language"].get(lang, 0) + 1
            
            # Analyze activity level
            if user.last_activity_at:
                days_since_activity = (datetime.utcnow() - user.last_activity_at).days
                if days_since_activity < 1:
                    patterns["activity_levels"]["high"] += 1
                elif days_since_activity <= 3:
                    patterns["activity_levels"]["medium"] += 1
                else:
                    patterns["activity_levels"]["low"] += 1
            else:
                patterns["activity_levels"]["inactive"] += 1

        return patterns

    async def _publish_events(self, user: User) -> None:
        """Publish domain events."""
        events = user.get_domain_events()
        for event in events:
            await event_bus.publish(event)
        user.clear_domain_events()