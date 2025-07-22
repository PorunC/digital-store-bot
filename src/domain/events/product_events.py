"""Product domain events."""

from typing import Any, Dict, Optional

from .base import DomainEvent


class ProductCreated(DomainEvent):
    """Event published when a product is created."""

    @classmethod
    def create(
        cls,
        product_id: str,
        name: str,
        category: str,
        price_amount: float,
        price_currency: str
    ) -> "ProductCreated":
        """Create ProductCreated event."""
        return super().create(
            aggregate_id=product_id,
            aggregate_type="Product",
            name=name,
            category=category,
            price_amount=price_amount,
            price_currency=price_currency
        )


class ProductUpdated(DomainEvent):
    """Event published when a product is updated."""

    @classmethod
    def create(
        cls,
        product_id: str,
        updated_fields: Dict[str, Any]
    ) -> "ProductUpdated":
        """Create ProductUpdated event."""
        return super().create(
            aggregate_id=product_id,
            aggregate_type="Product",
            updated_fields=updated_fields
        )


class ProductActivated(DomainEvent):
    """Event published when a product is activated."""

    @classmethod
    def create(cls, product_id: str) -> "ProductActivated":
        """Create ProductActivated event."""
        return super().create(
            aggregate_id=product_id,
            aggregate_type="Product"
        )


class ProductDeactivated(DomainEvent):
    """Event published when a product is deactivated."""

    @classmethod
    def create(cls, product_id: str) -> "ProductDeactivated":
        """Create ProductDeactivated event."""
        return super().create(
            aggregate_id=product_id,
            aggregate_type="Product"
        )


class ProductStockChanged(DomainEvent):
    """Event published when product stock changes."""

    @classmethod
    def create(
        cls,
        product_id: str,
        old_stock: int,
        new_stock: int,
        change_reason: str
    ) -> "ProductStockChanged":
        """Create ProductStockChanged event."""
        return super().create(
            aggregate_id=product_id,
            aggregate_type="Product",
            old_stock=old_stock,
            new_stock=new_stock,
            change_reason=change_reason
        )


class ProductOutOfStock(DomainEvent):
    """Event published when a product goes out of stock."""

    @classmethod
    def create(cls, product_id: str) -> "ProductOutOfStock":
        """Create ProductOutOfStock event."""
        return super().create(
            aggregate_id=product_id,
            aggregate_type="Product"
        )