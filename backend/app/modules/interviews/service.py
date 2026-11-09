import uuid
import logging
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.cv_processing.models import CvProfile
from app.modules.jobs.models import Job
from app.modules.matching.service import calculate_deterministic_score
from app.modules.interviews.models import InterviewSession, InterviewMessage
from app.modules.interviews.schemas import (
    TurnRubricEvaluation,
    InterviewMessageResponse,
    InterviewSessionResponse,
)
from app.modules.interviews.graph import (
    InterviewGraphState,
    get_stage_for_question,
    generate_opening_question_node,
    evaluate_and_advance_node,
    synthesize_final_report_node,
)

logger = logging.getLogger(__name__)


async def start_interview_session(
    cv_profile_id: uuid.UUID,
    job_id: uuid.UUID,
    db: AsyncSession,
    max_questions: int = 4,
    provider_override: Optional[str] = None,
) -> InterviewSessionResponse:
    """
    Initializes a new stateful AI Mock Interview session for a candidate CV and target Job.
    Automatically computes skill gaps from the deterministic matching engine to guide the interview.
    """
    cv_res = await db.execute(select(CvProfile).where(CvProfile.id == cv_profile_id))
    cv_profile = cv_res.scalar_one_or_none()
    if not cv_profile:
        raise ValueError(f"CV Profile '{cv_profile_id}' not found.")

    job_res = await db.execute(select(Job).where(Job.id == job_id))
    job = job_res.scalar_one_or_none()
    if not job:
        raise ValueError(f"Job '{job_id}' not found.")

    # Extract matched and missing skills using our Tier-1 deterministic engine
    _, matching_skills, missing_skills, exp_analysis = calculate_deterministic_score(cv_profile, job)
    verified_names = [m.skill for m in matching_skills] or [
        s.get("name", "") for s in (cv_profile.skills or []) if s.get("name")
    ]
    missing_names = [m.skill for m in missing_skills]

    provider = (provider_override or settings.LLM_PROVIDER).lower().strip()

    state: InterviewGraphState = {
        "candidate_role": cv_profile.target_role or "Software Engineer",
        "candidate_years": exp_analysis.candidate_years,
        "verified_skills": verified_names,
        "missing_skills": missing_names,
        "cv_summary": cv_profile.raw_text[:600],
        "job_title": job.title,
        "company_name": job.company_name,
        "job_required_skills": list(job.required_skills or []),
        "job_description": job.raw_description[:600],
        "question_index": 1,
        "max_questions": max_questions,
        "provider": provider,
    }

    # Execute Node 1: Generate opening welcome + Question #1
    state = await generate_opening_question_node(state)

    # Persist InterviewSession
    session = InterviewSession(
        user_id=cv_profile.user_id,
        job_id=job.id,
        status="IN_PROGRESS",
    )
    db.add(session)
    await db.flush()

    # Persist initial interviewer message (storing session metadata in first message feedback JSONB)
    opening_msg = InterviewMessage(
        session_id=session.id,
        role="interviewer",
        content=state["next_question"] or "Tell me about your background.",
        step_number=1,
        feedback={
            "max_questions": max_questions,
            "stage": state.get("current_stage", "WARMUP_EXPERIENCE"),
            "cv_profile_id": str(cv_profile.id),
        },
    )
    db.add(opening_msg)
    await db.commit()
    await db.refresh(session)
    await db.refresh(opening_msg)

    return InterviewSessionResponse(
        session_id=session.id,
        user_id=session.user_id,
        cv_profile_id=cv_profile.id,
        job_id=job.id,
        job_title=job.title,
        company_name=job.company_name,
        status=session.status,
        current_question_index=1,
        max_questions=max_questions,
        current_stage=state.get("current_stage", "WARMUP_EXPERIENCE"),
        average_score=None,
        overall_feedback=None,
        messages=[
            InterviewMessageResponse(
                id=opening_msg.id,
                role=opening_msg.role,
                content=opening_msg.content,
                step_number=opening_msg.step_number,
                feedback=opening_msg.feedback,
                created_at=opening_msg.created_at,
            )
        ],
        latest_evaluation=None,
        llm_provider=provider,
    )


