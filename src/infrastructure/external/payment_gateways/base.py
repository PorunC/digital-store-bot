"""Base payment gateway interface with bug fixes."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    """Payment method enumeration."""
    TELEGRAM_STARS = "telegram_stars"
    CRYPTOMUS = "cryptomus"


class PaymentData(BaseModel):
    """Payment data for creating payment."""
    
    order_id: str
    user_id: str
    product_id: str
    amount: float
    currency: str
    description: str
    user_telegram_id: int
    
    # Additional data
    webhook_url: Optional[str] = None
    return_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PaymentResult(BaseModel):
    """Payment creation result."""
    
    success: bool
    payment_id: Optional[str] = None
    payment_url: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WebhookData(BaseModel):
    """Webhook data for payment confirmation."""
    
    payment_id: str
    external_payment_id: Optional[str] = None
    status: PaymentStatus
    amount: Optional[float] = None
    currency: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PaymentGateway(ABC):
    """Base payment gateway interface."""

    def __init__(self, config: dict):
        self.config = config
        self.is_enabled = config.get("enabled", False)

    @property
    @abstractmethod
    def gateway_name(self) -> str:
        """Get gateway name."""
        pass

    @property
    @abstractmethod
    def payment_method(self) -> PaymentMethod:
        """Get payment method."""
        pass

    @abstractmethod
    async def create_payment(self, payment_data: PaymentData) -> PaymentResult:
        """Create a payment."""
        pass

    @abstractmethod
    async def get_payment_status(self, payment_id: str) -> PaymentStatus:
        """Get payment status."""
        pass

    @abstractmethod
    async def handle_webhook(self, webhook_data: dict) -> Optional[WebhookData]:
        """Handle webhook callback."""
        pass

    async def cancel_payment(self, payment_id: str) -> bool:
        """Cancel a payment (optional implementation)."""
        return False

    async def refund_payment(self, payment_id: str, amount: Optional[float] = None) -> bool:
        """Refund a payment (optional implementation)."""
        return False

    def validate_webhook_signature(self, data: dict, signature: str) -> bool:
        """Validate webhook signature (optional implementation)."""
        return True

    def is_available(self) -> bool:
        """Check if gateway is available."""
        return self.is_enabled

    def get_supported_currencies(self) -> list[str]:
        """Get supported currencies."""
        return ["USD", "EUR", "RUB"]

    def format_amount(self, amount: float, currency: str) -> str:
        """Format amount for display."""
        return f"{amount:.2f} {currency}"