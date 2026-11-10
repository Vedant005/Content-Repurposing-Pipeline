from unittest.mock import AsyncMock, patch
import pytest
from src.db.session import AsyncSessionLocal
from src.models.content import ContentJob
from src.services.event_service import EventService


@pytest.mark.asyncio
async def test_event_service_emit_and_replay():
    service = EventService(redis_url="redis://localhost:6379/9")

    # Create real ContentJob to satisfy foreign key
    async with AsyncSessionLocal() as db:
        job = ContentJob(
            youtube_url="https://youtube.com/watch?v=eventtest",
            status="queued",
            session_id="events_test_session",
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id

    # Mock Redis publish so local tests don't require running redis-server
    with patch("src.services.event_service.aioredis.from_url") as mock_redis_from_url:
        mock_client = AsyncMock()
        mock_redis_from_url.return_value = mock_client

        evt1 = await service.emit(job_id=job_id, event_type="job_created", payload={"url": "test"})
        assert evt1["sequence_num"] == 1
        assert evt1["event_type"] == "job_created"

        evt2 = await service.emit(
            job_id=job_id, event_type="fetching_transcript", payload={"status": "fetching"}
        )
        assert evt2["sequence_num"] == 2

        # Replay events after sequence_num 1
        replayed = await service.get_events_after(job_id=job_id, last_sequence_num=1)
        assert len(replayed) == 1
        assert replayed[0]["sequence_num"] == 2
        assert replayed[0]["event_type"] == "fetching_transcript"


@pytest.mark.asyncio
async def test_event_service_subscribe_replays_missed_and_terminates():
    service = EventService(redis_url="redis://localhost:6379/9")

    mock_events = [
        {
            "id": 1,
            "job_id": 888,
            "sequence_num": 1,
            "event_type": "job_created",
            "payload": {"foo": "bar"},
        },
        {
            "id": 2,
            "job_id": 888,
            "sequence_num": 2,
            "event_type": "job_completed",
            "payload": {"status": "ok"},
        },
    ]

    with patch.object(service, "get_events_after", new=AsyncMock(return_value=mock_events)):
        chunks = []
        async for chunk in service.subscribe_events(job_id=888, last_event_id=1):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert "id: 1" in chunks[0]
        assert "event: job_created" in chunks[0]
        assert "id: 2" in chunks[1]
        assert "event: job_completed" in chunks[1]
