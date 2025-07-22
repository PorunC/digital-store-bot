"""SQLAlchemy Unit of Work implementation."""

from typing import Any, Optional, Type

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.repositories.base import Repository, UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    """SQLAlchemy implementation of Unit of Work pattern."""

    def __init__(self, session: AsyncSession):
        """Initialize with SQLAlchemy session."""
        self.session = session
        self._repositories = {}
        self._transaction = None

    async def __aenter__(self):
        """Enter async context manager and start transaction."""
        if self._transaction is None:
            self._transaction = self.session.begin()
            await self._transaction.__aenter__()
        return self

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[Any]):
        """Exit async context manager and handle transaction."""
        if self._transaction:
            try:
                if exc_type is not None:
                    # Exception occurred, rollback
                    await self._transaction.__aexit__(exc_type, exc_val, exc_tb)
                else:
                    # No exception, commit
                    await self._transaction.__aexit__(None, None, None)
            finally:
                self._transaction = None

    async def commit(self) -> None:
        """Commit the current transaction."""
        if self._transaction:
            await self.session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        if self._transaction:
            await self.session.rollback()

    def get_repository(self, repository_type: type) -> Repository:
        """Get a repository instance of the specified type."""
        if repository_type not in self._repositories:
            # This would typically create the repository with the current session
            # For now, we'll raise an error indicating the repository needs to be registered
            raise ValueError(f"Repository {repository_type.__name__} not registered in Unit of Work")
        
        return self._repositories[repository_type]

    def register_repository(self, repository_type: type, repository_instance: Repository) -> None:
        """Register a repository instance."""
        self._repositories[repository_type] = repository_instance

    async def flush(self) -> None:
        """Flush pending changes to the database."""
        await self.session.flush()

    async def refresh(self, entity: Any) -> None:
        """Refresh an entity from the database."""
        await self.session.refresh(entity)

    @property
    def is_active(self) -> bool:
        """Check if transaction is active."""
        return self._transaction is not None