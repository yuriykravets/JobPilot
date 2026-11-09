from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.users.models import User
from app.modules.cv_processing.models import CvProfile
from app.modules.cv_processing.parser import PDFParsingError
from app.modules.cv_processing.service import process_and_save_cv
from app.modules.cv_processing.schemas import CvProfileResponse

router = APIRouter(prefix="/cv", tags=["CV Processing"])

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit


@router.post(
    "/upload",
    response_model=CvProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and parse a candidate CV PDF",
    description="Extracts clean layout-aware text, runs Gemini structured extraction with zero-hallucination verification, and saves to database.",
)
async def upload_cv(
    file: UploadFile = File(..., description="PDF resume file (max 10MB)"),
    user_email: str = Form(default="candidate@example.com", description="Candidate email address"),
    db: AsyncSession = Depends(get_db),
):
    # 1. Validate file extension and MIME type
    if not file.filename.lower().endswith(".pdf") and file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF documents (.pdf) are supported.",
        )

    # 2. Read bytes and check size limit
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of 10MB (got {len(file_bytes) / (1024*1024):.1f}MB).",
        )

    try:
        profile_response = await process_and_save_cv(
            file_bytes=file_bytes,
            user_email=user_email,
            db=db,
        )
        return profile_response
    except PDFParsingError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the CV: {str(e)}",
        )


@router.get(
    "/profile",
    response_model=CvProfileResponse,
    summary="Get candidate profile by email",
)
async def get_cv_profile(
    email: str = "candidate@example.com",
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(CvProfile)
        .join(User, CvProfile.user_id == User.id)
        .where(User.email == email)
    )
    result = await db.execute(stmt)
    cv_profile = result.scalar_one_or_none()

    if not cv_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No CV profile found for user '{email}'. Please upload a CV first.",
        )

    return CvProfileResponse(
        id=cv_profile.id,
        user_id=cv_profile.user_id,
        target_role=cv_profile.target_role,
        years_of_experience=cv_profile.years_of_experience,
        structured_data=cv_profile.structured_data,
        work_experiences=cv_profile.work_experiences,
        skills=cv_profile.skills,
        verified_skills_count=len(cv_profile.skills),
        discarded_hallucinations_count=0,
        created_at=cv_profile.created_at,
        updated_at=cv_profile.updated_at,
    )
