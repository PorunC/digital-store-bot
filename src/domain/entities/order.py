"""Order domain entity with complete transaction support."""

from datetime import datetime
from enum import Enum
from typing import Optional, UUID

from pydantic import Field

from ..events.order_events import (
    OrderCreated,
    OrderCompleted,
    OrderCancelled,
    OrderRefunded,
    PaymentReceived
)
from ..value_objects.money import Money
from .base import AggregateRoot


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "pending"
    PAID = "paid"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    FAILED = "failed"


class PaymentMethod(str, Enum):
    """Payment method enumeration."""
    TELEGRAM_STARS = "telegram_stars"
    CRYPTOMUS = "cryptomus"
    MANUAL = "manual"


class Order(AggregateRoot):
    """Order aggregate root."""

    user_id: UUID
    product_id: UUID
    payment_id: Optional[str] = None
    external_payment_id: Optional[str] = None
    
    # Order details
    product_name: str
    product_description: str
    amount: Money
    quantity: int = Field(default=1, gt=0)
    
    # Payment details
    payment_method: Optional[PaymentMethod] = None
    payment_gateway: Optional[str] = None
    payment_url: Optional[str] = None
    
    # Status tracking
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    
    # Timestamps
    expires_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    # Additional data
    notes: Optional[str] = None
    referrer_id: Optional[UUID] = None
    promocode: Optional[str] = None
    is_trial: bool = Field(default=False)
    is_extend: bool = Field(default=False)

    @classmethod
    def create(
        cls,
        user_id: UUID,
        product_id: UUID,
        product_name: str,
        product_description: str,
        amount: Money,
        quantity: int = 1,
        referrer_id: Optional[UUID] = None,
        promocode: Optional[str] = None,
        is_trial: bool = False,
        is_extend: bool = False,
        expires_at: Optional[datetime] = None,
    ) -> "Order":
        """Create a new order."""
        order = cls(
            user_id=user_id,
            product_id=product_id,
            product_name=product_name,
            product_description=product_description,
            amount=amount,
            quantity=quantity,
            referrer_id=referrer_id,
            promocode=promocode,
            is_trial=is_trial,
            is_extend=is_extend,
            expires_at=expires_at,
        )
        
        # Publish domain event
        event = OrderCreated.create(
            order_id=str(order.id),
            user_id=str(user_id),
            product_id=str(product_id),
            amount=float(amount.amount),
            currency=amount.currency,
            is_trial=is_trial
        )
        order.add_domain_event(event)
        
        return order

    def set_payment_details(
        self,
        payment_method: PaymentMethod,
        payment_gateway: str,
        payment_id: str,
        external_payment_id: Optional[str] = None,
        payment_url: Optional[str] = None,
    ) -> None:
        """Set payment details for the order."""
        if self.status != OrderStatus.PENDING:
            raise ValueError("Cannot set payment details for non-pending order")
            
        self.payment_method = payment_method
        self.payment_gateway = payment_gateway
        self.payment_id = payment_id
        self.external_payment_id = external_payment_id
        self.payment_url = payment_url
        
        self.mark_updated()

    def mark_as_paid(self, payment_id: Optional[str] = None) -> None:
        """Mark order as paid."""
        if self.status not in [OrderStatus.PENDING]:
            raise ValueError(f"Cannot mark order as paid from status: {self.status}")
            
        self.status = OrderStatus.PAID
        self.paid_at = datetime.utcnow()
        
        if payment_id:
            self.external_payment_id = payment_id
            
        self.mark_updated()
        
        # Publish domain event
        event = PaymentReceived.create(
            order_id=str(self.id),
            user_id=str(self.user_id),
            payment_id=payment_id or self.payment_id,
            amount=float(self.amount.amount),
            currency=self.amount.currency
        )
        self.add_domain_event(event)

    def complete(self, delivery_info: Optional[str] = None) -> None:
        """Complete the order (product delivered)."""
        if self.status != OrderStatus.PAID:
            raise ValueError("Cannot complete unpaid order")
            
        self.status = OrderStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        
        if delivery_info:
            self.notes = (self.notes or "") + f"\nDelivery: {delivery_info}"
            
        self.mark_updated()
        
        # Publish domain event
        event = OrderCompleted.create(
            order_id=str(self.id),
            user_id=str(self.user_id),
            product_id=str(self.product_id),
            delivery_info=delivery_info
        )
        self.add_domain_event(event)

    def cancel(self, reason: Optional[str] = None) -> None:
        """Cancel the order."""
        if self.status in [OrderStatus.COMPLETED, OrderStatus.REFUNDED]:
            raise ValueError(f"Cannot cancel order with status: {self.status}")
            
        self.status = OrderStatus.CANCELLED
        self.cancelled_at = datetime.utcnow()
        
        if reason:
            self.notes = (self.notes or "") + f"\nCancellation reason: {reason}"
            
        self.mark_updated()
        
        # Publish domain event
        event = OrderCancelled.create(
            order_id=str(self.id),
            user_id=str(self.user_id),
            reason=reason
        )
        self.add_domain_event(event)

    def refund(self, reason: Optional[str] = None) -> None:
        """Refund the order."""
        if self.status not in [OrderStatus.PAID, OrderStatus.COMPLETED]:
            raise ValueError(f"Cannot refund order with status: {self.status}")
            
        self.status = OrderStatus.REFUNDED
        
        if reason:
            self.notes = (self.notes or "") + f"\nRefund reason: {reason}"
            
        self.mark_updated()
        
        # Publish domain event
        event = OrderRefunded.create(
            order_id=str(self.id),
            user_id=str(self.user_id),
            amount=float(self.amount.amount),
            currency=self.amount.currency,
            reason=reason
        )
        self.add_domain_event(event)

    def fail(self, reason: Optional[str] = None) -> None:
        """Mark order as failed."""
        self.status = OrderStatus.FAILED
        
        if reason:
            self.notes = (self.notes or "") + f"\nFailure reason: {reason}"
            
        self.mark_updated()

    @property
    def is_expired(self) -> bool:
        """Check if order has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def can_be_paid(self) -> bool:
        """Check if order can be paid."""
        return (
            self.status == OrderStatus.PENDING and
            not self.is_expired
        )

    @property
    def can_be_cancelled(self) -> bool:
        """Check if order can be cancelled."""
        return self.status in [OrderStatus.PENDING, OrderStatus.PAID]

    @property
    def can_be_refunded(self) -> bool:
        """Check if order can be refunded."""
        return self.status in [OrderStatus.PAID, OrderStatus.COMPLETED]

    @property
    def total_amount(self) -> Money:
        """Get total order amount."""
        total = self.amount * self.quantity
        return total

    def add_note(self, note: str) -> None:
        """Add a note to the order."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        new_note = f"[{timestamp}] {note}"
        
        if self.notes:
            self.notes += f"\n{new_note}"
        else:
            self.notes = new_note
            
        self.mark_updated()