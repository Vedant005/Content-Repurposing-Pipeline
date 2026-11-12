import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.db.session import AsyncSessionLocal
from src.main import app
from src.models.content import ContentJob


@pytest.mark.asyncio
async def test_sse_endpoint_unauthorized_session_rejected():
    unique_v = uuid.uuid4().hex[:11]
    async with AsyncSessionLocal() as db:
        job = ContentJob(
            youtube_url=f"https://youtube.com/watch?v={unique_v}",
            status="processing",
            session_id=uuid.uuid4().hex,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id

    transport = ASGITransport(app=app)
    # Request without matching session cookie
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/jobs/{job_id}/events")
        assert response.status_code == 404
        assert "not found or not owned" in response.json()["detail"]


@pytest.mark.asyncio
async def test_repurpose_creates_queued_job_and_dispatches():
    transport = ASGITransport(app=app)
    cookies = {"rsid": uuid.uuid4().hex}
    unique_vid = uuid.uuid4().hex[:11]

    with (
        patch(
            "src.api.repurpose.get_redis_pool",
            new=AsyncMock(side_effect=Exception("Redis offline")),
        ),
        patch("src.api.repurpose.process_repurpose_job", new=AsyncMock(return_value="mocked")),
        patch("src.api.repurpose.event_service.emit", new=AsyncMock()),
    ):
        async with AsyncClient(
            transport=transport, base_url="http://test", cookies=cookies
        ) as client:
            resp = await client.post(
                "/api/v1/repurpose",
                json={"url": f"https://www.youtube.com/watch?v={unique_vid}"},
            )
            assert resp.status_code == 202
            data = resp.json()
            assert data["status"] == "queued"
            assert "job_id" in data


@pytest.mark.asyncio
async def test_retry_single_asset_endpoint():
    transport = ASGITransport(app=app)
    session_id = uuid.uuid4().hex
    cookies = {"rsid": session_id}
    unique_v = uuid.uuid4().hex[:11]

    async with AsyncSessionLocal() as db:
        job = ContentJob(
            youtube_url=f"https://youtube.com/watch?v={unique_v}",
            status="completed",
            session_id=session_id,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id

    with (
        patch(
            "src.api.repurpose.get_redis_pool",
            new=AsyncMock(side_effect=Exception("Redis offline")),
        ),
        patch("src.api.repurpose.process_repurpose_job", new=AsyncMock(return_value="mocked")),
        patch("src.api.repurpose.event_service.emit", new=AsyncMock()),
    ):
        async with AsyncClient(
            transport=transport, base_url="http://test", cookies=cookies
        ) as client:
            # 1. Invalid asset type
            resp_bad = await client.post(f"/api/v1/jobs/{job_id}/assets/invalid_type/retry")
            assert resp_bad.status_code == 422

            # 2. Valid retry request
            resp_ok = await client.post(f"/api/v1/jobs/{job_id}/assets/blog/retry")
            assert resp_ok.status_code == 202
            data = resp_ok.json()
            assert data["status"] == "queued"
            assert data["asset_type"] == "blog"


@pytest.mark.asyncio
async def test_delete_job_endpoint():
    transport = ASGITransport(app=app)
    session_id = uuid.uuid4().hex
    cookies = {"rsid": session_id}
    unique_v = uuid.uuid4().hex[:11]

    async with AsyncSessionLocal() as db:
        job = ContentJob(
            youtube_url=f"https://youtube.com/watch?v={unique_v}",
            status="completed",
            session_id=session_id,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id

    async with AsyncClient(transport=transport, base_url="http://test", cookies=cookies) as client:
        # 1. Delete the job successfully
        resp = await client.delete(f"/api/v1/jobs/{job_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

        # 2. Deleting again returns 404
        resp_404 = await client.delete(f"/api/v1/jobs/{job_id}")
        assert resp_404.status_code == 404

    # 3. Unauthorized session returns 404
    other_cookies = {"rsid": uuid.uuid4().hex}
    async with AsyncClient(
        transport=transport, base_url="http://test", cookies=other_cookies
    ) as client:
        resp_unauth = await client.delete(f"/api/v1/jobs/{job_id}")
        assert resp_unauth.status_code == 404
