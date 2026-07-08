"""update discovery schema

Revision ID: a6f6c91a3b2b
Revises: d3b1a8d052b6
Create Date: 2026-06-29 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a6f6c91a3b2b'
down_revision: Union[str, None] = 'd3b1a8d052b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update Enum values for repositorystatus (Postgres specific)
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        for state in ['cloning', 'parsing', 'detecting_technologies', 'finalizing']:
            op.execute(f"ALTER TYPE repositorystatus ADD VALUE IF NOT EXISTS '{state}'")

    # 2. Add columns to repositories table
    op.add_column('repositories', sa.Column('total_files', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('repositories', sa.Column('total_folders', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('repositories', sa.Column('text_file_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('repositories', sa.Column('binary_file_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('repositories', sa.Column('language_breakdown', sa.JSON(), nullable=True))
    op.add_column('repositories', sa.Column('tech_stack', sa.JSON(), nullable=True))
    op.add_column('repositories', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('repositories', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('repositories', sa.Column('duration_seconds', sa.Float(), nullable=True))
    op.add_column('repositories', sa.Column('error_message', sa.Text(), nullable=True))

    # Remove server defaults after adding
    op.alter_column('repositories', 'total_files', server_default=None)
    op.alter_column('repositories', 'total_folders', server_default=None)
    op.alter_column('repositories', 'text_file_count', server_default=None)
    op.alter_column('repositories', 'binary_file_count', server_default=None)

    # 3. Create repository_files table
    op.create_table(
        'repository_files',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('repository_id', sa.UUID(), nullable=False),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('extension', sa.String(), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('content_hash', sa.String(), nullable=False),
        sa.Column('is_text', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_repository_files_repository_id'), 'repository_files', ['repository_id'], unique=False)


def downgrade() -> None:
    # Drop index and table repository_files
    op.drop_index(op.f('ix_repository_files_repository_id'), table_name='repository_files')
    op.drop_table('repository_files')

    # Remove columns from repositories table
    op.drop_column('repositories', 'error_message')
    op.drop_column('repositories', 'duration_seconds')
    op.drop_column('repositories', 'completed_at')
    op.drop_column('repositories', 'started_at')
    op.drop_column('repositories', 'tech_stack')
    op.drop_column('repositories', 'language_breakdown')
    op.drop_column('repositories', 'binary_file_count')
    op.drop_column('repositories', 'text_file_count')
    op.drop_column('repositories', 'total_folders')
    op.drop_column('repositories', 'total_files')
