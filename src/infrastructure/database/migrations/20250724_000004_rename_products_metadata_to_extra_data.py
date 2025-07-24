"""Rename products metadata column to extra_data to match SQLAlchemy model.

Fixes the mismatch between database schema and model definition.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.migrations.base_migration import BaseMigration


class RenameProductsMetadataToExtraDataMigration(BaseMigration):
    """Rename products metadata column to extra_data."""
    
    def _get_migration_id(self) -> str:
        return "20250724_000004_rename_products_metadata_to_extra_data"
    
    def _get_description(self) -> str:
        return "Rename products metadata column to extra_data to match SQLAlchemy model"
    
    def _get_version(self) -> str:
        return "1.0.0"
    
    async def up(self, session: AsyncSession) -> None:
        """Rename metadata column to extra_data."""
        await session.execute(text("""
            ALTER TABLE products 
            RENAME COLUMN metadata TO extra_data
        """))
    
    async def down(self, session: AsyncSession) -> None:
        """Rename extra_data column back to metadata."""
        await session.execute(text("""
            ALTER TABLE products 
            RENAME COLUMN extra_data TO metadata
        """))
    
    def get_dependencies(self) -> list[str]:
        """Depends on initial schema migration."""
        return ["20241201_000001_initial_schema"]