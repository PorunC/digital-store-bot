"""Consolidated database schema migration - Fixed for multi-DB compatibility.

Creates all core tables with proper data types for SQLite/PostgreSQL compatibility.
This replaces the following migrations:
- 20241201_000001_initial_schema
- 20250723_000002_add_missing_user_columns
- 20250723_000003_add_missing_referral_fields
- 20250724_000004_rename_products_metadata_to_extra_data
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.migrations.base_migration import BaseMigration


class ConsolidatedSchemaFixedMigration(BaseMigration):
    """Consolidated database schema creation with multi-DB compatibility."""
    
    def _get_migration_id(self) -> str:
        return "20241201_000001_consolidated_schema_fixed"
    
    def _get_description(self) -> str:
        return "Create consolidated database schema with multi-DB compatibility"
    
    def _get_version(self) -> str:
        return "2.1.0"
    
    async def _detect_database_type(self, session: AsyncSession) -> str:
        """Detect the database type."""
        try:
            # Try to detect database by executing a database-specific query
            await session.execute(text("SELECT sqlite_version()"))
            return "sqlite"
        except:
            try:
                await session.execute(text("SELECT version()"))
                return "postgresql"
            except:
                return "sqlite"  # Default fallback
    
    async def up(self, session: AsyncSession) -> None:
        """Create consolidated schema with database-specific types."""
        
        db_type = await self._detect_database_type(session)
        
        # Database-specific type mappings
        if db_type == "sqlite":
            uuid_type = "TEXT"
            uuid_default = "(lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))), 2) || '-' || substr('89ab',abs(random())%4+1,1) || substr(lower(hex(randomblob(2))), 2) || '-' || lower(hex(randomblob(6))))"
            json_type = "TEXT"
            json_default = "'{}'"
            timestamp_tz = "TIMESTAMP"
            boolean_false = "0"
            boolean_true = "1"
        else:  # postgresql
            uuid_type = "UUID"
            uuid_default = "gen_random_uuid()"
            json_type = "JSONB"
            json_default = "'{}'::jsonb"
            timestamp_tz = "TIMESTAMP WITH TIME ZONE"
            boolean_false = "FALSE"
            boolean_true = "TRUE"
        
        # Users table with all required columns
        await session.execute(text(f"""
            CREATE TABLE users (
                id {uuid_type} PRIMARY KEY DEFAULT {uuid_default},
                created_at {timestamp_tz} DEFAULT CURRENT_TIMESTAMP,
                updated_at {timestamp_tz} DEFAULT CURRENT_TIMESTAMP,
                version INTEGER DEFAULT 1,
                
                -- Basic user information
                telegram_id BIGINT UNIQUE NOT NULL,
                first_name VARCHAR(255) NOT NULL,
                last_name VARCHAR(255),
                username VARCHAR(255),
                language_code VARCHAR(5) DEFAULT 'en',
                email VARCHAR(255),
                
                -- Subscription information
                subscription_type VARCHAR(20) DEFAULT 'free',
                subscription_expires_at {timestamp_tz},
                total_subscription_days INTEGER DEFAULT 0 NOT NULL,
                
                -- Trial system columns
                is_trial_used BOOLEAN DEFAULT {boolean_false} NOT NULL,
                trial_expires_at {timestamp_tz},
                trial_type VARCHAR(20),
                
                -- User status and activity
                status VARCHAR(20) DEFAULT 'active',
                last_activity_at TIMESTAMP,
                last_active_at {timestamp_tz},
                
                -- Statistics
                total_spent DECIMAL(10, 2) DEFAULT 0.00,
                total_spent_amount FLOAT DEFAULT 0.0 NOT NULL,
                total_spent_currency VARCHAR(3) DEFAULT 'USD' NOT NULL,
                total_referrals INTEGER DEFAULT 0,
                total_orders INTEGER DEFAULT 0 NOT NULL,
                
                -- Referral information (string-based for flexibility)
                referrer_id VARCHAR(255),
                invite_source VARCHAR(255),
                
                -- Additional data
                notes TEXT,
                metadata {json_type} DEFAULT {json_default},
                
                -- Timezone-aware timestamps (legacy)
                created_at_tz {timestamp_tz} DEFAULT CURRENT_TIMESTAMP,
                updated_at_tz {timestamp_tz} DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Products table with extra_data column (using JSON type for compatibility)
        await session.execute(text(f"""
            CREATE TABLE products (
                id {uuid_type} PRIMARY KEY DEFAULT {uuid_default},
                created_at {timestamp_tz} DEFAULT CURRENT_TIMESTAMP,
                updated_at {timestamp_tz} DEFAULT CURRENT_TIMESTAMP,
                version INTEGER DEFAULT 1,
                
                name VARCHAR(255) NOT NULL UNIQUE,
                description TEXT,
                category VARCHAR(50) NOT NULL,
                
                price_amount DECIMAL(10, 2) NOT NULL,
                price_currency VARCHAR(3) DEFAULT 'USD',
                
                duration_days INTEGER NOT NULL,
                delivery_type VARCHAR(50) NOT NULL,
                delivery_template TEXT,
                key_format VARCHAR(255),
                
                stock INTEGER DEFAULT -1,
                status VARCHAR(20) DEFAULT 'active',
                extra_data {json_type} DEFAULT {json_default}
            )
        """))
        
        # Orders table
        await session.execute(text(f"""
            CREATE TABLE orders (
                id {uuid_type} PRIMARY KEY DEFAULT {uuid_default},
                created_at {timestamp_tz} DEFAULT CURRENT_TIMESTAMP,
                updated_at {timestamp_tz} DEFAULT CURRENT_TIMESTAMP,
                version INTEGER DEFAULT 1,
                
                user_id {uuid_type} NOT NULL REFERENCES users(id),
                product_id {uuid_type} NOT NULL REFERENCES products(id),
                
                payment_id VARCHAR(255),
                external_payment_id VARCHAR(255),
                product_name VARCHAR(255) NOT NULL,
                product_description TEXT,
                
                amount DECIMAL(10, 2) NOT NULL,
                currency VARCHAR(3) DEFAULT 'USD',
                quantity INTEGER DEFAULT 1,
                
                payment_method VARCHAR(50),
                payment_gateway VARCHAR(50),
                payment_url TEXT,
                
                status VARCHAR(50) DEFAULT 'pending',
                expires_at TIMESTAMP,
                paid_at TIMESTAMP,
                completed_at TIMESTAMP,
                cancelled_at TIMESTAMP,
                
                notes TEXT,
                referrer_id {uuid_type} REFERENCES users(id),
                promocode VARCHAR(100),
                is_trial BOOLEAN DEFAULT {boolean_false},
                is_extend BOOLEAN DEFAULT {boolean_false}
            )
        """))
        
        # Referrals table with all required fields
        await session.execute(text(f"""
            CREATE TABLE referrals (
                id {uuid_type} PRIMARY KEY DEFAULT {uuid_default},
                created_at {timestamp_tz} DEFAULT CURRENT_TIMESTAMP,
                updated_at {timestamp_tz} DEFAULT CURRENT_TIMESTAMP,
                version INTEGER DEFAULT 1,
                
                referrer_id {uuid_type} NOT NULL REFERENCES users(id),
                referred_user_id {uuid_type} NOT NULL REFERENCES users(id) UNIQUE,
                
                -- Status tracking
                status VARCHAR(20) DEFAULT 'pending' NOT NULL,
                
                -- Reward tracking
                first_level_reward_granted BOOLEAN DEFAULT {boolean_false} NOT NULL,
                second_level_reward_granted BOOLEAN DEFAULT {boolean_false} NOT NULL,
                
                -- Activity tracking
                activated_at {timestamp_tz},
                first_purchase_at {timestamp_tz},
                invite_source VARCHAR(255),
                
                -- Legacy compatibility fields (for existing ReferralModel)
                referred_rewarded_at {timestamp_tz},
                referred_bonus_days INTEGER DEFAULT 0,
                referrer_rewarded_at {timestamp_tz},
                referrer_bonus_days INTEGER DEFAULT 0,
                
                -- Additional data (using 'metadata' column name to match ReferralModel)
                metadata {json_type}
            )
        """))
        
        # Promocodes table
        await session.execute(text(f"""
            CREATE TABLE promocodes (
                id {uuid_type} PRIMARY KEY DEFAULT {uuid_default},
                created_at {timestamp_tz} DEFAULT CURRENT_TIMESTAMP,
                updated_at {timestamp_tz} DEFAULT CURRENT_TIMESTAMP,
                version INTEGER DEFAULT 1,
                
                code VARCHAR(100) NOT NULL UNIQUE,
                promocode_type VARCHAR(50) NOT NULL,
                
                duration_days INTEGER DEFAULT 0,
                discount_percent DECIMAL(5, 2),
                discount_amount DECIMAL(10, 2),
                
                max_uses INTEGER DEFAULT -1,
                current_uses INTEGER DEFAULT 0,
                
                status VARCHAR(50) DEFAULT 'active',
                expires_at TIMESTAMP,
                activated_at TIMESTAMP,
                deactivated_at TIMESTAMP,
                
                metadata {json_type} DEFAULT {json_default}
            )
        """))
        
        # Invites table
        await session.execute(text(f"""
            CREATE TABLE invites (
                id {uuid_type} PRIMARY KEY DEFAULT {uuid_default},
                created_at {timestamp_tz} DEFAULT CURRENT_TIMESTAMP,
                updated_at {timestamp_tz} DEFAULT CURRENT_TIMESTAMP,
                version INTEGER DEFAULT 1,
                
                name VARCHAR(255) NOT NULL UNIQUE,
                hash_code VARCHAR(255) NOT NULL UNIQUE,
                description TEXT,
                campaign VARCHAR(255),
                
                total_clicks INTEGER DEFAULT 0,
                total_conversions INTEGER DEFAULT 0,
                conversion_reward_days INTEGER DEFAULT 0,
                
                status VARCHAR(50) DEFAULT 'active',
                expires_at TIMESTAMP,
                last_clicked_at TIMESTAMP,
                deactivated_at TIMESTAMP,
                
                metadata {json_type} DEFAULT {json_default}
            )
        """))
        
        # Create all indexes
        # Users table indexes
        await session.execute(text("CREATE INDEX idx_users_telegram_id ON users(telegram_id)"))
        await session.execute(text("CREATE INDEX idx_users_subscription ON users(subscription_type, subscription_expires_at)"))
        await session.execute(text("CREATE INDEX idx_users_referrer ON users(referrer_id)"))
        await session.execute(text("CREATE INDEX idx_users_status ON users(status)"))
        
        # Products table indexes
        await session.execute(text("CREATE INDEX idx_products_category ON products(category)"))
        await session.execute(text("CREATE INDEX idx_products_status ON products(status)"))
        await session.execute(text("CREATE INDEX idx_products_name ON products(name)"))
        
        # Orders table indexes
        await session.execute(text("CREATE INDEX idx_orders_user_id ON orders(user_id)"))
        await session.execute(text("CREATE INDEX idx_orders_status ON orders(status)"))
        await session.execute(text("CREATE INDEX idx_orders_payment_id ON orders(payment_id)"))
        await session.execute(text("CREATE INDEX idx_orders_created_at ON orders(created_at)"))
        
        # Referrals table indexes
        await session.execute(text("CREATE INDEX idx_referrals_referrer ON referrals(referrer_id)"))
        await session.execute(text("CREATE INDEX idx_referrals_referred ON referrals(referred_user_id)"))
        await session.execute(text("CREATE INDEX idx_referrals_status ON referrals(status)"))
        
        # Promocodes table indexes
        await session.execute(text("CREATE INDEX idx_promocodes_code ON promocodes(code)"))
        await session.execute(text("CREATE INDEX idx_promocodes_status ON promocodes(status)"))
        await session.execute(text("CREATE INDEX idx_promocodes_type ON promocodes(promocode_type)"))
        
        # Invites table indexes
        await session.execute(text("CREATE INDEX idx_invites_hash ON invites(hash_code)"))
        await session.execute(text("CREATE INDEX idx_invites_status ON invites(status)"))
        await session.execute(text("CREATE INDEX idx_invites_campaign ON invites(campaign)"))
    
    async def down(self, session: AsyncSession) -> None:
        """Drop consolidated schema."""
        
        # Drop tables in reverse order (due to foreign keys)
        await session.execute(text("DROP TABLE IF EXISTS invites CASCADE"))
        await session.execute(text("DROP TABLE IF EXISTS promocodes CASCADE"))
        await session.execute(text("DROP TABLE IF EXISTS referrals CASCADE"))
        await session.execute(text("DROP TABLE IF EXISTS orders CASCADE"))
        await session.execute(text("DROP TABLE IF EXISTS products CASCADE"))
        await session.execute(text("DROP TABLE IF EXISTS users CASCADE"))
    
    async def validate(self, session: AsyncSession) -> bool:
        """Validate that the consolidated migration was applied correctly."""
        try:
            db_type = await self._detect_database_type(session)
            
            if db_type == "sqlite":
                # SQLite validation
                tables_result = await session.execute(text("""
                    SELECT name 
                    FROM sqlite_master 
                    WHERE type = 'table' 
                    AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """))
                
                tables = [row[0] for row in tables_result.fetchall()]
                expected_tables = ['invites', 'orders', 'products', 'promocodes', 'referrals', 'users']
                
                if not all(table in tables for table in expected_tables):
                    return False
                
                # Check users table structure
                users_columns_result = await session.execute(text("PRAGMA table_info(users)"))
                users_columns = [row[1] for row in users_columns_result.fetchall()]
                
                # Check products table has extra_data
                products_columns_result = await session.execute(text("PRAGMA table_info(products)"))
                products_columns = [row[1] for row in products_columns_result.fetchall()]
                
                return 'extra_data' in products_columns and 'is_trial_used' in users_columns
                
            else:
                # PostgreSQL validation
                tables_result = await session.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """))
                
                tables = [row[0] for row in tables_result.fetchall()]
                expected_tables = ['invites', 'orders', 'products', 'promocodes', 'referrals', 'users']
                
                return all(table in tables for table in expected_tables)
            
        except Exception as e:
            print(f"Validation error: {e}")
            return False
    
    def get_dependencies(self) -> list[str]:
        """No dependencies for consolidated migration."""
        return []