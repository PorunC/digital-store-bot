"""Product domain entity with complete feature set."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, validator

from ..events.product_events import ProductCreated, ProductUpdated, ProductActivated, ProductDeactivated
from ..value_objects.money import Money
from ..value_objects.product_info import ProductInfo, DeliveryType
from .base import AggregateRoot


class ProductCategory(str, Enum):
    """Product categories."""
    SOFTWARE = "software"
    GAMING = "gaming"
    SUBSCRIPTION = "subscription"
    DIGITAL = "digital"
    EDUCATION = "education"


class ProductStatus(str, Enum):
    """Product status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    OUT_OF_STOCK = "out_of_stock"


class Product(AggregateRoot):
    """Product aggregate root."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=1000)
    category: ProductCategory
    price: Money
    duration_days: int = Field(default=0, ge=0)  # 0 = permanent
    delivery_type: DeliveryType
    delivery_template: str = Field(..., min_length=1)
    key_format: Optional[str] = None
    stock: int = Field(default=-1)  # -1 = unlimited
    status: ProductStatus = Field(default=ProductStatus.ACTIVE)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        category: ProductCategory,
        price: Money,
        duration_days: int,
        delivery_type: DeliveryType,
        delivery_template: str,
        key_format: Optional[str] = None,
        stock: int = -1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Product":
        """Create a new product."""
        product = cls(
            name=name,
            description=description,
            category=category,
            price=price,
            duration_days=duration_days,
            delivery_type=delivery_type,
            delivery_template=delivery_template,
            key_format=key_format,
            stock=stock,
            metadata=metadata or {},
        )
        
        # Publish domain event
        event = ProductCreated.create(
            product_id=str(product.id),
            name=name,
            category=category.value if hasattr(category, 'value') else str(category),
            price_amount=float(price.amount),
            price_currency=price.currency
        )
        product.add_domain_event(event)
        
        return product

    def update_info(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        price: Optional[Money] = None,
        delivery_template: Optional[str] = None,
    ) -> None:
        """Update product information."""
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        if price is not None:
            self.price = price
        if delivery_template is not None:
            self.delivery_template = delivery_template
            
        self.mark_updated()
        
        # Publish domain event
        event = ProductUpdated.create(
            product_id=str(self.id),
            updated_fields={
                "name": name,
                "description": description,
                "price": price.model_dump() if price else None,
                "delivery_template": delivery_template,
            }
        )
        self.add_domain_event(event)

    def activate(self) -> None:
        """Activate the product."""
        if self.status == ProductStatus.ACTIVE:
            return
            
        self.status = ProductStatus.ACTIVE
        self.mark_updated()
        
        event = ProductActivated.create(product_id=str(self.id))
        self.add_domain_event(event)

    def deactivate(self) -> None:
        """Deactivate the product."""
        if self.status == ProductStatus.INACTIVE:
            return
            
        self.status = ProductStatus.INACTIVE
        self.mark_updated()
        
        event = ProductDeactivated.create(product_id=str(self.id))
        self.add_domain_event(event)

    def decrease_stock(self, quantity: int = 1) -> None:
        """Decrease product stock."""
        if self.stock == -1:  # Unlimited stock
            return
            
        if self.stock < quantity:
            raise ValueError("Insufficient stock")
            
        self.stock -= quantity
        if self.stock == 0:
            self.status = ProductStatus.OUT_OF_STOCK
            
        self.mark_updated()

    def increase_stock(self, quantity: int = 1) -> None:
        """Increase product stock."""
        if self.stock == -1:  # Unlimited stock
            return
            
        self.stock += quantity
        if self.status == ProductStatus.OUT_OF_STOCK and self.stock > 0:
            self.status = ProductStatus.ACTIVE
            
        self.mark_updated()

    @property
    def is_available(self) -> bool:
        """Check if product is available for purchase."""
        return (
            self.status == ProductStatus.ACTIVE and
            (self.stock == -1 or self.stock > 0)
        )

    @property
    def is_permanent(self) -> bool:
        """Check if product provides permanent access."""
        return self.duration_days == 0

    @property
    def is_subscription(self) -> bool:
        """Check if product is a subscription (has duration)."""
        return self.duration_days > 0

    def format_delivery_message(self, **kwargs) -> str:
        """Format delivery message with provided data."""
        try:
            return self.delivery_template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing delivery data: {e}")

    @validator("stock")
    def validate_stock(cls, v):
        """Validate stock value."""
        if v < -1:
            raise ValueError("Stock must be -1 (unlimited) or >= 0")
        return v

    @validator("delivery_template")
    def validate_delivery_template(cls, v):
        """Validate delivery template."""
        if not v.strip():
            raise ValueError("Delivery template cannot be empty")
        return v.strip()