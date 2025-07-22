"""Invite SQLAlchemy model."""

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class InviteModel(Base):
    """Invite link database model."""

    __tablename__ = "invites"

    # Invite details
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True
    )
    hash_code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Statistics
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Additional data
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    campaign: Mapped[str] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<InviteModel(id={self.id}, name='{self.name}', "
            f"clicks={self.clicks}, conversions={self.conversions})>"
        )