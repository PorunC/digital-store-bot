"""Promocode application service with complete functionality."""

from datetime import datetime, timedelta
from typing import List, Optional

from src.domain.entities.promocode import Promocode, PromocodeType, PromocodeStatus
from src.domain.entities.user import User, SubscriptionType
from src.domain.repositories.promocode_repository import PromocodeRepository
from src.domain.repositories.user_repository import UserRepository
from src.domain.repositories.base import UnitOfWork
from src.shared.events import event_bus


class PromocodeApplicationService:
    """Promocode application service handling promocode-related operations."""

    def __init__(
        self,
        unit_of_work: UnitOfWork
    ):
        self.unit_of_work = unit_of_work
        
    def _get_promocode_repository(self) -> PromocodeRepository:
        """Get promocode repository from unit of work."""
        from src.infrastructure.database.repositories.promocode_repository import SqlAlchemyPromocodeRepository
        if hasattr(self.unit_of_work, 'session') and self.unit_of_work.session:
            return SqlAlchemyPromocodeRepository(self.unit_of_work.session)
        else:
            raise RuntimeError("Unit of work session not available")
            
    def _get_user_repository(self) -> UserRepository:
        """Get user repository from unit of work."""
        from src.infrastructure.database.repositories.user_repository import SqlAlchemyUserRepository
        if hasattr(self.unit_of_work, 'session') and self.unit_of_work.session:
            return SqlAlchemyUserRepository(self.unit_of_work.session)
        else:
            raise RuntimeError("Unit of work session not available")

    async def create_promocode(
        self,
        code: str,
        promocode_type: PromocodeType,
        duration_days: int = 0,
        discount_percent: Optional[float] = None,
        discount_amount: Optional[float] = None,
        max_uses: int = -1,
        expires_at: Optional[datetime] = None,
        metadata: Optional[dict] = None
    ) -> Promocode:
        """Create a new promocode."""
        async with self.unit_of_work:
            # Check if promocode with same code exists
            existing_promocode = await self._get_promocode_repository().find_by_code(code)
            if existing_promocode:
                raise ValueError(f"Promocode with code '{code}' already exists")

            # Validate promocode parameters
            if promocode_type == PromocodeType.TRIAL_EXTENSION and duration_days <= 0:
                raise ValueError("Trial extension promocodes must have duration_days > 0")
            
            if promocode_type == PromocodeType.DISCOUNT:
                if not discount_percent and not discount_amount:
                    raise ValueError("Discount promocodes must have discount_percent or discount_amount")

            promocode = Promocode.create(
                code=code.upper(),
                promocode_type=promocode_type,
                duration_days=duration_days,
                discount_percent=discount_percent,
                discount_amount=discount_amount,
                max_uses=max_uses,
                expires_at=expires_at,
                metadata=metadata or {}
            )

            promocode = await self._get_promocode_repository().add(promocode)
            await self._publish_events(promocode)
            await self.unit_of_work.commit()
            return promocode

    async def get_promocode_by_id(self, promocode_id: str) -> Optional[Promocode]:
        """Get promocode by ID."""
        async with self.unit_of_work:
            return await self._get_promocode_repository().get_by_id(promocode_id)

    async def get_promocode_by_code(self, code: str) -> Optional[Promocode]:
        """Get promocode by code."""
        async with self.unit_of_work:
            return await self._get_promocode_repository().find_by_code(code.upper())

    async def validate_promocode(self, code: str, user_id: Optional[str] = None) -> dict:
        """Validate if a promocode can be used."""
        async with self.unit_of_work:
            promocode = await self._get_promocode_repository().find_by_code(code.upper())
            
            if not promocode:
                return {
                    "valid": False,
                    "error": "Promocode not found",
                    "promocode": None
                }

            # Check if promocode is active
            if promocode.status != PromocodeStatus.ACTIVE:
                return {
                    "valid": False,
                    "error": f"Promocode is {promocode.status.value}",
                    "promocode": promocode
                }

            # Check expiration
            if promocode.expires_at and promocode.expires_at <= datetime.utcnow():
                return {
                    "valid": False,
                    "error": "Promocode has expired",
                    "promocode": promocode
                }

            # Check usage limits
            if promocode.max_uses != -1 and promocode.current_uses >= promocode.max_uses:
                return {
                    "valid": False,
                    "error": "Promocode usage limit reached",
                    "promocode": promocode
                }

            # Additional user-specific validations
            if user_id:
                user = await self._get_user_repository().get_by_id(user_id)
                if not user:
                    return {
                        "valid": False,
                        "error": "User not found",
                        "promocode": promocode
                    }

                # Check if user can use trial extension codes
                if promocode.promocode_type == PromocodeType.TRIAL_EXTENSION:
                    if user.has_active_subscription():
                        return {
                            "valid": False,
                            "error": "Cannot use trial extension with active subscription",
                            "promocode": promocode
                        }

            return {
                "valid": True,
                "error": None,
                "promocode": promocode
            }

    async def use_promocode(
        self,
        code: str,
        user_id: str,
        order_id: Optional[str] = None
    ) -> dict:
        """Use a promocode."""
        async with self.unit_of_work:
            # Validate promocode
            validation = await self.validate_promocode(code, user_id)
            if not validation["valid"]:
                return validation

            promocode = validation["promocode"]
            user = await self._get_user_repository().get_by_id(user_id)

            # Apply promocode effects
            result = {}
            
            if promocode.promocode_type == PromocodeType.TRIAL_EXTENSION:
                # Extend user's trial/subscription
                user.extend_subscription(
                    promocode.duration_days,
                    SubscriptionType.TRIAL if not user.has_active_subscription() else user.subscription_type
                )
                result["effect"] = f"Extended subscription by {promocode.duration_days} days"
                
            elif promocode.promocode_type == PromocodeType.DISCOUNT:
                # Calculate discount (handled at order level, just record usage)
                discount_value = promocode.discount_percent or promocode.discount_amount
                result["effect"] = f"Applied discount: {discount_value}{'%' if promocode.discount_percent else ' units'}"
                
            elif promocode.promocode_type == PromocodeType.FREE_TRIAL:
                # Grant free trial
                user.start_trial(promocode.duration_days, SubscriptionType.TRIAL)
                result["effect"] = f"Granted {promocode.duration_days} days free trial"

            # Update promocode usage
            promocode.use_promocode(user_id, order_id)

            # Save changes
            await self._get_user_repository().update(user)
            promocode = await self._get_promocode_repository().update(promocode)
            
            await self._publish_events(promocode)
            await self.unit_of_work.commit()

            result.update({
                "valid": True,
                "error": None,
                "promocode": promocode,
                "user": user
            })

            return result

    async def activate_promocode(self, promocode_id: str) -> Promocode:
        """Activate a promocode."""
        async with self.unit_of_work:
            promocode = await self._get_promocode_repository().get_by_id(promocode_id)
            if not promocode:
                raise ValueError(f"Promocode with ID {promocode_id} not found")

            promocode.activate()

            promocode = await self._get_promocode_repository().update(promocode)
            await self._publish_events(promocode)
            await self.unit_of_work.commit()
            return promocode

    async def deactivate_promocode(
        self,
        promocode_id: str,
        reason: Optional[str] = None
    ) -> Promocode:
        """Deactivate a promocode."""
        async with self.unit_of_work:
            promocode = await self._get_promocode_repository().get_by_id(promocode_id)
            if not promocode:
                raise ValueError(f"Promocode with ID {promocode_id} not found")

            promocode.deactivate(reason)

            promocode = await self._get_promocode_repository().update(promocode)
            await self._publish_events(promocode)
            await self.unit_of_work.commit()
            return promocode

    async def get_active_promocodes(self) -> List[Promocode]:
        """Get all active promocodes."""
        async with self.unit_of_work:
            return await self._get_promocode_repository().find_active_codes()

    async def get_promocodes_by_type(self, promocode_type: PromocodeType) -> List[Promocode]:
        """Get promocodes by type."""
        async with self.unit_of_work:
            return await self._get_promocode_repository().find_by_type(promocode_type)

    async def search_promocodes(self, query: str) -> List[Promocode]:
        """Search promocodes by query."""
        async with self.unit_of_work:
            return await self._get_promocode_repository().search_codes(query)

    async def process_expired_promocodes(self) -> List[Promocode]:
        """Process expired promocodes."""
        async with self.unit_of_work:
            expired_promocodes = await self._get_promocode_repository().find_expired_codes()
            
        processed_promocodes = []

        for promocode in expired_promocodes:
            try:
                async with self.unit_of_work:
                    promocode.expire()
                    promocode = await self._get_promocode_repository().update(promocode)
                    await self._publish_events(promocode)
                    await self.unit_of_work.commit()
                    processed_promocodes.append(promocode)
            except Exception as e:
                # Log error but continue processing
                print(f"Error processing expired promocode {promocode.id}: {e}")

        return processed_promocodes

    async def process_exhausted_promocodes(self) -> List[Promocode]:
        """Process promocodes that have reached max uses."""
        async with self.unit_of_work:
            exhausted_promocodes = await self._get_promocode_repository().find_exhausted_codes()
            
        processed_promocodes = []

        for promocode in exhausted_promocodes:
            try:
                async with self.unit_of_work:
                    promocode.deactivate("Maximum usage reached")
                    promocode = await self._get_promocode_repository().update(promocode)
                    await self._publish_events(promocode)
                    await self.unit_of_work.commit()
                    processed_promocodes.append(promocode)
            except Exception as e:
                # Log error but continue processing
                print(f"Error processing exhausted promocode {promocode.id}: {e}")

        return processed_promocodes

    async def create_bulk_promocodes(
        self,
        prefix: str,
        count: int,
        promocode_type: PromocodeType,
        duration_days: int = 0,
        discount_percent: Optional[float] = None,
        discount_amount: Optional[float] = None,
        max_uses: int = 1,
        expires_at: Optional[datetime] = None,
        metadata: Optional[dict] = None
    ) -> List[Promocode]:
        """Create multiple promocodes with generated codes."""
        import random
        import string

        promocodes = []
        
        for i in range(count):
            # Generate unique code
            async with self.unit_of_work:
                while True:
                    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
                    code = f"{prefix}{suffix}"
                    
                    existing = await self._get_promocode_repository().find_by_code(code)
                    if not existing:
                        break

            promocode = await self.create_promocode(
                code=code,
                promocode_type=promocode_type,
                duration_days=duration_days,
                discount_percent=discount_percent,
                discount_amount=discount_amount,
                max_uses=max_uses,
                expires_at=expires_at,
                metadata=metadata
            )
            promocodes.append(promocode)

        return promocodes

    async def get_promocode_statistics(self) -> dict:
        """Get promocode usage statistics."""
        async with self.unit_of_work:
            return await self._get_promocode_repository().get_usage_stats()

    async def calculate_discount(
        self,
        promocode: Promocode,
        original_amount: float
    ) -> dict:
        """Calculate discount amount for a promocode."""
        if promocode.promocode_type != PromocodeType.DISCOUNT:
            return {
                "discount_amount": 0.0,
                "final_amount": original_amount,
                "discount_type": "none"
            }

        discount_amount = 0.0
        discount_type = "none"

        if promocode.discount_percent:
            discount_amount = original_amount * (promocode.discount_percent / 100)
            discount_type = "percentage"
        elif promocode.discount_amount:
            discount_amount = min(promocode.discount_amount, original_amount)
            discount_type = "fixed"

        final_amount = max(0.0, original_amount - discount_amount)

        return {
            "discount_amount": discount_amount,
            "final_amount": final_amount,
            "discount_type": discount_type,
            "original_amount": original_amount
        }

    async def _publish_events(self, promocode: Promocode) -> None:
        """Publish domain events."""
        events = promocode.get_domain_events()
        for event in events:
            await event_bus.publish(event)
        promocode.clear_domain_events()