"""Add missing referral fields migration.

Adds status tracking and reward fields to referrals table.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.migrations.base_migration import BaseMigration


class AddMissingReferralFieldsMigration(BaseMigration):
    """Add missing fields to referrals table."""
    
    def _get_migration_id(self) -> str:
        return "20250723_000003_add_missing_referral_fields"
    
    def _get_description(self) -> str:
        return "Add missing fields to referrals table"
    
    def _get_version(self) -> int:
        return 20250723_000003

    async def up(self, session: AsyncSession) -> None:
        """Apply the migration."""
        # Add status column if it doesn't exist
        await session.execute(text("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'referrals' AND column_name = 'status'
                ) THEN
                    ALTER TABLE referrals 
                    ADD COLUMN status VARCHAR(20) DEFAULT 'pending' NOT NULL;
                    
                    CREATE INDEX ix_referrals_status ON referrals (status);
                END IF;
            END $$;
        """))
        
        # Add reward tracking flags
        await session.execute(text("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'referrals' AND column_name = 'first_level_reward_granted'
                ) THEN
                    ALTER TABLE referrals 
                    ADD COLUMN first_level_reward_granted BOOLEAN DEFAULT FALSE NOT NULL;
                END IF;
            END $$;
        """))
        
        await session.execute(text("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'referrals' AND column_name = 'second_level_reward_granted'
                ) THEN
                    ALTER TABLE referrals 
                    ADD COLUMN second_level_reward_granted BOOLEAN DEFAULT FALSE NOT NULL;
                END IF;
            END $$;
        """))
        
        # Add activation tracking
        await session.execute(text("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'referrals' AND column_name = 'activated_at'
                ) THEN
                    ALTER TABLE referrals 
                    ADD COLUMN activated_at TIMESTAMPTZ NULL;
                END IF;
            END $$;
        """))
        
        # Add purchase tracking
        await session.execute(text("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'referrals' AND column_name = 'first_purchase_at'
                ) THEN
                    ALTER TABLE referrals 
                    ADD COLUMN first_purchase_at TIMESTAMPTZ NULL;
                END IF;
            END $$;
        """))
        
        # Add metadata column (for additional tracking data)
        await session.execute(text("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'referrals' AND column_name = 'metadata'
                ) THEN
                    ALTER TABLE referrals 
                    ADD COLUMN metadata JSONB NULL;
                END IF;
            END $$;
        """))

    async def down(self, session: AsyncSession) -> None:
        """Rollback the migration."""
        await session.execute(text("ALTER TABLE referrals DROP COLUMN IF EXISTS metadata"))
        await session.execute(text("ALTER TABLE referrals DROP COLUMN IF EXISTS first_purchase_at"))
        await session.execute(text("ALTER TABLE referrals DROP COLUMN IF EXISTS activated_at"))
        await session.execute(text("ALTER TABLE referrals DROP COLUMN IF EXISTS second_level_reward_granted"))
        await session.execute(text("ALTER TABLE referrals DROP COLUMN IF EXISTS first_level_reward_granted"))
        await session.execute(text("DROP INDEX IF EXISTS ix_referrals_status"))
        await session.execute(text("ALTER TABLE referrals DROP COLUMN IF EXISTS status"))

    async def validate(self, session: AsyncSession) -> bool:
        """Validate that the migration was applied correctly."""
        try:
            # Check that all new columns exist
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'referrals' 
                AND column_name IN (
                    'status', 'first_level_reward_granted', 'second_level_reward_granted',
                    'activated_at', 'first_purchase_at', 'metadata'
                )
                ORDER BY column_name
            """))
            
            columns = [row[0] for row in result.fetchall()]
            expected_columns = [
                'activated_at', 'first_level_reward_granted', 'first_purchase_at',
                'metadata', 'second_level_reward_granted', 'status'
            ]
            
            return set(columns) == set(expected_columns)
            
        except Exception:
            return False