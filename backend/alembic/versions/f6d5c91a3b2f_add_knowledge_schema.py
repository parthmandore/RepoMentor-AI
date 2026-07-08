"""add knowledge schema

Revision ID: f6d5c91a3b2f
Revises: f5d5c91a3b2e
Create Date: 2026-06-29 17:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f6d5c91a3b2f'
down_revision: Union[str, None] = 'f5d5c91a3b2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add knowledge columns to repositories
    op.add_column('repositories', sa.Column('knowledge_status', sa.String(), nullable=False, server_default='pending'))
    op.add_column('repositories', sa.Column('knowledge_summary', sa.JSON(), nullable=True))

    op.alter_column('repositories', 'knowledge_status', server_default=None)


def downgrade() -> None:
    op.drop_column('repositories', 'knowledge_summary')
    op.drop_column('repositories', 'knowledge_status')
