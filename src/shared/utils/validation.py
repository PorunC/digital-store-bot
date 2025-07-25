"""Validation utilities for consistent data validation."""

import re
from typing import Optional


class ValidationError(ValueError):
    """Custom validation error."""
    pass


class DataValidator:
    """Centralized data validation utilities."""
    
    @staticmethod
    def sanitize_name(name: str, max_length: int = 64) -> str:
        """Sanitize name input to prevent validation errors."""
        if not name:
            return "User"
        
        name = name.strip()
        if len(name) > max_length:
            name = name[:max_length - 3] + "..."
        
        return name
    
    @staticmethod
    def sanitize_username(username: Optional[str], max_length: int = 32) -> Optional[str]:
        """Sanitize username input to prevent validation errors."""
        if not username:
            return None
        
        username = username.strip()
        if not username:
            return None
        
        if len(username) > max_length:
            username = username[:max_length - 3] + "..."
        
        return username
    
    @staticmethod
    def sanitize_language_code(language_code: str) -> str:
        """Sanitize language code input."""
        if not language_code or len(language_code) < 2:
            return "en"
        return language_code[:5].lower()
    
    @staticmethod
    def validate_telegram_id(telegram_id: int) -> int:
        """Validate Telegram ID."""
        if telegram_id <= 0:
            raise ValidationError("Telegram ID must be positive")
        return telegram_id
    
    @staticmethod
    def validate_amount(amount: float) -> float:
        """Validate monetary amount."""
        if amount < 0:
            raise ValidationError("Amount cannot be negative")
        return round(amount, 2)
    
    @staticmethod
    def validate_quantity(quantity: int) -> int:
        """Validate quantity."""
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")
        return quantity
    
    @staticmethod
    def validate_email(email: str) -> str:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValidationError("Invalid email format")
        return email.lower()
    
    @staticmethod
    def validate_password(password: str, min_length: int = 8) -> str:
        """Validate password strength."""
        if len(password) < min_length:
            raise ValidationError(f"Password must be at least {min_length} characters long")
        
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            raise ValidationError("Password must contain at least one lowercase letter")
        
        if not re.search(r'[0-9]', password):
            raise ValidationError("Password must contain at least one digit")
        
        return password