"""Base entity and aggregate root classes."""

from abc import ABC
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from ..events.base import DomainEvent


class Entity(BaseModel, ABC):
    """Base class for all entities."""

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    version: int = Field(default=1)

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        validate_assignment = True

    def __eq__(self, other: object) -> bool:
        """Check equality based on ID."""
        if not isinstance(other, Entity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self.id)

    def mark_updated(self) -> None:
        """Mark entity as updated."""
        self.updated_at = datetime.utcnow()
        self.version += 1


class AggregateRoot(Entity, ABC):
    """Base class for aggregate roots that can publish domain events."""

    def __init__(self, **data):
        super().__init__(**data)
        self._domain_events: List[DomainEvent] = []

    def add_domain_event(self, event: DomainEvent) -> None:
        """Add a domain event to be published."""
        self._domain_events.append(event)

    def get_domain_events(self) -> List[DomainEvent]:
        """Get all domain events."""
        return self._domain_events.copy()

    def clear_domain_events(self) -> None:
        """Clear all domain events."""
        self._domain_events.clear()

    def has_domain_events(self) -> bool:
        """Check if there are any domain events."""
        return len(self._domain_events) > 0