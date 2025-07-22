"""Base repository and unit of work interfaces."""

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

from ..entities.base import Entity

T = TypeVar("T", bound=Entity)


class Repository(Generic[T], ABC):
    """Base repository interface."""

    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def get_all(self) -> List[T]:
        """Get all entities."""
        pass

    @abstractmethod
    async def add(self, entity: T) -> T:
        """Add a new entity."""
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Delete an entity by ID."""
        pass

    @abstractmethod
    async def exists(self, entity_id: str) -> bool:
        """Check if entity exists."""
        pass


class UnitOfWork(ABC):
    """Unit of work interface for managing transactions."""

    @abstractmethod
    async def __aenter__(self):
        """Enter async context manager."""
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        pass

    @abstractmethod
    async def commit(self) -> None:
        """Commit the transaction."""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the transaction."""
        pass

    @abstractmethod
    def get_repository(self, repository_type: type) -> Repository:
        """Get a repository of the specified type."""
        pass