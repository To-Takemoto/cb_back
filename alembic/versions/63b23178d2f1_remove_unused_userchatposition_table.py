"""Remove unused userchatposition table

Revision ID: 63b23178d2f1
Revises: faa78268640b
Create Date: 2025-06-08 02:07:37.003765

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63b23178d2f1'
down_revision: Union[str, None] = 'faa78268640b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop unused userchatposition table
    op.drop_table('userchatposition')


def downgrade() -> None:
    """Downgrade schema."""
    # Recreate userchatposition table if needed (though it was unused)
    op.create_table('userchatposition',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('discussion_structure_id', sa.Integer(), nullable=False),
        sa.Column('last_position', sa.String(length=255), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['discussion_structure_id'], ['discussionstructure.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_position_user_discussion', 'userchatposition', ['user_id', 'discussion_structure_id'], unique=True)
