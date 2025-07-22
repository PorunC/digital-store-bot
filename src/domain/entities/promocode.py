"""Promocode domain entity with complete functionality."""

import secrets
import string
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import Field, validator

from ..events.promocode_events import (
    PromocodeCreated,
    PromocodeActivated,
    PromocodeExpired,
    PromocodeDeactivated
)
from .base import AggregateRoot


class PromocodeStatus(str, Enum):
    """Promocode status enumeration."""
    ACTIVE = "active"
    USED = "used"
    EXPIRED = "expired"
    DEACTIVATED = "deactivated"


class PromocodeType(str, Enum):
    """Promocode type enumeration."""
    TRIAL_EXTENSION = "trial_extension"
    SUBSCRIPTION_BONUS = "subscription_bonus"
    DISCOUNT = "discount"
    FREE_PRODUCT = "free_product"


class Promocode(AggregateRoot):
    """Promocode aggregate root."""

    code: str = Field(..., min_length=4, max_length=50)
    promocode_type: PromocodeType
    duration_days: int = Field(..., gt=0)
    
    # Usage tracking
    status: PromocodeStatus = Field(default=PromocodeStatus.ACTIVE)
    activated_by_id: Optional[UUID] = None
    activated_at: Optional[datetime] = None
    
    # Validity
    expires_at: Optional[datetime] = None
    max_uses: int = Field(default=1, gt=0)
    current_uses: int = Field(default=0, ge=0)
    
    # Additional data
    description: Optional[str] = None
    discount_percentage: Optional[float] = Field(None, ge=0, le=100)
    product_id: Optional[UUID] = None  # For free product codes

    @classmethod
    def create(
        cls,
        code: Optional[str] = None,
        promocode_type: PromocodeType = PromocodeType.TRIAL_EXTENSION,
        duration_days: int = 7,
        max_uses: int = 1,
        expires_at: Optional[datetime] = None,
        description: Optional[str] = None,
        discount_percentage: Optional[float] = None,
        product_id: Optional[UUID] = None
    ) -> "Promocode":
        """Create a new promocode."""
        if not code:
            code = cls._generate_code()
            
        promocode = cls(
            code=code.upper(),
            promocode_type=promocode_type,
            duration_days=duration_days,
            max_uses=max_uses,
            expires_at=expires_at,
            description=description,
            discount_percentage=discount_percentage,
            product_id=product_id
        )
        
        # Publish domain event
        event = PromocodeCreated.create(
            promocode_id=str(promocode.id),
            code=promocode.code,
            promocode_type=promocode_type.value,
            duration_days=duration_days,
            max_uses=max_uses
        )
        promocode.add_domain_event(event)
        
        return promocode

    @classmethod
    def create_trial_extension(
        cls,
        duration_days: int = 7,
        code: Optional[str] = None,
        description: Optional[str] = None
    ) -> "Promocode":
        """Create a trial extension promocode."""
        return cls.create(
            code=code,
            promocode_type=PromocodeType.TRIAL_EXTENSION,
            duration_days=duration_days,
            description=description or f"{duration_days}-day trial extension"
        )

    @classmethod
    def create_discount(
        cls,
        discount_percentage: float,
        code: Optional[str] = None,
        description: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> "Promocode":
        """Create a discount promocode."""
        return cls.create(
            code=code,
            promocode_type=PromocodeType.DISCOUNT,
            duration_days=0,  # Discounts don't add time
            discount_percentage=discount_percentage,
            description=description or f"{discount_percentage}% discount",
            expires_at=expires_at
        )

    def activate(self, user_id: UUID) -> None:
        """Activate the promocode for a user."""
        if not self.can_be_activated():
            raise ValueError(f"Promocode cannot be activated: {self._get_activation_error()}")
            
        self.activated_by_id = user_id
        self.activated_at = datetime.utcnow()
        self.current_uses += 1
        
        if self.current_uses >= self.max_uses:
            self.status = PromocodeStatus.USED
        
        self.mark_updated()
        
        # Publish domain event
        event = PromocodeActivated.create(
            promocode_id=str(self.id),
            code=self.code,
            user_id=str(user_id),
            promocode_type=self.promocode_type.value,
            duration_days=self.duration_days
        )
        self.add_domain_event(event)

    def deactivate(self, reason: Optional[str] = None) -> None:
        """Deactivate the promocode."""
        if self.status == PromocodeStatus.DEACTIVATED:
            return
            
        self.status = PromocodeStatus.DEACTIVATED
        self.mark_updated()
        
        event = PromocodeDeactivated.create(
            promocode_id=str(self.id),
            code=self.code,
            reason=reason
        )
        self.add_domain_event(event)

    def check_expiration(self) -> None:
        """Check and handle expiration."""
        if self.is_expired and self.status == PromocodeStatus.ACTIVE:
            self.status = PromocodeStatus.EXPIRED
            self.mark_updated()
            
            event = PromocodeExpired.create(
                promocode_id=str(self.id),
                code=self.code
            )
            self.add_domain_event(event)

    def can_be_activated(self) -> bool:
        """Check if promocode can be activated."""
        return (
            self.status == PromocodeStatus.ACTIVE and
            not self.is_expired and
            self.current_uses < self.max_uses
        )

    def can_be_used_by(self, user_id: UUID) -> bool:
        """Check if promocode can be used by specific user."""
        if not self.can_be_activated():
            return False
            
        # Single-use codes can't be reused by same user
        if self.max_uses == 1 and self.activated_by_id == user_id:
            return False
            
        return True

    @property
    def is_expired(self) -> bool:
        """Check if promocode has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def is_active(self) -> bool:
        """Check if promocode is active."""
        return (
            self.status == PromocodeStatus.ACTIVE and
            not self.is_expired
        )

    @property
    def uses_remaining(self) -> int:
        """Get remaining uses."""
        return max(0, self.max_uses - self.current_uses)

    @property
    def is_single_use(self) -> bool:
        """Check if promocode is single-use."""
        return self.max_uses == 1

    def _get_activation_error(self) -> str:
        """Get reason why promocode cannot be activated."""
        if self.status != PromocodeStatus.ACTIVE:
            return f"Status is {self.status.value}"
        if self.is_expired:
            return "Promocode has expired"
        if self.current_uses >= self.max_uses:
            return "No uses remaining"
        return "Unknown error"

    @staticmethod
    def _generate_code(length: int = 8) -> str:
        """Generate a random promocode."""
        # Use uppercase letters and numbers, exclude confusing characters
        alphabet = string.ascii_uppercase + string.digits
        alphabet = alphabet.replace('0', '').replace('O', '').replace('I', '').replace('1')
        
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @validator("code")
    def validate_code(cls, v):
        """Validate promocode format."""
        if not v:
            raise ValueError("Promocode cannot be empty")
        
        # Convert to uppercase and validate characters
        v = v.upper().strip()
        if not v.isalnum():
            raise ValueError("Promocode must contain only letters and numbers")
            
        return v

    @validator("current_uses")
    def validate_current_uses(cls, v, values):
        """Validate current uses doesn't exceed max uses."""
        max_uses = values.get("max_uses", 1)
        if v > max_uses:
            raise ValueError("Current uses cannot exceed max uses")
        return v