"""Add missing referral fields

Revision ID: 20250723_000003
Revises: 20250723_000002
Create Date: 2025-07-23 16:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '20250723_000003'
down_revision = '20250723_000002'
branch_labels = None
depends_on = None


def upgrade():
    """Add missing fields to referrals table."""
    # Add status column
    op.add_column('referrals', sa.Column('status', sa.String(20), nullable=False, server_default='pending'))
    op.create_index('ix_referrals_status', 'referrals', ['status'])
    
    # Add reward tracking flags
    op.add_column('referrals', sa.Column('first_level_reward_granted', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('referrals', sa.Column('second_level_reward_granted', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add activation tracking
    op.add_column('referrals', sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add purchase tracking  
    op.add_column('referrals', sa.Column('first_purchase_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add metadata column
    op.add_column('referrals', sa.Column('metadata', postgresql.JSON(), nullable=True))


def downgrade():
    """Remove added fields from referrals table."""
    op.drop_column('referrals', 'metadata')
    op.drop_column('referrals', 'first_purchase_at')
    op.drop_column('referrals', 'activated_at')
    op.drop_column('referrals', 'second_level_reward_granted')
    op.drop_column('referrals', 'first_level_reward_granted')
    op.drop_index('ix_referrals_status', 'referrals')
    op.drop_column('referrals', 'status')