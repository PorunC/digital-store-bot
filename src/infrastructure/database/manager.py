"""Database manager for SQLAlchemy."""

from __future__ import annotations

import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.infrastructure.configuration.settings import DatabaseConfig

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


class DatabaseManager:
    """Database manager for handling connections and sessions."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    async def initialize(self) -> None:
        """Initialize database engine and session factory."""
        try:
            self._engine = create_async_engine(
                self.config.get_url(),
                echo=self.config.echo,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
            )
            
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def create_tables(self) -> None:
        """Create all database tables."""
        if self._engine is None:
            raise RuntimeError("Database not initialized")
        
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created")

    async def drop_tables(self) -> None:
        """Drop all database tables."""
        if self._engine is None:
            raise RuntimeError("Database not initialized")
        
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.info("Database tables dropped")

    def get_session(self) -> AsyncSession:
        """Get a new database session."""
        if self._session_factory is None:
            raise RuntimeError("Database not initialized")
        
        return self._session_factory()

    async def close(self) -> None:
        """Close database connections."""
        if self._engine:
            await self._engine.dispose()
            logger.info("Database connections closed")

    @property
    def engine(self) -> Optional[AsyncEngine]:
        """Get the database engine."""
        return self._engine

    @property
    def session_factory(self) -> Optional[async_sessionmaker[AsyncSession]]:
        """Get the session factory."""
        return self._session_factory