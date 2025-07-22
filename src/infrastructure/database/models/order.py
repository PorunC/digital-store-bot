"""Order SQLAlchemy model."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class OrderModel(Base):
    """Order database model."""

    __tablename__ = "orders"

    # Foreign keys
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id"),
        nullable=False,
        index=True
    )

    # Payment identifiers
    payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    external_payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Order details
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_description: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Pricing
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Payment details
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    payment_gateway: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    payment_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True
    )

    # Timestamps
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Additional data
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    referrer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    promocode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_extend: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="orders",
        foreign_keys=[user_id]
    )
    product: Mapped["ProductModel"] = relationship(
        "ProductModel",
        back_populates="orders"
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<OrderModel(id={self.id}, user_id={self.user_id}, "
            f"product_name='{self.product_name}', status='{self.status}')>"
        )