"""Base classes for domain events."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    """Base class for all domain events."""

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
        aggregate_type: str,
        event_type: str,
        data: Dict[str, Any] = None,
    ) -> "DomainEvent":
        """Create a new domain event."""
        return cls(
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            event_type=event_type,
            data=data or {},
        )


class EventHandler(Protocol):
    """Protocol for event handlers."""

    async def handle(self, event: DomainEvent) -> None:
        """Handle a domain event."""
        ...


class IntegrationEvent(BaseModel):
    """Base class for integration events (between bounded contexts)."""

    event_id: UUID = Field(default_factory=uuid4)
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    source_service: str
    event_type: str
    data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""
        frozen = True