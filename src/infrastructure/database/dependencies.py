"""Database session dependency for dependency injection."""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.dependency_injection import container


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with proper lifecycle management."""
    database_manager = container.get("DatabaseManager")
    
    async with database_manager.get_session() as session:
        yield session


async def get_session_factory():
    """Get session factory for manual session management."""
    database_manager = container.get("DatabaseManager")
    return database_manager.get_session_factory()