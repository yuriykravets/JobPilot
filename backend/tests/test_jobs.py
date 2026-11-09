import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_seed_and_query_jobs():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Seed the jobs catalog
        seed_res = await client.post("/api/v1/jobs/seed")
        assert seed_res.status_code == 200
        seed_data = seed_res.json()
        assert seed_data["status"] == "success"
        assert seed_data["seeded_count"] >= 11

        # 2. Re-seeding must be idempotent (no duplicate errors or count inflation)
        seed_res_2 = await client.post("/api/v1/jobs/seed")
        assert seed_res_2.status_code == 200

        # 3. Query all jobs with pagination
        list_res = await client.get("/api/v1/jobs?limit=5&offset=0")
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert len(list_data["items"]) == 5
        assert list_data["total"] >= 11
        assert list_data["has_more"] is True

        # 4. Filter by region (Ukraine - UA)
        ua_res = await client.get("/api/v1/jobs?region=UA")
        assert ua_res.status_code == 200
        ua_data = ua_res.json()
        assert ua_data["total"] >= 4
        for item in ua_data["items"]:
            assert item["region"] == "UA"

        # 5. Filter by skill (Jetpack Compose)
        skill_res = await client.get("/api/v1/jobs?skill=Compose")
        assert skill_res.status_code == 200
        skill_data = skill_res.json()
        assert skill_data["total"] >= 1
        for item in skill_data["items"]:
            all_skills = item["required_skills"] + item["preferred_skills"]
            assert any("compose" in s.lower() for s in all_skills)

        # 6. Filter by min salary ($150k for US jobs)
        salary_res = await client.get("/api/v1/jobs?min_salary=150000")
        assert salary_res.status_code == 200
        salary_data = salary_res.json()
        assert salary_data["total"] >= 2
        for item in salary_data["items"]:
            max_comp = item["salary_max"] or item["salary_min"] or 0
            assert max_comp >= 150000

        # 7. Get specific job by ID
        first_job_id = list_data["items"][0]["id"]
        detail_res = await client.get(f"/api/v1/jobs/{first_job_id}")
        assert detail_res.status_code == 200
        assert detail_res.json()["id"] == first_job_id

        # 8. Non-existent job returns 404
        fake_id = str(uuid.uuid4())
        not_found_res = await client.get(f"/api/v1/jobs/{fake_id}")
        assert not_found_res.status_code == 404


@pytest.mark.asyncio
async def test_create_and_normalize_job():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        payload = {
            "title": "Junior Android Developer",
            "company_name": "AppDev UA",
            "location": "Lviv, Ukraine",
            "region": "UA",
            "raw_description": "We are seeking a junior Android developer to build modern mobile apps in Kotlin.",
            "required_skills": ["kotlin", "compose", "coroutines"],  # Lowercase to test normalization
            "preferred_skills": ["room", "git"],
            "min_experience_years": 1.0,
            "salary_min": 1500,
            "salary_max": 2500,
            "salary_currency": "USD",
            "external_id": f"test-job-{uuid.uuid4().hex[:8]}",
        }
        res = await client.post("/api/v1/jobs", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "Junior Android Developer"
        # Verify normalization occurred
        assert "Kotlin" in data["required_skills"]
        assert "Jetpack Compose" in data["required_skills"]
        assert "Coroutines" in data["required_skills"]
