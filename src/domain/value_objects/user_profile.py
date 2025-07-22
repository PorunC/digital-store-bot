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

    @validator("first_name")
    def validate_first_name(cls, v):
        """Validate first name."""
        if not v or not v.strip():
            raise ValueError("First name cannot be empty")
        return v.strip()

    @validator("username")
    def validate_username(cls, v):
        """Validate username."""
        if v is not None:
            v = v.strip()
            if not v:
                return None
            if not v.isalnum() and "_" not in v:
                raise ValueError("Username can only contain letters, numbers, and underscores")
        return v

    @property
    def display_name(self) -> str:
        """Get display name for the user."""
        if self.username:
            return f"{self.first_name} (@{self.username})"
        return self.first_name