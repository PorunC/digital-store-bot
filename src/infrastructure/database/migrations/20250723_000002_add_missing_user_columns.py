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
        
        # Helper function to safely execute ALTER COLUMN operations
        async def safe_alter_column(table: str, column: str, new_type: str, using_clause: str = None):
            """Safely alter column type if column exists and type is different."""
            # Check if column exists and get current type
            result = await session.execute(text("""
                SELECT data_type, character_maximum_length 
                FROM information_schema.columns 
                WHERE table_name = :table AND column_name = :column
            """), {"table": table, "column": column})
            
            column_info = result.fetchone()
            if not column_info:
                return  # Column doesn't exist, skip
            
            current_type = column_info[0].upper()
            max_length = column_info[1]
            
            # Check if we need to change the type
            needs_change = False
            if 'VARCHAR' in new_type.upper():
                # Extract length from new_type (e.g., "VARCHAR(20)" -> 20)
                import re
                length_match = re.search(r'VARCHAR\((\d+)\)', new_type.upper())
                new_length = int(length_match.group(1)) if length_match else None
                
                if current_type != 'CHARACTER VARYING' or (new_length and new_length != max_length):
                    needs_change = True
            elif current_type != new_type.upper():
                needs_change = True
            
            if needs_change:
                using_part = f" USING {using_clause}" if using_clause else ""
                await session.execute(text(f"""
                    ALTER TABLE {table} 
                    ALTER COLUMN {column} TYPE {new_type}{using_part}
                """))
        
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
        
        # Update column types to match model - safe alterations
        await safe_alter_column('users', 'subscription_type', 'VARCHAR(20)')
        await safe_alter_column('users', 'language_code', 'VARCHAR(5)')
        await safe_alter_column('users', 'status', 'VARCHAR(20)')
        
        # Fix referrer_id column - the most critical part
        # Step 1: Check if foreign key constraint exists and drop it
        constraint_check = await session.execute(text("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'users' 
            AND constraint_type = 'FOREIGN KEY' 
            AND constraint_name = 'users_referrer_id_fkey'
        """))
        
        if constraint_check.fetchone():
            await session.execute(text("""
                ALTER TABLE users 
                DROP CONSTRAINT users_referrer_id_fkey
            """))
        
        # Step 2: Change referrer_id column type from UUID to VARCHAR if needed
        await safe_alter_column('users', 'referrer_id', 'VARCHAR(255)', 'referrer_id::VARCHAR(255)')
        
        # Note: We don't recreate the foreign key constraint because referrer_id 
        # in the UserModel is now a string (user identifier) not a UUID reference to users.id
        # This allows for more flexible referral systems including external referrers
    
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
        
        # Revert referrer_id back to UUID and recreate foreign key constraint
        # This might fail if there are non-UUID values in referrer_id
        await session.execute(text("""
            ALTER TABLE users 
            ALTER COLUMN referrer_id TYPE UUID USING 
            CASE 
                WHEN referrer_id ~ '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$' 
                THEN referrer_id::UUID 
                ELSE NULL 
            END
        """))
        
        # Recreate the foreign key constraint
        await session.execute(text("""
            ALTER TABLE users 
            ADD CONSTRAINT users_referrer_id_fkey 
            FOREIGN KEY (referrer_id) REFERENCES users(id)
        """))
    
    def get_dependencies(self) -> list[str]:
        """Depends on initial schema migration."""
        return ["20241201_000001_initial_schema"]