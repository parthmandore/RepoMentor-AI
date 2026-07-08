"""add security schema

Revision ID: f5d5c91a3b2e
Revises: f4d5c91a3b2d
Create Date: 2026-06-29 16:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f5d5c91a3b2e'
down_revision: Union[str, None] = 'f4d5c91a3b2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add security columns to repositories
    op.add_column('repositories', sa.Column('security_score', sa.Integer(), nullable=False, server_default='100'))
    op.add_column('repositories', sa.Column('security_grade', sa.String(), nullable=False, server_default="'A'"))
    op.add_column('repositories', sa.Column('security_summary', sa.JSON(), nullable=True))
    op.add_column('repositories', sa.Column('security_findings', sa.JSON(), nullable=True))

    op.alter_column('repositories', 'security_score', server_default=None)
    op.alter_column('repositories', 'security_grade', server_default=None)

    # 2. Create security_issues table
    op.create_table(
        'security_issues',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('repository_id', sa.UUID(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=True),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('evidence', sa.String(), nullable=False),
        sa.Column('snippet', sa.String(), nullable=True),
        sa.Column('reason', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_security_issues_repository_id'), 'security_issues', ['repository_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_security_issues_repository_id'), table_name='security_issues')
    op.drop_table('security_issues')

    op.drop_column('repositories', 'security_findings')
    op.drop_column('repositories', 'security_summary')
    op.drop_column('repositories', 'security_grade')
    op.drop_column('repositories', 'security_score')
