"""Database manager for SQLAlchemy with optimized connection pool."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from src.infrastructure.configuration.settings import DatabaseConfig

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


class DatabaseManager:
    """Database manager for handling connections and sessions with optimized pool management."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    async def initialize(self) -> None:
        """Initialize database engine and session factory with optimized settings."""
        try:
            # 优化的引擎配置
            engine_kwargs = {
                "echo": self.config.echo,
            }
            
            # 对于小型应用，使用NullPool避免连接池问题
            if self.config.pool_size <= 1 or "sqlite" in self.config.get_url():
                engine_kwargs["poolclass"] = NullPool
                logger.info("Using NullPool for SQLite or single connection setup")
            else:
                # Only add pool parameters for non-SQLite databases
                engine_kwargs.update({
                    "pool_size": max(self.config.pool_size, 5),  # 最小5个连接
                    "max_overflow": max(self.config.max_overflow, 10),  # 最大额外10个连接
                    "pool_timeout": 30,  # 连接池超时30秒
                    "pool_recycle": 3600,  # 连接回收时间1小时
                    "pool_pre_ping": True,  # 连接前ping检查
                })
            
            self._engine = create_async_engine(
                self.config.get_url(),
                **engine_kwargs
            )
            
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False
            )
            
            logger.info("Database initialized successfully with optimized connection pool")
            
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

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session with proper context management."""
        if self._session_factory is None:
            raise RuntimeError("Database not initialized")
        
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    def get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get the session factory for dependency injection."""
        if self._session_factory is None:
            raise RuntimeError("Database not initialized")
        return self._session_factory
    
    def create_session(self) -> AsyncSession:
        """Create a new database session (for backward compatibility)."""
        if self._session_factory is None:
            raise RuntimeError("Database not initialized")
        return self._session_factory()

    async def close(self) -> None:
        """Close database connections properly."""
        if self._engine:
            # 等待所有连接完成
            await asyncio.sleep(0.1)
            await self._engine.dispose()
            logger.info("Database connections closed properly")

    async def health_check(self) -> bool:
        """Check database connectivity."""
        if not self._engine:
            return False
        
        try:
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    @property
    def engine(self) -> Optional[AsyncEngine]:
        """Get the database engine."""
        return self._engine

    @property
    def session_factory(self) -> Optional[async_sessionmaker[AsyncSession]]:
        """Get the session factory."""
        return self._session_factory