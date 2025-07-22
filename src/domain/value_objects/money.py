"""Money value object."""

from decimal import Decimal
from typing import Union

from pydantic import BaseModel, Field, validator


class Money(BaseModel):
    """Money value object."""

    amount: Decimal = Field(..., decimal_places=2)
    currency: str = Field(..., min_length=3, max_length=3)

    class Config:
        """Pydantic configuration."""
        frozen = True

    @validator("amount")
    def validate_amount(cls, v):
        """Validate amount."""
        if v < 0:
            raise ValueError("Amount cannot be negative")
        return v

    @validator("currency")
    def validate_currency(cls, v):
        """Validate currency code."""
        if not v.isupper():
            v = v.upper()
        if len(v) != 3:
            raise ValueError("Currency code must be 3 characters")
        return v

    def __add__(self, other: "Money") -> "Money":
        """Add two money objects."""
        if not isinstance(other, Money):
            raise TypeError("Can only add Money to Money")
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: "Money") -> "Money":
        """Subtract two money objects."""
        if not isinstance(other, Money):
            raise TypeError("Can only subtract Money from Money")
        if self.currency != other.currency:
            raise ValueError("Cannot subtract different currencies")
        result_amount = self.amount - other.amount
        if result_amount < 0:
            raise ValueError("Result cannot be negative")
        return Money(amount=result_amount, currency=self.currency)

    def __mul__(self, multiplier: Union[int, float, Decimal]) -> "Money":
        """Multiply money by a number."""
        if not isinstance(multiplier, (int, float, Decimal)):
            raise TypeError("Can only multiply Money by numbers")
        result_amount = self.amount * Decimal(str(multiplier))
        if result_amount < 0:
            raise ValueError("Result cannot be negative")
        return Money(amount=result_amount, currency=self.currency)

    def __eq__(self, other: object) -> bool:
        """Check equality."""
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency

    def __lt__(self, other: "Money") -> bool:
        """Less than comparison."""
        if not isinstance(other, Money):
            raise TypeError("Can only compare Money to Money")
        if self.currency != other.currency:
            raise ValueError("Cannot compare different currencies")
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        """Less than or equal comparison."""
        return self < other or self == other

    def __gt__(self, other: "Money") -> bool:
        """Greater than comparison."""
        return not self <= other

    def __ge__(self, other: "Money") -> bool:
        """Greater than or equal comparison."""
        return not self < other

    @property
    def is_zero(self) -> bool:
        """Check if amount is zero."""
        return self.amount == 0

    def to_string(self, symbol: str = None) -> str:
        """Convert to string representation."""
        if symbol:
            return f"{symbol}{self.amount:.2f}"
        return f"{self.amount:.2f} {self.currency}"

    @classmethod
    def zero(cls, currency: str) -> "Money":
        """Create zero money."""
        return cls(amount=Decimal("0"), currency=currency)

    @classmethod
    def from_float(cls, amount: float, currency: str) -> "Money":
        """Create money from float."""
        return cls(amount=Decimal(str(amount)), currency=currency)