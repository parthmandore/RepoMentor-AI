"""add architecture schema

Revision ID: f4d5c91a3b2d
Revises: f3d5c91a3b2c
Create Date: 2026-06-29 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f4d5c91a3b2d'
down_revision: Union[str, None] = 'f3d5c91a3b2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add architecture columns to repositories
    op.add_column('repositories', sa.Column('architecture_score', sa.Integer(), nullable=False, server_default='100'))
    op.add_column('repositories', sa.Column('architecture_grade', sa.String(), nullable=False, server_default="'A'"))
    op.add_column('repositories', sa.Column('architecture_summary', sa.JSON(), nullable=True))
    op.add_column('repositories', sa.Column('architecture_findings', sa.JSON(), nullable=True))

    op.alter_column('repositories', 'architecture_score', server_default=None)
    op.alter_column('repositories', 'architecture_grade', server_default=None)

    # 2. Add architecture columns to repository_files
    op.add_column('repository_files', sa.Column('module_type', sa.String(), nullable=False, server_default="'Unknown'"))
    op.add_column('repository_files', sa.Column('incoming_dependencies', sa.JSON(), nullable=False, server_default='[]'))
    op.add_column('repository_files', sa.Column('outgoing_dependencies', sa.JSON(), nullable=False, server_default='[]'))
    op.add_column('repository_files', sa.Column('coupling_score', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('repository_files', sa.Column('instability_score', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('repository_files', sa.Column('in_dependency_cycle', sa.Boolean(), nullable=False, server_default='false'))

    op.alter_column('repository_files', 'module_type', server_default=None)
    op.alter_column('repository_files', 'incoming_dependencies', server_default=None)
    op.alter_column('repository_files', 'outgoing_dependencies', server_default=None)
    op.alter_column('repository_files', 'coupling_score', server_default=None)
    op.alter_column('repository_files', 'instability_score', server_default=None)
    op.alter_column('repository_files', 'in_dependency_cycle', server_default=None)


def downgrade() -> None:
    op.drop_column('repository_files', 'in_dependency_cycle')
    op.drop_column('repository_files', 'instability_score')
    op.drop_column('repository_files', 'coupling_score')
    op.drop_column('repository_files', 'outgoing_dependencies')
    op.drop_column('repository_files', 'incoming_dependencies')
    op.drop_column('repository_files', 'module_type')

    op.drop_column('repositories', 'architecture_findings')
    op.drop_column('repositories', 'architecture_summary')
    op.drop_column('repositories', 'architecture_grade')
    op.drop_column('repositories', 'architecture_score')
