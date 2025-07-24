"""Product SQLAlchemy model."""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ProductModel(Base):
    """Product database model."""

    __tablename__ = "products"

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Pricing
    price_amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2),
        nullable=False
    )
    price_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    
    # Product details
    duration_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivery_type: Mapped[str] = mapped_column(String(50), nullable=False)
    delivery_template: Mapped[str] = mapped_column(Text, nullable=False)
    key_format: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Stock management
    stock: Mapped[int] = mapped_column(Integer, default=-1, nullable=False)  # -1 = unlimited
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        index=True
    )
    
    # Additional data
    extra_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False
    )

    # Relationships
    orders: Mapped[List["OrderModel"]] = relationship(
        "OrderModel",
        back_populates="product"
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<ProductModel(id={self.id}, name='{self.name}', category='{self.category}')>"