async def submit_candidate_answer(
    session_id: uuid.UUID,
    answer: str,
    db: AsyncSession,
    provider_override: Optional[str] = None,
) -> InterviewSessionResponse:
    """
    Processes a candidate's turn in the interview state machine:
    1. Evaluates the answer against the rubric (score, technical accuracy, clarity, STAR feedback)
    2. Advances to the next stage/question or synthesizes the final executive report
    3. Persists all messages and evaluations in PostgreSQL
    """
    stmt = (
        select(InterviewSession)
        .options(selectinload(InterviewSession.messages), selectinload(InterviewSession.job))
        .where(InterviewSession.id == session_id)
    )
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise ValueError(f"Interview session '{session_id}' not found.")

    if session.status == "COMPLETED":
        raise ValueError("This interview session is already completed.")

    job = session.job
    sorted_messages = sorted(session.messages, key=lambda m: m.step_number)

    # Retrieve metadata from first message
    first_meta = (sorted_messages[0].feedback or {}) if sorted_messages else {}
    max_questions = int(first_meta.get("max_questions", 4))
    cv_profile_id_str = first_meta.get("cv_profile_id")

    # Fetch candidate CV profile
    if cv_profile_id_str:
        cv_res = await db.execute(select(CvProfile).where(CvProfile.id == uuid.UUID(cv_profile_id_str)))
        cv_profile = cv_res.scalar_one_or_none()
    else:
        cv_res = await db.execute(
            select(CvProfile).where(CvProfile.user_id == session.user_id).order_by(CvProfile.created_at.desc())
        )
        cv_profile = cv_res.scalars().first()

    verified_names: List[str] = []
    missing_names: List[str] = []
    candidate_role = "Software Engineer"
    candidate_years = 3.0
    cv_summary = ""

    if cv_profile:
        _, matching_skills, missing_skills, exp_analysis = calculate_deterministic_score(cv_profile, job)
        verified_names = [m.skill for m in matching_skills] or [
            s.get("name", "") for s in (cv_profile.skills or []) if s.get("name")
        ]
        missing_names = [m.skill for m in missing_skills]
        candidate_role = cv_profile.target_role or "Software Engineer"
        candidate_years = exp_analysis.candidate_years
        cv_summary = cv_profile.raw_text[:600]

    # Count previous candidate answers to determine current question index
    candidate_msgs = [m for m in sorted_messages if m.role == "candidate"]
    current_question_index = len(candidate_msgs) + 1
    last_interviewer_msg = next((m for m in reversed(sorted_messages) if m.role == "interviewer"), None)
    last_question_text = last_interviewer_msg.content if last_interviewer_msg else ""

    provider = (provider_override or settings.LLM_PROVIDER).lower().strip()

    transcript = [{"role": m.role, "content": m.content} for m in sorted_messages]
    transcript.append({"role": "candidate", "content": answer})

    existing_scores = [
        float(m.feedback["score"])
        for m in candidate_msgs
        if m.feedback and "score" in m.feedback
    ]

    state: InterviewGraphState = {
        "candidate_role": candidate_role,
        "candidate_years": candidate_years,
        "verified_skills": verified_names,
        "missing_skills": missing_names,
        "cv_summary": cv_summary,
        "job_title": job.title,
        "company_name": job.company_name,
        "job_required_skills": list(job.required_skills or []),
        "job_description": job.raw_description[:600],
        "question_index": current_question_index,
        "max_questions": max_questions,
        "last_question": last_question_text,
        "candidate_answer": answer,
        "transcript": transcript,
        "turn_scores": existing_scores,
        "provider": provider,
    }

    # Execute Node 2: Evaluate answer & determine next step
    state = await evaluate_and_advance_node(state)
    eval_dict = state.get("latest_evaluation") or {}
    latest_eval_obj = TurnRubricEvaluation.model_validate(eval_dict) if eval_dict else None

    if latest_eval_obj:
        existing_scores.append(latest_eval_obj.score)
    state["turn_scores"] = existing_scores

    next_step_num = (sorted_messages[-1].step_number if sorted_messages else 0) + 1

    # Save candidate message with rubric evaluation attached
    cand_msg = InterviewMessage(
        session_id=session.id,
        role="candidate",
        content=answer,
        step_number=next_step_num,
        feedback=eval_dict,
    )
    db.add(cand_msg)
    sorted_messages.append(cand_msg)

    if state.get("is_completed"):
        # Execute Node 3: Synthesize final executive report
        state = await synthesize_final_report_node(state)
        session.status = "COMPLETED"
        session.overall_feedback = state.get("final_report")
        closing_msg = InterviewMessage(
            session_id=session.id,
            role="interviewer",
            content=state.get("next_question") or "Thank you for completing the mock interview!",
            step_number=next_step_num + 1,
            feedback={"stage": "COMPLETED"},
        )
        db.add(closing_msg)
        sorted_messages.append(closing_msg)
        active_question_idx = max_questions
    else:
        next_interviewer_msg = InterviewMessage(
            session_id=session.id,
            role="interviewer",
            content=state.get("next_question") or "Could you elaborate further?",
            step_number=next_step_num + 1,
            feedback={"stage": state.get("current_stage", "CORE_TECHNICAL")},
        )
        db.add(next_interviewer_msg)
        sorted_messages.append(next_interviewer_msg)
        active_question_idx = current_question_index + 1

    await db.commit()
    await db.refresh(session)

    avg_score = round(sum(existing_scores) / len(existing_scores), 1) if existing_scores else None

    return InterviewSessionResponse(
        session_id=session.id,
        user_id=session.user_id,
        cv_profile_id=cv_profile.id if cv_profile else None,
        job_id=job.id,
        job_title=job.title,
        company_name=job.company_name,
        status=session.status,
        current_question_index=active_question_idx,
        max_questions=max_questions,
        current_stage=state.get("current_stage", "COMPLETED"),
        average_score=avg_score,
        overall_feedback=session.overall_feedback,
        messages=[
            InterviewMessageResponse(
                id=m.id or uuid.uuid4(),
                role=m.role,
                content=m.content,
                step_number=m.step_number,
                feedback=m.feedback,
                created_at=m.created_at,
            )
            for m in sorted_messages
        ],
        latest_evaluation=latest_eval_obj,
        llm_provider=provider,
    )


