"""Payment domain events."""

from typing import Optional

from .base import DomainEvent


class PaymentProcessedEvent(DomainEvent):
    """Event published when a payment is successfully processed."""

    @classmethod
    def create(
        cls,
        payment_id: str,
        order_id: str,
        user_id: str,
        amount: float,
        currency: str,
        payment_method: str,
        external_payment_id: Optional[str] = None
    ) -> "PaymentProcessedEvent":
        """Create PaymentProcessedEvent."""
        return super().create(
            aggregate_id=payment_id,
            aggregate_type="Payment",
            order_id=order_id,
            user_id=user_id,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            external_payment_id=external_payment_id
        )


class PaymentFailedEvent(DomainEvent):
    """Event published when a payment fails."""

    @classmethod
    def create(
        cls,
        payment_id: str,
        order_id: str,
        user_id: str,
        amount: float,
        currency: str,
        payment_method: str,
        failure_reason: str,
        external_payment_id: Optional[str] = None
    ) -> "PaymentFailedEvent":
        """Create PaymentFailedEvent."""
        return super().create(
            aggregate_id=payment_id,
            aggregate_type="Payment",
            order_id=order_id,
            user_id=user_id,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            failure_reason=failure_reason,
            external_payment_id=external_payment_id
        )


class PaymentRefundedEvent(DomainEvent):
    """Event published when a payment is refunded."""

    @classmethod
    def create(
        cls,
        payment_id: str,
        order_id: str,
        user_id: str,
        refund_amount: float,
        currency: str,
        refund_reason: str,
        external_refund_id: Optional[str] = None
    ) -> "PaymentRefundedEvent":
        """Create PaymentRefundedEvent."""
        return super().create(
            aggregate_id=payment_id,
            aggregate_type="Payment",
            order_id=order_id,
            user_id=user_id,
            refund_amount=refund_amount,
            currency=currency,
            refund_reason=refund_reason,
            external_refund_id=external_refund_id
        )