"""Base migration class for database schema changes."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession


class BaseMigration(ABC):
    """Base class for database migrations."""
    
    def __init__(self):
        self.id = self._get_migration_id()
        self.description = self._get_description()
        self.version = self._get_version()
        self.created_at = datetime.utcnow()
    
    @abstractmethod
    def _get_migration_id(self) -> str:
        """Get unique migration identifier."""
        pass
    
    @abstractmethod
    def _get_description(self) -> str:
        """Get migration description."""
        pass
    
    @abstractmethod 
    def _get_version(self) -> str:
        """Get migration version."""
        pass
    
    @abstractmethod
    async def up(self, session: AsyncSession) -> None:
        """Apply the migration (upgrade)."""
        pass
    
    @abstractmethod
    async def down(self, session: AsyncSession) -> None:
        """Reverse the migration (downgrade)."""
        pass
    
    async def validate(self, session: AsyncSession) -> bool:
        """Validate that migration was applied correctly."""
        return True
    
    def get_dependencies(self) -> List[str]:
        """Get list of migration IDs this migration depends on."""
        return []
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get additional migration metadata."""
        return {
            "id": self.id,
            "description": self.description,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "dependencies": self.get_dependencies()
        }
    
    def __str__(self) -> str:
        return f"Migration {self.id}: {self.description}"
    
    def __repr__(self) -> str:
        return f"<Migration(id='{self.id}', version='{self.version}')>"