async def get_interview_session(
    session_id: uuid.UUID,
    db: AsyncSession,
) -> InterviewSessionResponse:
    """
    Retrieves the complete state, transcript, and evaluations of an interview session.
    """
    stmt = (
        select(InterviewSession)
        .options(selectinload(InterviewSession.messages), selectinload(InterviewSession.job))
        .where(InterviewSession.id == session_id)
    )
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise ValueError(f"Interview session '{session_id}' not found.")

    job = session.job
    sorted_messages = sorted(session.messages, key=lambda m: m.step_number)
    first_meta = (sorted_messages[0].feedback or {}) if sorted_messages else {}
    max_questions = int(first_meta.get("max_questions", 4))
    cv_profile_id_str = first_meta.get("cv_profile_id")

    candidate_msgs = [m for m in sorted_messages if m.role == "candidate"]
    scores = [
        float(m.feedback["score"])
        for m in candidate_msgs
        if m.feedback and "score" in m.feedback
    ]
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    latest_eval_obj = None
    if candidate_msgs and candidate_msgs[-1].feedback:
        try:
            latest_eval_obj = TurnRubricEvaluation.model_validate(candidate_msgs[-1].feedback)
        except Exception:
            latest_eval_obj = None

    current_q_idx = min(len(candidate_msgs) + 1, max_questions)
    current_stage = (
        "COMPLETED"
        if session.status == "COMPLETED"
        else get_stage_for_question(current_q_idx, max_questions)
    )

    return InterviewSessionResponse(
        session_id=session.id,
        user_id=session.user_id,
        cv_profile_id=uuid.UUID(cv_profile_id_str) if cv_profile_id_str else None,
        job_id=job.id,
        job_title=job.title,
        company_name=job.company_name,
        status=session.status,
        current_question_index=current_q_idx,
        max_questions=max_questions,
        current_stage=current_stage,
        average_score=avg_score,
        overall_feedback=session.overall_feedback,
        messages=[
            InterviewMessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                step_number=m.step_number,
                feedback=m.feedback,
                created_at=m.created_at,
            )
            for m in sorted_messages
        ],
        latest_evaluation=latest_eval_obj,
        llm_provider=settings.LLM_PROVIDER,
    )
