"""relational assets, events, transcripts, and brand profiles

Revision ID: 0002_relational_assets_and_events
Revises: 0001_initial_content_jobs
Create Date: 2026-11-10 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002_relational_assets'
down_revision: Union[str, None] = '0001_initial_content_jobs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. video_transcripts
    op.create_table(
        'video_transcripts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('segments', sa.JSON(), nullable=False),
        sa.Column('canonical_brief', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_video_transcripts_id'), 'video_transcripts', ['id'], unique=False)
    op.create_index(op.f('ix_video_transcripts_video_id'), 'video_transcripts', ['video_id'], unique=True)

    # 2. brand_profiles
    op.create_table(
        'brand_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('brand_name', sa.String(length=128), nullable=False),
        sa.Column('tone_guidelines', sa.Text(), nullable=True),
        sa.Column('target_audience', sa.Text(), nullable=True),
        sa.Column('few_shot_examples', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_brand_profiles_id'), 'brand_profiles', ['id'], unique=False)
    op.create_index(op.f('ix_brand_profiles_session_id'), 'brand_profiles', ['session_id'], unique=False)

    # 3. Add columns to content_jobs
    op.add_column('content_jobs', sa.Column('video_id', sa.String(length=32), nullable=True))
    op.add_column('content_jobs', sa.Column('transcript_id', sa.Integer(), nullable=True))
    op.add_column('content_jobs', sa.Column('brand_profile_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_content_jobs_video_id'), 'content_jobs', ['video_id'], unique=False)
    op.create_foreign_key('fk_content_jobs_transcript', 'content_jobs', 'video_transcripts', ['transcript_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_content_jobs_brand_profile', 'content_jobs', 'brand_profiles', ['brand_profile_id'], ['id'], ondelete='SET NULL')

    # 4. content_assets
    op.create_table(
        'content_assets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('asset_type', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('content', sa.JSON(), nullable=True),
        sa.Column('validation_errors', sa.JSON(), nullable=True),
        sa.Column('critique_score', sa.Float(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['content_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_content_assets_asset_type'), 'content_assets', ['asset_type'], unique=False)
    op.create_index(op.f('ix_content_assets_id'), 'content_assets', ['id'], unique=False)
    op.create_index(op.f('ix_content_assets_job_id'), 'content_assets', ['job_id'], unique=False)
    op.create_index(op.f('ix_content_assets_status'), 'content_assets', ['status'], unique=False)

    # 5. job_events
    op.create_table(
        'job_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('sequence_num', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['content_jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_events_event_type'), 'job_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_job_events_id'), 'job_events', ['id'], unique=False)
    op.create_index(op.f('ix_job_events_job_id'), 'job_events', ['job_id'], unique=False)
    op.create_index(op.f('ix_job_events_sequence_num'), 'job_events', ['sequence_num'], unique=False)


def downgrade() -> None:
    op.drop_table('job_events')
    op.drop_table('content_assets')
    op.drop_constraint('fk_content_jobs_brand_profile', 'content_jobs', type_='foreignkey')
    op.drop_constraint('fk_content_jobs_transcript', 'content_jobs', type_='foreignkey')
    op.drop_index(op.f('ix_content_jobs_video_id'), table_name='content_jobs')
    op.drop_column('content_jobs', 'brand_profile_id')
    op.drop_column('content_jobs', 'transcript_id')
    op.drop_column('content_jobs', 'video_id')
    op.drop_table('brand_profiles')
    op.drop_table('video_transcripts')
