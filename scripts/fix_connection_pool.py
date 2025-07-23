#!/usr/bin/env python3
"""
SQLAlchemy连接池优化脚本
修复连接池管理问题，防止连接泄漏
"""

import asyncio
import logging
from pathlib import Path
import sys

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)


class ConnectionPoolOptimizer:
    """连接池优化器"""
    
    @staticmethod
    def create_optimized_database_manager():
        """创建优化的数据库管理器代码"""
        
        optimized_code = '''"""Database manager for SQLAlchemy with optimized connection pool."""

from __future__ import annotations

import logging
from typing import Optional, AsyncContextManager
from contextlib import asynccontextmanager
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
                "pool_size": max(self.config.pool_size, 5),  # 最小5个连接
                "max_overflow": max(self.config.max_overflow, 10),  # 最大额外10个连接
                "pool_timeout": 30,  # 连接池超时30秒
                "pool_recycle": 3600,  # 连接回收时间1小时
                "pool_pre_ping": True,  # 连接前ping检查
            }
            
            # 对于小型应用，使用NullPool避免连接池问题
            if self.config.pool_size <= 1:
                engine_kwargs["poolclass"] = NullPool
                logger.info("Using NullPool for single connection setup")
            
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
    async def get_session(self) -> AsyncContextManager[AsyncSession]:
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
                await session.execute("SELECT 1")
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
'''
        
        return optimized_code
    
    @staticmethod
    def create_session_dependency():
        """创建优化的会话依赖注入代码"""
        
        dependency_code = '''"""Database session dependency for dependency injection."""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.dependency_injection import container


async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with proper lifecycle management."""
    database_manager = container.get("DatabaseManager")
    
    async with database_manager.get_session() as session:
        yield session
'''
        
        return dependency_code
    
    async def apply_optimizations(self):
        """应用连接池优化"""
        print("🔧 开始应用SQLAlchemy连接池优化...")
        
        # 1. 备份原始文件
        manager_file = project_root / "src/infrastructure/database/manager.py"
        backup_file = project_root / "src/infrastructure/database/manager.py.backup"
        
        if manager_file.exists():
            import shutil
            shutil.copy2(manager_file, backup_file)
            print(f"✅ 已备份原始文件到: {backup_file}")
        
        # 2. 写入优化的代码
        optimized_code = self.create_optimized_database_manager()
        with open(manager_file, 'w', encoding='utf-8') as f:
            f.write(optimized_code)
        print("✅ 已更新数据库管理器代码")
        
        # 3. 创建会话依赖文件
        dependency_file = project_root / "src/infrastructure/database/dependencies.py"
        dependency_code = self.create_session_dependency()
        with open(dependency_file, 'w', encoding='utf-8') as f:
            f.write(dependency_code)
        print("✅ 已创建会话依赖文件")
        
        print("\n📋 优化内容:")
        print("  ✅ 添加连接池超时和回收机制")
        print("  ✅ 启用连接前ping检查")
        print("  ✅ 优化会话上下文管理")
        print("  ✅ 添加数据库健康检查")
        print("  ✅ 改进连接关闭流程")
        
        print("\n💡 建议:")
        print("  1. 重启应用以应用优化")
        print("  2. 监控日志确认连接池错误消失")
        print("  3. 如有问题可恢复备份文件")


async def main():
    """主函数"""
    print("🔍 SQLAlchemy连接池优化工具")
    print("=" * 40)
    
    optimizer = ConnectionPoolOptimizer()
    
    try:
        await optimizer.apply_optimizations()
        print("\n🎉 连接池优化完成！")
        return 0
    except Exception as e:
        print(f"\n❌ 优化失败: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)