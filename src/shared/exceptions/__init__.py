"""Shared exceptions for the Digital Store Bot v2."""

from .example_custom_exception import (
    BusinessLogicError,
    InsufficientFundsError,
    ProductNotAvailableError,
    PaymentProcessingError
)

__all__ = [
    "BusinessLogicError",
    "InsufficientFundsError", 
    "ProductNotAvailableError",
    "PaymentProcessingError"
]