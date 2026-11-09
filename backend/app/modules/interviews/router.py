import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.interviews.schemas import (
    InterviewStartRequest,
    InterviewAnswerRequest,
    InterviewSessionResponse,
)
from app.modules.interviews.service import (
    start_interview_session,
    submit_candidate_answer,
    get_interview_session,
)

router = APIRouter(prefix="/interviews", tags=["AI Interview Coach"])


@router.post(
    "/start",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a stateful multi-turn AI Mock Interview session",
)
async def start_interview_endpoint(
    payload: InterviewStartRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Starts a new stateful mock interview tailored to the candidate's CV Profile and target Job.
    Automatically detects missing skill gaps and generates Question #1 (`WARMUP_EXPERIENCE`).
    """
    try:
        return await start_interview_session(
            cv_profile_id=payload.cv_profile_id,
            job_id=payload.job_id,
            db=db,
            max_questions=payload.max_questions,
            provider_override=payload.provider,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{session_id}/answer",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit candidate answer, get rubric evaluation & advance state graph",
)
async def submit_answer_endpoint(
    session_id: uuid.UUID,
    payload: InterviewAnswerRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates the candidate's answer against the technical/STAR rubric (0-10 score, strengths,
    improvements, ideal answer hint) and transitions the interview graph to the next stage
    (or synthesizes the final executive report upon completion).
    """
    try:
        return await submit_candidate_answer(
            session_id=session_id,
            answer=payload.answer,
            db=db,
            provider_override=payload.provider,
        )
    except ValueError as e:
        detail = str(e)
        code = status.HTTP_400_BAD_REQUEST if "already completed" in detail else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=code, detail=detail)


@router.get(
    "/{session_id}",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full interview session state, transcript, and rubric evaluations",
)
async def get_session_endpoint(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await get_interview_session(session_id=session_id, db=db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
