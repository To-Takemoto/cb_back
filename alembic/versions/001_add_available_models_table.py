"""Add available_models table for caching

Revision ID: 001
Revises: 
Create Date: 2025-06-08 01:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 既存のテーブルがない場合のみavailable_modelsテーブルを作成
    op.create_table('available_models',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('context_length', sa.Integer(), nullable=True),
        sa.Column('pricing_prompt', sa.String(length=50), nullable=True),
        sa.Column('pricing_completion', sa.String(length=50), nullable=True),
        sa.Column('architecture_data', sa.Text(), nullable=True),
        sa.Column('created', sa.Integer(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_model_active', 'available_models', ['is_active'], unique=False)
    op.create_index('idx_model_last_updated', 'available_models', ['last_updated'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_model_last_updated', table_name='available_models')
    op.drop_index('idx_model_active', table_name='available_models')
    op.drop_table('available_models')