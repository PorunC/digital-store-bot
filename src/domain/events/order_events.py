"""Order domain events."""

from typing import Optional

from .base import DomainEvent


class OrderCreated(DomainEvent):
    """Event published when an order is created."""

    @classmethod
    def create(
        cls,
        order_id: str,
        user_id: str,
        product_id: str,
        amount: float,
        currency: str,
        is_trial: bool = False
    ) -> "OrderCreated":
        """Create OrderCreated event."""
        return super().create(
            aggregate_id=order_id,
            aggregate_type="Order",
            user_id=user_id,
            product_id=product_id,
            amount=amount,
            currency=currency,
            is_trial=is_trial
        )


class PaymentReceived(DomainEvent):
    """Event published when payment is received for an order."""

    @classmethod
    def create(
        cls,
        order_id: str,
        user_id: str,
        payment_id: Optional[str],
        amount: float,
        currency: str
    ) -> "PaymentReceived":
        """Create PaymentReceived event."""
        return super().create(
            aggregate_id=order_id,
            aggregate_type="Order",
            user_id=user_id,
            payment_id=payment_id,
            amount=amount,
            currency=currency
        )


class OrderCompleted(DomainEvent):
    """Event published when an order is completed."""

    @classmethod
    def create(
        cls,
        order_id: str,
        user_id: str,
        product_id: str,
        delivery_info: Optional[str] = None
    ) -> "OrderCompleted":
        """Create OrderCompleted event."""
        return super().create(
            aggregate_id=order_id,
            aggregate_type="Order",
            user_id=user_id,
            product_id=product_id,
            delivery_info=delivery_info
        )


class OrderCancelled(DomainEvent):
    """Event published when an order is cancelled."""

    @classmethod
    def create(
        cls,
        order_id: str,
        user_id: str,
        reason: Optional[str] = None
    ) -> "OrderCancelled":
        """Create OrderCancelled event."""
        return super().create(
            aggregate_id=order_id,
            aggregate_type="Order",
            user_id=user_id,
            reason=reason
        )


class OrderRefunded(DomainEvent):
    """Event published when an order is refunded."""

    @classmethod
    def create(
        cls,
        order_id: str,
        user_id: str,
        amount: float,
        currency: str,
        reason: Optional[str] = None
    ) -> "OrderRefunded":
        """Create OrderRefunded event."""
        return super().create(
            aggregate_id=order_id,
            aggregate_type="Order",
            user_id=user_id,
            amount=amount,
            currency=currency,
            reason=reason
        )


class OrderExpired(DomainEvent):
    """Event published when an order expires."""

    @classmethod
    def create(cls, order_id: str, user_id: str) -> "OrderExpired":
        """Create OrderExpired event."""
        return super().create(
            aggregate_id=order_id,
            aggregate_type="Order",
            user_id=user_id
        )