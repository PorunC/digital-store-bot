"""Initial database schema migration.

Creates all core tables for the digital store bot.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.migrations.base_migration import BaseMigration


class InitialSchemaMigration(BaseMigration):
    """Initial database schema creation."""
    
    def _get_migration_id(self) -> str:
        return "20241201_000001_initial_schema"
    
    def _get_description(self) -> str:
        return "Create initial database schema"
    
    def _get_version(self) -> str:
        return "1.0.0"
    
    async def up(self, session: AsyncSession) -> None:
        """Create initial schema."""
        
        # Users table
        await session.execute(text("""
            CREATE TABLE users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                version INTEGER DEFAULT 1,
                
                telegram_id BIGINT UNIQUE NOT NULL,
                first_name VARCHAR(255) NOT NULL,
                last_name VARCHAR(255),
                username VARCHAR(255),
                language_code VARCHAR(10) DEFAULT 'en',
                email VARCHAR(255),
                
                subscription_type VARCHAR(50) DEFAULT 'free',
                subscription_expires_at TIMESTAMP,
                
                status VARCHAR(50) DEFAULT 'active',
                total_spent DECIMAL(10, 2) DEFAULT 0.00,
                total_referrals INTEGER DEFAULT 0,
                last_activity_at TIMESTAMP,
                
                referrer_id VARCHAR(255),
                invite_source VARCHAR(255),
                metadata JSONB DEFAULT '{}'::jsonb,
                
                created_at_tz TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at_tz TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Products table
        await session.execute(text("""
            CREATE TABLE products (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                version INTEGER DEFAULT 1,
                
                name VARCHAR(255) NOT NULL UNIQUE,
                description TEXT,
                category VARCHAR(100) NOT NULL,
                
                price_amount DECIMAL(10, 2) NOT NULL,
                price_currency VARCHAR(3) DEFAULT 'USD',
                
                duration_days INTEGER NOT NULL,
                delivery_type VARCHAR(50) NOT NULL,
                delivery_template TEXT,
                key_format VARCHAR(255),
                
                stock INTEGER DEFAULT -1, -- -1 for unlimited
                status VARCHAR(50) DEFAULT 'active',
                metadata JSONB DEFAULT '{}'::jsonb
            )
        """))
        
        # Orders table
        await session.execute(text("""
            CREATE TABLE orders (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                version INTEGER DEFAULT 1,
                
                user_id UUID NOT NULL REFERENCES users(id),
                product_id UUID NOT NULL REFERENCES products(id),
                
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
                referrer_id UUID REFERENCES users(id),
                promocode VARCHAR(100),
                is_trial BOOLEAN DEFAULT FALSE,
                is_extend BOOLEAN DEFAULT FALSE
            )
        """))
        
        # Referrals table
        await session.execute(text("""
            CREATE TABLE referrals (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                version INTEGER DEFAULT 1,
                
                referrer_id UUID NOT NULL REFERENCES users(id),
                referred_user_id UUID NOT NULL REFERENCES users(id) UNIQUE,
                
                status VARCHAR(50) DEFAULT 'pending',
                first_level_reward_granted BOOLEAN DEFAULT FALSE,
                second_level_reward_granted BOOLEAN DEFAULT FALSE,
                
                activated_at TIMESTAMP,
                first_purchase_at TIMESTAMP,
                invite_source VARCHAR(255),
                metadata JSONB DEFAULT '{}'::jsonb
            )
        """))
        
        # Promocodes table
        await session.execute(text("""
            CREATE TABLE promocodes (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                version INTEGER DEFAULT 1,
                
                code VARCHAR(100) NOT NULL UNIQUE,
                promocode_type VARCHAR(50) NOT NULL,
                
                duration_days INTEGER DEFAULT 0,
                discount_percent DECIMAL(5, 2),
                discount_amount DECIMAL(10, 2),
                
                max_uses INTEGER DEFAULT -1, -- -1 for unlimited
                current_uses INTEGER DEFAULT 0,
                
                status VARCHAR(50) DEFAULT 'active',
                expires_at TIMESTAMP,
                activated_at TIMESTAMP,
                deactivated_at TIMESTAMP,
                
                metadata JSONB DEFAULT '{}'::jsonb
            )
        """))
        
        # Invites table
        await session.execute(text("""
            CREATE TABLE invites (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
                
                metadata JSONB DEFAULT '{}'::jsonb
            )
        """))
        
        # Create indexes
        await session.execute(text("CREATE INDEX idx_users_telegram_id ON users(telegram_id)"))
        await session.execute(text("CREATE INDEX idx_users_subscription ON users(subscription_type, subscription_expires_at)"))
        await session.execute(text("CREATE INDEX idx_users_referrer ON users(referrer_id)"))
        
        await session.execute(text("CREATE INDEX idx_products_category ON products(category)"))
        await session.execute(text("CREATE INDEX idx_products_status ON products(status)"))
        await session.execute(text("CREATE INDEX idx_products_name ON products(name)"))
        
        await session.execute(text("CREATE INDEX idx_orders_user_id ON orders(user_id)"))
        await session.execute(text("CREATE INDEX idx_orders_status ON orders(status)"))
        await session.execute(text("CREATE INDEX idx_orders_payment_id ON orders(payment_id)"))
        await session.execute(text("CREATE INDEX idx_orders_created_at ON orders(created_at)"))
        
        await session.execute(text("CREATE INDEX idx_referrals_referrer ON referrals(referrer_id)"))
        await session.execute(text("CREATE INDEX idx_referrals_referred ON referrals(referred_user_id)"))
        await session.execute(text("CREATE INDEX idx_referrals_status ON referrals(status)"))
        
        await session.execute(text("CREATE INDEX idx_promocodes_code ON promocodes(code)"))
        await session.execute(text("CREATE INDEX idx_promocodes_status ON promocodes(status)"))
        await session.execute(text("CREATE INDEX idx_promocodes_type ON promocodes(promocode_type)"))
        
        await session.execute(text("CREATE INDEX idx_invites_hash ON invites(hash_code)"))
        await session.execute(text("CREATE INDEX idx_invites_status ON invites(status)"))
        await session.execute(text("CREATE INDEX idx_invites_campaign ON invites(campaign)"))
    
    async def down(self, session: AsyncSession) -> None:
        """Drop initial schema."""
        
        # Drop tables in reverse order (due to foreign keys)
        await session.execute(text("DROP TABLE IF EXISTS invites CASCADE"))
        await session.execute(text("DROP TABLE IF EXISTS promocodes CASCADE"))
        await session.execute(text("DROP TABLE IF EXISTS referrals CASCADE"))
        await session.execute(text("DROP TABLE IF EXISTS orders CASCADE"))
        await session.execute(text("DROP TABLE IF EXISTS products CASCADE"))
        await session.execute(text("DROP TABLE IF EXISTS users CASCADE"))
    
    def get_dependencies(self) -> list[str]:
        """No dependencies for initial migration."""
        return []