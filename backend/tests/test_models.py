import pytest
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.models import User, CvProfile, Job, Application, JobMatch


@pytest.mark.asyncio
async def test_create_user_and_cv_profile():
    async with AsyncSessionLocal() as session:
        # Create a test user
        user = User(
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            full_name="Olena Kovalenko",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert user.id is not None
        assert user.created_at is not None

        # Create CV profile with a 768-dim mock embedding
        mock_embedding = [0.01 * (i % 10) for i in range(768)]
        cv = CvProfile(
            user_id=user.id,
            raw_text="Senior Android Engineer with 5 years experience in Kotlin, Coroutines, Jetpack Compose.",
            target_role="Senior Android Engineer",
            years_of_experience=5.0,
            structured_data={"education": [{"degree": "B.Sc. Computer Science"}]},
            work_experiences=[
                {
                    "company": "TechCorp",
                    "role": "Android Developer",
                    "quote": "5 years experience in Kotlin",
                }
            ],
            skills=[
                {"name": "Kotlin", "category": "Languages", "years": 5.0, "quote": "Kotlin, Coroutines"}
            ],
            embedding=mock_embedding,
        )
        session.add(cv)
        await session.commit()
        await session.refresh(cv)

        assert cv.id is not None
        assert cv.user_id == user.id
        assert len(cv.embedding) == 768

        # Clean up
        await session.delete(user)  # Should cascade delete cv_profile
        await session.commit()

        # Verify cascade
        result = await session.execute(select(CvProfile).where(CvProfile.id == cv.id))
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_job_vector_similarity_query():
    async with AsyncSessionLocal() as session:
        # Insert two jobs with distinct 768-dim embeddings
        vec_android = [1.0 if i < 100 else 0.0 for i in range(768)]
        vec_devops = [1.0 if i >= 600 else 0.0 for i in range(768)]

        job1 = Job(
            title="Senior Android Engineer",
            company_name="KyivStar",
            location="Kyiv, Ukraine",
            region="UA",
            raw_description="Looking for an experienced Android engineer with Jetpack Compose.",
            required_skills=["Kotlin", "Jetpack Compose", "Coroutines"],
            preferred_skills=["KMP"],
            min_experience_years=4.0,
            salary_min=4000,
            salary_max=5500,
            salary_currency="USD",
            embedding=vec_android,
        )
        job2 = Job(
            title="Senior DevOps Engineer",
            company_name="CloudUA",
            location="Remote - Ukraine",
            region="UA",
            raw_description="Kubernetes, Terraform, AWS specialist needed.",
            required_skills=["Kubernetes", "Terraform", "AWS"],
            preferred_skills=["Golang"],
            min_experience_years=4.0,
            salary_min=4500,
            salary_max=6000,
            salary_currency="USD",
            embedding=vec_devops,
        )
        session.add_all([job1, job2])
        await session.commit()
        await session.refresh(job1)
        await session.refresh(job2)

        # Query using pgvector cosine distance:
        # A query vector close to Android should rank job1 first with smallest distance
        query_vector = [0.9 if i < 100 else 0.05 for i in range(768)]
        
        # pgvector cosine distance operator is <=>
        stmt = (
            select(Job, Job.embedding.cosine_distance(query_vector).label("distance"))
            .where(Job.id.in_([job1.id, job2.id]))
            .order_by("distance")
        )
        result = await session.execute(stmt)
        rows = result.all()

        assert len(rows) == 2
        # First row must be the Android job because its cosine distance is much lower
        top_job, top_dist = rows[0]
        second_job, second_dist = rows[1]

        assert top_job.title == "Senior Android Engineer"
        assert top_dist < second_dist

        # Clean up
        await session.delete(job1)
        await session.delete(job2)
        await session.commit()
