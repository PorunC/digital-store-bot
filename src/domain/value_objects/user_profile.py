"""User profile value object."""

from typing import Optional

from pydantic import BaseModel, Field, validator


class UserProfile(BaseModel):
    """User profile value object."""

    first_name: str = Field(..., min_length=1, max_length=64)
    username: Optional[str] = Field(None, max_length=32)

    class Config:
        """Pydantic configuration."""
        frozen = True

    @validator("first_name", pre=True)
    def validate_first_name(cls, v):
        """Validate first name."""
        if not v or not v.strip():
            raise ValueError("First name cannot be empty")
        # Truncate if too long to prevent validation errors
        v = v.strip()
        if len(v) > 64:
            v = v[:61] + "..."
        return v

    @validator("username", pre=True)
    def validate_username(cls, v):
        """Validate username."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            # Truncate if too long to prevent validation errors
            if len(v) > 32:
                v = v[:29] + "..."
            # Accept all valid Telegram usernames (letters, numbers, underscores)
        return v

    @property
    def display_name(self) -> str:
        """Get display name for the user."""
        if self.username:
            return f"{self.first_name} (@{self.username})"
        return self.first_name