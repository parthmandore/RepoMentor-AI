"""add analysis schema

Revision ID: f3d5c91a3b2c
Revises: a6f6c91a3b2b
Create Date: 2026-06-29 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f3d5c91a3b2c'
down_revision: Union[str, None] = 'a6f6c91a3b2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add analyzing enum value
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TYPE repositorystatus ADD VALUE IF NOT EXISTS 'analyzing'")

    # 2. Add analysis summary columns to repositories
    op.add_column('repositories', sa.Column('status_message', sa.String(), nullable=True))
    op.add_column('repositories', sa.Column('health_score', sa.Integer(), nullable=False, server_default='100'))
    op.add_column('repositories', sa.Column('health_grade', sa.String(), nullable=False, server_default="'A'"))
    op.add_column('repositories', sa.Column('total_lines_of_code', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('repositories', sa.Column('average_complexity', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('repositories', sa.Column('max_complexity', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('repositories', sa.Column('total_smells', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('repositories', sa.Column('duplication_percentage', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('repositories', sa.Column('files_analyzed', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('repositories', sa.Column('files_skipped', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('repositories', sa.Column('analysis_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('repositories', sa.Column('analysis_completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('repositories', sa.Column('analysis_duration_seconds', sa.Float(), nullable=True))

    # Remove server defaults
    for col in ['health_score', 'health_grade', 'total_lines_of_code', 'average_complexity',
                'max_complexity', 'total_smells', 'duplication_percentage', 'files_analyzed', 'files_skipped']:
        op.alter_column('repositories', col, server_default=None)

    # 3. Add file-level analysis columns to repository_files
    op.add_column('repository_files', sa.Column('lines_of_code', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('repository_files', sa.Column('complexity', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('repository_files', sa.Column('code_smells_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('repository_files', sa.Column('analysis_metadata', sa.JSON(), nullable=True))

    for col in ['lines_of_code', 'complexity', 'code_smells_count']:
        op.alter_column('repository_files', col, server_default=None)

    # 4. Create code_smells table
    op.create_table(
        'code_smells',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('repository_id', sa.UUID(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('smell_type', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=True),
        sa.Column('measured_value', sa.Float(), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('reason', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_code_smells_repository_id'), 'code_smells', ['repository_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_code_smells_repository_id'), table_name='code_smells')
    op.drop_table('code_smells')

    op.drop_column('repository_files', 'analysis_metadata')
    op.drop_column('repository_files', 'code_smells_count')
    op.drop_column('repository_files', 'complexity')
    op.drop_column('repository_files', 'lines_of_code')

    op.drop_column('repositories', 'analysis_duration_seconds')
    op.drop_column('repositories', 'analysis_completed_at')
    op.drop_column('repositories', 'analysis_started_at')
    op.drop_column('repositories', 'files_skipped')
    op.drop_column('repositories', 'files_analyzed')
    op.drop_column('repositories', 'duplication_percentage')
    op.drop_column('repositories', 'total_smells')
    op.drop_column('repositories', 'max_complexity')
    op.drop_column('repositories', 'average_complexity')
    op.drop_column('repositories', 'total_lines_of_code')
    op.drop_column('repositories', 'health_grade')
    op.drop_column('repositories', 'health_score')
    op.drop_column('repositories', 'status_message')
