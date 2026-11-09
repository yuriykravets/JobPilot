import uuid
from typing import Dict, Any, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User
from app.modules.cv_processing.models import CvProfile
from app.modules.cv_processing.parser import extract_text_from_pdf, PDFParsingError
from app.modules.cv_processing.extractor import extract_structured_cv
from app.modules.cv_processing.schemas import CvProfileResponse
from app.modules.matching.embeddings import build_cv_embedding_text, generate_embedding


async def process_and_save_cv(
    file_bytes: bytes,
    user_email: str,
    db: AsyncSession,
) -> CvProfileResponse:
    """
    Full pipeline:
    1. Parse PDF layout and extract clean text.
    2. Extract structured candidate profile via Gemini with verbatim citation verification.
    3. Ensure user exists (find or create).
    4. Upsert candidate CvProfile in PostgreSQL.
    """
    # 1. Parse PDF
    raw_text, page_count = extract_text_from_pdf(file_bytes)

    # 2. Extract structured profile with anti-hallucination guardrail
    extracted, verified_skills_count, discarded_count = await extract_structured_cv(raw_text)

    # 3. Find or create user
    stmt = select(User).where(User.email == user_email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        candidate_name = extracted.full_name or user_email.split("@")[0].title()
        user = User(
            email=user_email,
            full_name=candidate_name,
        )
        db.add(user)
        await db.flush()  # Flush to populate user.id

    # 4. Upsert CvProfile
    profile_stmt = select(CvProfile).where(CvProfile.user_id == user.id)
    profile_result = await db.execute(profile_stmt)
    cv_profile = profile_result.scalar_one_or_none()

    structured_data_payload = {
        "contact": extracted.contact.model_dump(),
        "education": [e.model_dump() for e in extracted.education],
        "summary": extracted.summary,
        "page_count": page_count,
    }

    work_experiences_payload = [w.model_dump() for w in extracted.work_experiences]
    skills_payload = [s.model_dump() for s in extracted.skills]

    # Generate 768-dim semantic embedding vector
    embedding_text = build_cv_embedding_text(
        target_role=extracted.target_role,
        summary=extracted.summary,
        skills=skills_payload,
        work_experiences=work_experiences_payload,
    )
    cv_embedding = await generate_embedding(embedding_text)

    if not cv_profile:
        cv_profile = CvProfile(
            user_id=user.id,
            raw_text=raw_text,
            target_role=extracted.target_role,
            years_of_experience=extracted.total_years_of_experience,
            structured_data=structured_data_payload,
            work_experiences=work_experiences_payload,
            skills=skills_payload,
            embedding=cv_embedding,
        )
        db.add(cv_profile)
    else:
        cv_profile.raw_text = raw_text
        cv_profile.target_role = extracted.target_role
        cv_profile.years_of_experience = extracted.total_years_of_experience
        cv_profile.structured_data = structured_data_payload
        cv_profile.work_experiences = work_experiences_payload
        cv_profile.skills = skills_payload
        if cv_embedding:
            cv_profile.embedding = cv_embedding

    await db.commit()
    await db.refresh(cv_profile)

    return CvProfileResponse(
        id=cv_profile.id,
        user_id=user.id,
        target_role=cv_profile.target_role,
        years_of_experience=cv_profile.years_of_experience,
        structured_data=cv_profile.structured_data,
        work_experiences=cv_profile.work_experiences,
        skills=cv_profile.skills,
        verified_skills_count=verified_skills_count,
        discarded_hallucinations_count=discarded_count,
        created_at=cv_profile.created_at,
        updated_at=cv_profile.updated_at,
    )
