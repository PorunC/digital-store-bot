"""Example custom exception classes for the Digital Store Bot v2.

This module demonstrates how to create custom exception classes for specific
business logic errors and system failures.
"""

from typing import Optional, Dict, Any


class BusinessLogicError(Exception):
    """Base class for business logic errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(self.message)


class InsufficientFundsError(BusinessLogicError):
    """Raised when user doesn't have enough funds for a purchase."""
    
    def __init__(
        self,
        required_amount: float,
        available_amount: float,
        currency: str = "USD"
    ):
        message = f"Insufficient funds. Required: {required_amount} {currency}, Available: {available_amount} {currency}"
        context = {
            "required_amount": required_amount,
            "available_amount": available_amount,
            "currency": currency
        }
        super().__init__(message, "INSUFFICIENT_FUNDS", context)


class ProductNotAvailableError(BusinessLogicError):
    """Raised when a product is not available for purchase."""
    
    def __init__(self, product_id: str, reason: str = "Product unavailable"):
        message = f"Product {product_id} is not available: {reason}"
        context = {"product_id": product_id, "reason": reason}
        super().__init__(message, "PRODUCT_NOT_AVAILABLE", context)


class PaymentProcessingError(BusinessLogicError):
    """Raised when payment processing fails."""
    
    def __init__(
        self,
        payment_id: str,
        gateway: str,
        reason: str = "Payment processing failed"
    ):
        message = f"Payment {payment_id} failed on {gateway}: {reason}"
        context = {
            "payment_id": payment_id,
            "gateway": gateway,
            "reason": reason
        }
        super().__init__(message, "PAYMENT_PROCESSING_ERROR", context)


# Usage Example:
"""
try:
    # Business logic that might fail
    process_payment(order)
except InsufficientFundsError as e:
    logger.error(f"Payment failed: {e.message}", extra=e.context)
    # Handle insufficient funds scenario
except PaymentProcessingError as e:
    logger.error(f"Payment processing error: {e.message}", extra=e.context)
    # Handle payment gateway errors
"""