"""SQLAlchemy Unit of Work implementation."""

from typing import Any, Optional, Type, Union

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.domain.repositories.base import Repository, UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    """SQLAlchemy implementation of Unit of Work pattern."""

    def __init__(self, session_or_factory: Union[AsyncSession, async_sessionmaker]):
        """Initialize with SQLAlchemy session or session factory."""
        if isinstance(session_or_factory, async_sessionmaker):
            self._session_factory = session_or_factory
            self.session = None
        else:
            self._session_factory = None
            self.session = session_or_factory
        self._repositories = {}
        self._transaction = None
        self._owns_session = False

    async def __aenter__(self):
        """Enter async context manager and start transaction."""
        # Create session if we have a factory
        if self.session is None and self._session_factory:
            self.session = self._session_factory()
            self._owns_session = True
        
        if self._transaction is None and self.session:
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
                
        # Close session if we own it
        if self._owns_session and self.session:
            await self.session.close()
            self.session = None
            self._owns_session = False

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