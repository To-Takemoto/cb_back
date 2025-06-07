"""Add missing core tables

Revision ID: faa78268640b
Revises: a458667e6754
Create Date: 2025-06-08 01:56:41.758064

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'faa78268640b'
down_revision: Union[str, None] = 'a458667e6754'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create user table if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Create prompttemplate table if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS prompttemplate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            uuid VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            template_content TEXT NOT NULL,
            category VARCHAR(255),
            variables TEXT,
            is_public BOOLEAN NOT NULL DEFAULT 0,
            is_favorite BOOLEAN NOT NULL DEFAULT 0,
            usage_count INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user(id)
        );
    """)
    
    # Create conversationpreset table if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS conversationpreset (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            uuid VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            model_id VARCHAR(255) NOT NULL,
            temperature VARCHAR(255) NOT NULL DEFAULT '0.7',
            max_tokens INTEGER NOT NULL DEFAULT 1000,
            system_prompt TEXT,
            is_favorite BOOLEAN NOT NULL DEFAULT 0,
            usage_count INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user(id)
        );
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('conversationpreset')
    op.drop_table('prompttemplate')
    op.drop_table('user')
