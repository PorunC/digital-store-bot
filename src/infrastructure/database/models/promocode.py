"""Promocode SQLAlchemy model."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class PromocodeModel(Base):
    """Promocode database model."""

    __tablename__ = "promocodes"

    # Promocode details
    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True
    )
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Usage tracking
    is_activated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activated_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    activated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Validity
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Additional data
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    max_uses: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    current_uses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    activated_by: Mapped[Optional["UserModel"]] = relationship(
        "UserModel",
        foreign_keys=[activated_by_id]
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<PromocodeModel(id={self.id}, code='{self.code}', "
            f"duration_days={self.duration_days}, is_activated={self.is_activated})>"
        )