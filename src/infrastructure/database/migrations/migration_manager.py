"""Migration manager for database schema evolution."""

from __future__ import annotations

import logging
import importlib
import importlib.util
import inspect
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Type

from sqlalchemy import text, Table, Column, String, DateTime, Boolean, MetaData
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.exc import SQLAlchemyError

from .base_migration import BaseMigration

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages database migrations for schema evolution."""
    
    def __init__(self, database_url: str, migrations_path: str = "migrations"):
        self.database_url = database_url
        self.migrations_path = Path(migrations_path)
        self.engine: AsyncEngine = create_async_engine(database_url)
        
        # Migration tracking table
        self.migration_table = Table(
            'schema_migrations',
            MetaData(),
            Column('id', String(255), primary_key=True),
            Column('version', String(50), nullable=False),
            Column('description', String(500), nullable=False),
            Column('applied_at', DateTime, nullable=False),
            Column('execution_time_ms', String(20)),
            Column('success', Boolean, default=True),
            Column('error_message', String(1000), nullable=True)
        )
    
    async def initialize(self) -> None:
        """Initialize migration system and create tracking table."""
        try:
            async with self.engine.begin() as conn:
                # Create migrations tracking table if it doesn't exist
                await conn.run_sync(self.migration_table.create, checkfirst=True)
            
            logger.info("Migration system initialized")
            
        except Exception as e:
            # Handle race condition where table might already exist
            error_msg = str(e).lower()
            if "already exists" in error_msg or "duplicate key" in error_msg or "unique constraint" in error_msg:
                logger.info("Migration table already exists, continuing...")
            else:
                logger.error(f"Failed to initialize migration system: {e}")
                raise
    
    async def discover_migrations(self) -> List[BaseMigration]:
        """Discover all migration files and load them."""
        migrations = []
        
        try:
            if not self.migrations_path.exists():
                logger.warning(f"Migrations directory not found: {self.migrations_path}")
                return migrations
            
            # Find all Python files in migrations directory
            for migration_file in self.migrations_path.glob("*.py"):
                if migration_file.name.startswith("__"):
                    continue
                
                try:
                    # Import the migration module
                    module_name = f"src.infrastructure.database.migrations.{migration_file.stem}"
                    spec = importlib.util.spec_from_file_location(module_name, migration_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find migration classes
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, BaseMigration) and 
                            obj != BaseMigration):
                            
                            migration = obj()
                            migrations.append(migration)
                            logger.debug(f"Discovered migration: {migration.id}")
                
                except Exception as e:
                    logger.error(f"Error loading migration file {migration_file}: {e}")
            
            # Sort migrations by version/ID
            migrations.sort(key=lambda m: (m.version, m.id))
            
            logger.info(f"Discovered {len(migrations)} migrations")
            return migrations
            
        except Exception as e:
            logger.error(f"Error discovering migrations: {e}")
            return []
    
    async def get_applied_migrations(self) -> List[Dict[str, Any]]:
        """Get list of already applied migrations."""
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(
                    text("SELECT * FROM schema_migrations ORDER BY applied_at")
                )
                return [dict(row._mapping) for row in result.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting applied migrations: {e}")
            return []
    
    async def get_pending_migrations(self) -> List[BaseMigration]:
        """Get list of migrations that need to be applied."""
        all_migrations = await self.discover_migrations()
        applied_migrations = await self.get_applied_migrations()
        applied_ids = {m['id'] for m in applied_migrations}
        
        pending = [m for m in all_migrations if m.id not in applied_ids]
        
        # Validate dependencies
        pending = self._resolve_dependencies(pending, applied_ids)
        
        logger.info(f"Found {len(pending)} pending migrations")
        return pending
    
    def _resolve_dependencies(
        self, 
        migrations: List[BaseMigration], 
        applied_ids: set
    ) -> List[BaseMigration]:
        """Resolve migration dependencies and return ordered list."""
        resolved = []
        remaining = migrations.copy()
        
        while remaining:
            made_progress = False
            
            for migration in remaining[:]:
                dependencies = migration.get_dependencies()
                
                # Check if all dependencies are satisfied
                if all(dep_id in applied_ids or 
                      any(r.id == dep_id for r in resolved) 
                      for dep_id in dependencies):
                    
                    resolved.append(migration)
                    remaining.remove(migration)
                    made_progress = True
            
            if not made_progress and remaining:
                # Circular dependency or missing dependency
                missing_deps = []
                for migration in remaining:
                    for dep_id in migration.get_dependencies():
                        if (dep_id not in applied_ids and 
                            not any(r.id == dep_id for r in resolved)):
                            missing_deps.append(f"{migration.id} -> {dep_id}")
                
                raise ValueError(f"Unresolved dependencies: {missing_deps}")
        
        return resolved
    
    async def apply_migrations(
        self, 
        migrations: Optional[List[BaseMigration]] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Apply pending migrations."""
        if migrations is None:
            migrations = await self.get_pending_migrations()
        
        if not migrations:
            logger.info("No pending migrations to apply")
            return {"applied": 0, "skipped": 0, "errors": 0}
        
        applied = 0
        skipped = 0
        errors = 0
        results = []
        
        for migration in migrations:
            try:
                logger.info(f"Applying migration: {migration}")
                
                if dry_run:
                    logger.info(f"[DRY RUN] Would apply: {migration}")
                    results.append({
                        "migration": migration.id,
                        "status": "dry_run",
                        "description": migration.description
                    })
                    continue
                
                start_time = datetime.utcnow()
                
                async with self.engine.begin() as conn:
                    session = AsyncSession(bind=conn)
                    
                    try:
                        # Apply the migration
                        await migration.up(session)
                        
                        # Validate the migration
                        if not await migration.validate(session):
                            raise ValueError("Migration validation failed")
                        
                        # Record successful migration
                        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                        
                        await conn.execute(
                            self.migration_table.insert().values(
                                id=migration.id,
                                version=migration.version,
                                description=migration.description,
                                applied_at=start_time,
                                execution_time_ms=str(int(execution_time)),
                                success=True
                            )
                        )
                        
                        applied += 1
                        results.append({
                            "migration": migration.id,
                            "status": "applied",
                            "execution_time_ms": int(execution_time),
                            "description": migration.description
                        })
                        
                        logger.info(f"Successfully applied migration: {migration.id}")
                        
                    except Exception as e:
                        # Record failed migration
                        execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                        
                        await conn.execute(
                            self.migration_table.insert().values(
                                id=migration.id,
                                version=migration.version,
                                description=migration.description,
                                applied_at=start_time,
                                execution_time_ms=str(int(execution_time)),
                                success=False,
                                error_message=str(e)[:1000]
                            )
                        )
                        
                        errors += 1
                        results.append({
                            "migration": migration.id,
                            "status": "failed",
                            "error": str(e),
                            "description": migration.description
                        })
                        
                        logger.error(f"Failed to apply migration {migration.id}: {e}")
                        
                        # Stop on first error to prevent cascading failures
                        break
                
            except Exception as e:
                errors += 1
                results.append({
                    "migration": migration.id,
                    "status": "error",
                    "error": str(e),
                    "description": migration.description
                })
                
                logger.error(f"Error applying migration {migration.id}: {e}")
                break
        
        summary = {
            "applied": applied,
            "skipped": skipped,
            "errors": errors,
            "total": len(migrations),
            "dry_run": dry_run,
            "results": results
        }
        
        logger.info(f"Migration summary: {summary}")
        return summary
    
    async def rollback_migration(self, migration_id: str) -> bool:
        """Rollback a specific migration."""
        try:
            # Find the migration
            all_migrations = await self.discover_migrations()
            migration = next((m for m in all_migrations if m.id == migration_id), None)
            
            if not migration:
                logger.error(f"Migration not found: {migration_id}")
                return False
            
            # Check if migration is applied
            applied = await self.get_applied_migrations()
            if not any(m['id'] == migration_id for m in applied):
                logger.warning(f"Migration not applied: {migration_id}")
                return False
            
            logger.info(f"Rolling back migration: {migration}")
            
            async with self.engine.begin() as conn:
                session = AsyncSession(bind=conn)
                
                # Execute rollback
                await migration.down(session)
                
                # Remove from tracking table
                await conn.execute(
                    text("DELETE FROM schema_migrations WHERE id = :id"),
                    {"id": migration_id}
                )
            
            logger.info(f"Successfully rolled back migration: {migration_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error rolling back migration {migration_id}: {e}")
            return False
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """Get current migration status."""
        try:
            all_migrations = await self.discover_migrations()
            applied_migrations = await self.get_applied_migrations()
            pending_migrations = await self.get_pending_migrations()
            
            return {
                "total_migrations": len(all_migrations),
                "applied_count": len(applied_migrations),
                "pending_count": len(pending_migrations),
                "last_applied": applied_migrations[-1] if applied_migrations else None,
                "next_pending": pending_migrations[0].get_metadata() if pending_migrations else None,
                "database_url": self.database_url.split('@')[-1] if '@' in self.database_url else "***",
                "migrations_path": str(self.migrations_path)
            }
            
        except Exception as e:
            logger.error(f"Error getting migration status: {e}")
            return {"error": str(e)}
    
    async def create_migration_template(
        self, 
        name: str, 
        description: str = ""
    ) -> Path:
        """Create a new migration file template."""
        try:
            # Ensure migrations directory exists
            self.migrations_path.mkdir(parents=True, exist_ok=True)
            
            # Generate migration ID with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            migration_id = f"{timestamp}_{name.lower().replace(' ', '_')}"
            
            # Create migration file
            template = f'''"""Migration: {description or name}

Generated at: {datetime.utcnow().isoformat()}
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.migrations.base_migration import BaseMigration


class {name.title().replace('_', '')}Migration(BaseMigration):
    """Migration for {description or name}."""
    
    def _get_migration_id(self) -> str:
        return "{migration_id}"
    
    def _get_description(self) -> str:
        return "{description or name}"
    
    def _get_version(self) -> str:
        return "{timestamp}"
    
    async def up(self, session: AsyncSession) -> None:
        """Apply the migration."""
        # TODO: Implement migration logic
        # Example:
        # await session.execute(text("""
        #     CREATE TABLE example (
        #         id SERIAL PRIMARY KEY,
        #         name VARCHAR(255) NOT NULL
        #     )
        # """))
        pass
    
    async def down(self, session: AsyncSession) -> None:
        """Reverse the migration."""
        # TODO: Implement rollback logic
        # Example:
        # await session.execute(text("DROP TABLE IF EXISTS example"))
        pass
    
    def get_dependencies(self) -> list[str]:
        """Get migration dependencies."""
        return []  # Add dependency migration IDs if needed
'''
            
            migration_file = self.migrations_path / f"{migration_id}.py"
            migration_file.write_text(template)
            
            logger.info(f"Created migration template: {migration_file}")
            return migration_file
            
        except Exception as e:
            logger.error(f"Error creating migration template: {e}")
            raise