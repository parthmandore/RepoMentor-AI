"""initial migration

Revision ID: d3b1a8d052b6
Revises: 
Create Date: 2026-06-29 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd3b1a8d052b6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Define repository status enum
    status_enum = sa.Enum('queued', 'processing', 'ready', 'failed', name='repositorystatus')
    
    op.create_table(
        'repositories',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('status', status_enum, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_repositories_url'), 'repositories', ['url'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_repositories_url'), table_name='repositories')
    op.drop_table('repositories')
    
    # Drop enum type
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        status_enum = sa.Enum(name='repositorystatus')
        status_enum.drop(bind, checkfirst=True)
