"""Database session dependency for dependency injection."""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from dependency_injector.wiring import inject, Provide
from src.core.containers import ApplicationContainer


@inject
async def get_database_session(
    database_manager = Provide[ApplicationContainer.database_manager]
) -> AsyncGenerator[AsyncSession, None]:
    """Get database session with proper lifecycle management."""
    
    async with database_manager.get_session() as session:
        yield session


@inject
async def get_session_factory(
    database_manager = Provide[ApplicationContainer.database_manager]
):
    """Get session factory for manual session management."""
    return database_manager.get_session_factory()