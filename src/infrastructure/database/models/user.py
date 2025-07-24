"""User SQLAlchemy model."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class UserModel(Base):
    """User database model."""

    __tablename__ = "users"

    # Telegram info
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True
    )
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str] = mapped_column(
        String(5),
        default="en",
        nullable=False
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False
    )

    # Trial system
    is_trial_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trial_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    trial_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Subscription system
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    subscription_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    total_subscription_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Referral system
    referrer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    invite_source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    total_referrals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Statistics
    total_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_spent_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_spent_currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False
    )
    last_active_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Additional data
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    orders: Mapped[List["OrderModel"]] = relationship(
        "OrderModel",
        back_populates="user",
        foreign_keys="OrderModel.user_id"
    )
    
    referrals_made: Mapped[List["ReferralModel"]] = relationship(
        "ReferralModel",
        back_populates="referrer",
        foreign_keys="ReferralModel.referrer_id",
        lazy="dynamic"
    )
    
    referral_received: Mapped[Optional["ReferralModel"]] = relationship(
        "ReferralModel",
        back_populates="referred_user",
        foreign_keys="ReferralModel.referred_user_id",
        uselist=False,
        lazy="select"
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<UserModel(id={self.id}, telegram_id={self.telegram_id}, first_name='{self.first_name}')>"