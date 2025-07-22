"""Base domain event class."""

from datetime import datetime
from typing import Any, Dict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """Base class for domain events."""

    event_id: UUID = Field(default_factory=uuid4)
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    event_version: int = Field(default=1)
    aggregate_id: str
    aggregate_type: str
    event_type: str
    data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""
        frozen = True
        use_enum_values = True

    @classmethod
    def create(
        cls,
        aggregate_id: str,
        aggregate_type: str = None,
        event_type: str = None,
        **kwargs
    ) -> "DomainEvent":
        """Create a new domain event."""
        if aggregate_type is None:
            aggregate_type = cls.__module__.split('.')[-2]  # Extract from module path
        if event_type is None:
            event_type = cls.__name__
            
        return cls(
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            event_type=event_type,
            data=kwargs
        )