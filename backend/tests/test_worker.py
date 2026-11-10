from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from src.db.session import AsyncSessionLocal
from src.models.content import ContentJob
from src.worker.worker import process_repurpose_job, recover_stale_jobs


@pytest.mark.asyncio
async def test_worker_idempotency_skips_completed_job():
    async with AsyncSessionLocal() as db:
        job = ContentJob(
            youtube_url="https://youtube.com/watch?v=123",
            status="completed",
            session_id="test_session",
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id

    result = await process_repurpose_job({}, job_id, "https://youtube.com/watch?v=123")
    assert result == "already_completed"


@pytest.mark.asyncio
async def test_worker_recover_stale_jobs():
    async with AsyncSessionLocal() as db:
        stale_time = datetime.now(UTC) - timedelta(minutes=25)
        job = ContentJob(
            youtube_url="https://youtube.com/watch?v=stale",
            status="processing",
            session_id="test_stale_session",
            updated_at=stale_time,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id

    with patch("src.worker.worker.event_service.emit", new=AsyncMock()):
        reaped_count = await recover_stale_jobs()
        assert reaped_count >= 1

        async with AsyncSessionLocal() as db:
            refreshed = await db.get(ContentJob, job_id)
            assert refreshed.status == "failed"
            assert "timed out" in refreshed.error_message
