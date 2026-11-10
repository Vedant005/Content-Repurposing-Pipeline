"""initial content jobs baseline

Revision ID: 0001_initial_content_jobs
Revises: 
Create Date: 2026-11-10 18:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001_initial_content_jobs'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'content_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('youtube_url', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('blog_content', sa.Text(), nullable=True),
        sa.Column('tweets', sa.JSON(), nullable=True),
        sa.Column('linkedin_post', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('session_id', sa.String(length=64), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_content_jobs_id'), 'content_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_content_jobs_session_id'), 'content_jobs', ['session_id'], unique=False)
    op.create_index(op.f('ix_content_jobs_status'), 'content_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_content_jobs_user_id'), 'content_jobs', ['user_id'], unique=False)
    op.create_index(op.f('ix_content_jobs_youtube_url'), 'content_jobs', ['youtube_url'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_content_jobs_youtube_url'), table_name='content_jobs')
    op.drop_index(op.f('ix_content_jobs_user_id'), table_name='content_jobs')
    op.drop_index(op.f('ix_content_jobs_status'), table_name='content_jobs')
    op.drop_index(op.f('ix_content_jobs_session_id'), table_name='content_jobs')
    op.drop_index(op.f('ix_content_jobs_id'), table_name='content_jobs')
    op.drop_table('content_jobs')
