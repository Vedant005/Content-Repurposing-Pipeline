import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_brand_profile_crud_and_session_isolation():
    session_a = uuid.uuid4().hex
    session_b = uuid.uuid4().hex
    transport = ASGITransport(app=app)

    # 1. Create brand profile for Session A
    async with AsyncClient(
        transport=transport, base_url="http://test", cookies={"rsid": session_a}
    ) as client_a:
        payload = {
            "brand_name": "TechPulse Media",
            "tone_guidelines": "Punchy, authoritative, no jargon, data-first.",
            "target_audience": "Senior engineers and tech leads.",
            "few_shot_examples": {
                "blog": "# Sample Post\n\nHigh impact engineering patterns.",
                "twitter": "1/ Break down monoliths cleanly. Here is how:",
                "linkedin": "Why modern systems fail under pressure.",
            },
        }
        res_create = await client_a.post("/api/v1/brand-profiles", json=payload)
        assert res_create.status_code == 201
        data = res_create.json()
        assert data["brand_name"] == "TechPulse Media"
        assert data["session_id"] == session_a
        profile_id = data["id"]

        # 2. List profiles for Session A
        res_list = await client_a.get("/api/v1/brand-profiles")
        assert res_list.status_code == 200
        profiles_a = res_list.json()
        assert len(profiles_a) >= 1
        assert any(p["id"] == profile_id for p in profiles_a)

        # 3. Retrieve single profile
        res_get = await client_a.get(f"/api/v1/brand-profiles/{profile_id}")
        assert res_get.status_code == 200
        assert res_get.json()["id"] == profile_id

        # 4. Update profile
        res_update = await client_a.put(
            f"/api/v1/brand-profiles/{profile_id}",
            json={"brand_name": "TechPulse Global", "target_audience": "CTOs and VPs"},
        )
        assert res_update.status_code == 200
        assert res_update.json()["brand_name"] == "TechPulse Global"
        assert res_update.json()["target_audience"] == "CTOs and VPs"

    # 5. Verify Session B cannot access or modify Session A's profile
    async with AsyncClient(
        transport=transport, base_url="http://test", cookies={"rsid": session_b}
    ) as client_b:
        # Cannot retrieve Session A's profile
        res_b_get = await client_b.get(f"/api/v1/brand-profiles/{profile_id}")
        assert res_b_get.status_code == 404

        # Cannot update Session A's profile
        res_b_update = await client_b.put(
            f"/api/v1/brand-profiles/{profile_id}", json={"brand_name": "Hacked Brand"}
        )
        assert res_b_update.status_code == 404

        # Cannot delete Session A's profile
        res_b_del = await client_b.delete(f"/api/v1/brand-profiles/{profile_id}")
        assert res_b_del.status_code == 404

    # 6. Session A deletes its profile
    async with AsyncClient(
        transport=transport, base_url="http://test", cookies={"rsid": session_a}
    ) as client_a:
        res_del = await client_a.delete(f"/api/v1/brand-profiles/{profile_id}")
        assert res_del.status_code == 204

        res_check = await client_a.get(f"/api/v1/brand-profiles/{profile_id}")
        assert res_check.status_code == 404
