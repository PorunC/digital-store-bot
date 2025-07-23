"""Add missing user columns migration.

Adds missing columns to users table to match the UserModel.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.migrations.base_migration import BaseMigration


class AddMissingUserColumnsMigration(BaseMigration):
    """Add missing columns to users table."""
    
    def _get_migration_id(self) -> str:
        return "20250723_000002_add_missing_user_columns"
    
    def _get_description(self) -> str:
        return "Add missing columns to users table"
    
    def _get_version(self) -> str:
        return "1.0.1"
    
    async def up(self, session: AsyncSession) -> None:
        """Add missing columns to users table."""
        
        # Add missing trial system columns
        await session.execute(text("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS is_trial_used BOOLEAN DEFAULT FALSE NOT NULL
        """))
        
        await session.execute(text("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS trial_expires_at TIMESTAMP WITH TIME ZONE
        """))
        
        await session.execute(text("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS trial_type VARCHAR(20)
        """))
        
        # Add missing subscription columns
        await session.execute(text("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS total_subscription_days INTEGER DEFAULT 0 NOT NULL
        """))
        
        # Update existing subscription_type column to match model constraints
        await session.execute(text("""
            ALTER TABLE users 
            ALTER COLUMN subscription_type TYPE VARCHAR(20)
        """))
        
        # Add missing statistics columns
        await session.execute(text("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS total_orders INTEGER DEFAULT 0 NOT NULL
        """))
        
        await session.execute(text("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS total_spent_amount FLOAT DEFAULT 0.0 NOT NULL
        """))
        
        await session.execute(text("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS total_spent_currency VARCHAR(3) DEFAULT 'USD' NOT NULL
        """))
        
        await session.execute(text("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMP WITH TIME ZONE
        """))
        
        # Add notes column
        await session.execute(text("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS notes TEXT
        """))
        
        # Update language_code column size to match model
        await session.execute(text("""
            ALTER TABLE users 
            ALTER COLUMN language_code TYPE VARCHAR(5)
        """))
        
        # Update status column size to match model
        await session.execute(text("""
            ALTER TABLE users 
            ALTER COLUMN status TYPE VARCHAR(20)
        """))
        
        # Rename and adjust referrer_id column to match model (should be string, not UUID)
        await session.execute(text("""
            ALTER TABLE users 
            ALTER COLUMN referrer_id TYPE VARCHAR(255) USING referrer_id::VARCHAR(255)
        """))
    
    async def down(self, session: AsyncSession) -> None:
        """Remove the added columns."""
        
        # Remove added columns
        await session.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS is_trial_used"))
        await session.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS trial_expires_at"))
        await session.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS trial_type"))
        await session.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS total_subscription_days"))
        await session.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS total_orders"))
        await session.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS total_spent_amount"))
        await session.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS total_spent_currency"))
        await session.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS last_active_at"))
        await session.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS notes"))
        
        # Revert column type changes
        await session.execute(text("ALTER TABLE users ALTER COLUMN subscription_type TYPE VARCHAR(50)"))
        await session.execute(text("ALTER TABLE users ALTER COLUMN language_code TYPE VARCHAR(10)"))
        await session.execute(text("ALTER TABLE users ALTER COLUMN status TYPE VARCHAR(50)"))
        
        # Revert referrer_id back to UUID (this might fail if there are invalid UUIDs)
        await session.execute(text("ALTER TABLE users ALTER COLUMN referrer_id TYPE UUID USING referrer_id::UUID"))
    
    def get_dependencies(self) -> list[str]:
        """Depends on initial schema migration."""
        return ["20241201_000001_initial_schema"]