"""Referral SQLAlchemy model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ReferralModel(Base):
    """Referral database model."""

    __tablename__ = "referrals"

    # Foreign keys
    referrer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    referred_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        unique=True  # Each user can only be referred once
    )

    # Status tracking
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)

    # Reward tracking flags
    first_level_reward_granted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    second_level_reward_granted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Activation tracking
    activated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Purchase tracking
    first_purchase_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Legacy reward tracking (kept for compatibility)
    referred_rewarded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    referred_bonus_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Referrer reward tracking
    referrer_rewarded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    referrer_bonus_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Invite source tracking
    invite_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Metadata for additional tracking
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Relationships
    referrer: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="referrals_made",
        foreign_keys=[referrer_id]
    )
    referred_user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="referral_received",
        foreign_keys=[referred_user_id]
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<ReferralModel(id={self.id}, referrer_id={self.referrer_id}, "
            f"referred_user_id={self.referred_user_id})>"
        )