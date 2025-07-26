"""Invite link domain entity with analytics."""

import hashlib
import secrets
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field, validator

from ..events.invite_events import (
    InviteCreated,
    InviteClicked,
    InviteConverted,
    InviteDeactivated
)
from .base import AggregateRoot


class InviteStatus(str, Enum):
    """Invite status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"


class Invite(AggregateRoot):
    """Invite link aggregate root for tracking marketing campaigns."""

    name: str = Field(..., min_length=1, max_length=100)
    hash_code: str = Field(..., min_length=8, max_length=64)
    
    # Analytics
    clicks: int = Field(default=0, ge=0)
    conversions: int = Field(default=0, ge=0)
    
    # Status and metadata
    status: InviteStatus = Field(default=InviteStatus.ACTIVE)
    description: Optional[str] = Field(None, max_length=255)
    campaign: Optional[str] = Field(None, max_length=100)
    
    # Validity
    expires_at: Optional[datetime] = None
    max_uses: Optional[int] = Field(None, gt=0)
    
    # Tracking
    last_clicked_at: Optional[datetime] = None
    last_converted_at: Optional[datetime] = None

    @classmethod
    def create(
        cls,
        name: str,
        description: Optional[str] = None,
        campaign: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        max_uses: Optional[int] = None
    ) -> "Invite":
        """Create a new invite link."""
        hash_code = cls._generate_hash_code(name)
        
        invite = cls(
            name=name,
            hash_code=hash_code,
            description=description,
            campaign=campaign,
            expires_at=expires_at,
            max_uses=max_uses
        )
        
        # Publish domain event
        event = InviteCreated.create(
            invite_id=str(invite.id),
            name=name,
            hash_code=hash_code,
            campaign=campaign
        )
        invite.add_domain_event(event)
        
        return invite

    def record_click(self, user_info: Optional[dict] = None) -> None:
        """Record a click on the invite link."""
        if not self.is_active:
            return
            
        self.clicks += 1
        self.last_clicked_at = datetime.utcnow()
        self.mark_updated()
        
        # Check if expired due to max uses
        if self.max_uses and self.clicks >= self.max_uses:
            self.status = InviteStatus.EXPIRED
        
        # Publish domain event
        event = InviteClicked.create(
            invite_id=str(self.id),
            name=self.name,
            hash_code=self.hash_code,
            total_clicks=self.clicks,
            user_info=user_info or {}
        )
        self.add_domain_event(event)

    def record_conversion(self, user_id: str, conversion_type: str = "registration") -> None:
        """Record a conversion (user registration/purchase)."""
        if not self.is_active:
            return
            
        self.conversions += 1
        self.last_converted_at = datetime.utcnow()
        self.mark_updated()
        
        # Publish domain event
        event = InviteConverted.create(
            invite_id=str(self.id),
            name=self.name,
            hash_code=self.hash_code,
            user_id=user_id,
            conversion_type=conversion_type,
            total_conversions=self.conversions
        )
        self.add_domain_event(event)

    def deactivate(self, reason: Optional[str] = None) -> None:
        """Deactivate the invite link."""
        if self.status == InviteStatus.INACTIVE:
            return
            
        self.status = InviteStatus.INACTIVE
        self.mark_updated()
        
        event = InviteDeactivated.create(
            invite_id=str(self.id),
            name=self.name,
            hash_code=self.hash_code,
            reason=reason
        )
        self.add_domain_event(event)

    def activate(self) -> None:
        """Reactivate the invite link."""
        if self.is_expired:
            raise ValueError("Cannot activate expired invite")
            
        self.status = InviteStatus.ACTIVE
        self.mark_updated()

    def check_expiration(self) -> None:
        """Check and handle expiration."""
        if self.is_expired and self.status == InviteStatus.ACTIVE:
            self.status = InviteStatus.EXPIRED
            self.mark_updated()

    @property
    def is_active(self) -> bool:
        """Check if invite is active."""
        return (
            self.status == InviteStatus.ACTIVE and
            not self.is_expired and
            (not self.max_uses or self.clicks < self.max_uses)
        )

    @property
    def is_expired(self) -> bool:
        """Check if invite has expired."""
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return True
        if self.max_uses and self.clicks >= self.max_uses:
            return True
        return False

    @property
    def conversion_rate(self) -> float:
        """Calculate conversion rate as percentage."""
        if self.clicks == 0:
            return 0.0
        return (self.conversions / self.clicks) * 100

    @property
    def uses_remaining(self) -> Optional[int]:
        """Get remaining uses if max_uses is set."""
        if not self.max_uses:
            return None
        return max(0, self.max_uses - self.clicks)

    @property
    def invite_url(self) -> str:
        """Get the invite URL."""
        return f"https://t.me/your_bot?start=invite_{self.hash_code}"

    def get_analytics(self) -> dict:
        """Get comprehensive analytics data."""
        return {
            "name": self.name,
            "hash_code": self.hash_code,
            "campaign": self.campaign,
            "status": self.status.value if hasattr(self.status, 'value') else str(self.status),
            "clicks": self.clicks,
            "conversions": self.conversions,
            "conversion_rate": self.conversion_rate,
            "uses_remaining": self.uses_remaining,
            "created_at": self.created_at,
            "last_clicked_at": self.last_clicked_at,
            "last_converted_at": self.last_converted_at,
            "is_active": self.is_active,
            "is_expired": self.is_expired
        }

    @staticmethod
    def _generate_hash_code(name: str, length: int = 12) -> str:
        """Generate a unique hash code for the invite."""
        # Create a hash based on name + timestamp + random
        timestamp = str(datetime.utcnow().timestamp())
        random_part = secrets.token_hex(8)
        combined = f"{name}_{timestamp}_{random_part}"
        
        # Create SHA-256 hash and take first `length` characters
        hash_object = hashlib.sha256(combined.encode())
        return hash_object.hexdigest()[:length]

    @validator("name")
    def validate_name(cls, v):
        """Validate invite name."""
        if not v or not v.strip():
            raise ValueError("Invite name cannot be empty")
        
        # Remove special characters that might cause issues in URLs
        cleaned = ''.join(c for c in v if c.isalnum() or c in '-_')
        if not cleaned:
            raise ValueError("Invite name must contain alphanumeric characters")
            
        return cleaned.strip()

    @validator("hash_code")
    def validate_hash_code(cls, v):
        """Validate hash code format."""
        if not v or len(v) < 8:
            raise ValueError("Hash code must be at least 8 characters")
        
        if not v.isalnum():
            raise ValueError("Hash code must be alphanumeric")
            
        return v.lower()

    @validator("conversions")
    def validate_conversions(cls, v, values):
        """Validate conversions don't exceed clicks."""
        clicks = values.get("clicks", 0)
        if v > clicks:
            raise ValueError("Conversions cannot exceed clicks")
        return v