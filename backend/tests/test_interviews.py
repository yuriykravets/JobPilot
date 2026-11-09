import uuid
import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.modules.interviews.graph import (
    InterviewGraphState,
    get_stage_for_question,
    generate_opening_question_node,
    evaluate_and_advance_node,
    synthesize_final_report_node,
)


def test_stage_progression_routing():
    assert get_stage_for_question(1, 4) == "WARMUP_EXPERIENCE"
    assert get_stage_for_question(2, 4) == "CORE_TECHNICAL"
    assert get_stage_for_question(3, 4) == "SKILL_GAP_PROBE"
    assert get_stage_for_question(4, 4) == "BEHAVIORAL_STAR"
    assert get_stage_for_question(5, 4) == "COMPLETED"


@pytest.mark.asyncio
async def test_interview_graph_nodes_with_mocked_llm():
    state: InterviewGraphState = {
        "candidate_role": "Senior Backend Engineer",
        "candidate_years": 5.0,
        "verified_skills": ["Python", "FastAPI", "PostgreSQL"],
        "missing_skills": ["Kubernetes"],
        "cv_summary": "5 years building FastAPI microservices.",
        "job_title": "Staff AI Backend Engineer",
        "company_name": "TechCorp",
        "job_required_skills": ["Python", "FastAPI", "Kubernetes"],
        "job_description": "Building scalable AI agents.",
        "question_index": 1,
        "max_questions": 2,
        "provider": "gemini",
    }

    mock_opening = {
        "welcome_message": "Welcome to TechCorp!",
        "first_question": "How have you scaled FastAPI with PostgreSQL in production?",
    }

    with patch(
        "app.modules.interviews.graph.generate_structured_json",
        new_callable=AsyncMock,
        return_value=mock_opening,
    ), patch("app.modules.interviews.graph._has_active_llm", return_value=True):
        state = await generate_opening_question_node(state)
        assert state["current_stage"] == "WARMUP_EXPERIENCE"
        assert "Welcome to TechCorp!" in state["next_question"]
        assert "FastAPI" in state["next_question"]

    # Turn 1 answer -> advances to Question 2 (CORE_TECHNICAL)
    state["last_question"] = state["next_question"]
    state["candidate_answer"] = (
        "We used asyncpg connection pooling with PgBouncer and tuned HNSW vector indexes, "
        "reducing p99 latency from 420ms to 45ms under 2,000 RPS."
    )

    mock_turn_1 = {
        "evaluation": {
            "score": 9.2,
            "technical_accuracy": 9.5,
            "communication_clarity": 9.0,
            "stage": "WARMUP_EXPERIENCE",
            "strengths": ["Quantified p99 latency reduction", "Concrete PgBouncer & HNSW details"],
            "improvements": ["Mention connection pool sizing math"],
            "ideal_answer_hint": "Include pool_size formula relative to Postgres vCPUs.",
        },
        "next_question": "How do you handle zero-downtime deployments in Kubernetes?",
    }

    with patch(
        "app.modules.interviews.graph.generate_structured_json",
        new_callable=AsyncMock,
        return_value=mock_turn_1,
    ), patch("app.modules.interviews.graph._has_active_llm", return_value=True):
        state = await evaluate_and_advance_node(state)
        assert state["is_completed"] is False
        assert state["current_stage"] == "CORE_TECHNICAL"
        assert state["latest_evaluation"]["score"] == 9.2
        assert "Kubernetes" in state["next_question"]

    # Turn 2 (Final question since max_questions=2) -> completes & synthesizes report
    state["question_index"] = 2
    state["turn_scores"] = [9.2, 8.8]
    state["transcript"] = [
        {"role": "interviewer", "content": "Q1"},
        {"role": "candidate", "content": "A1"},
    ]

    mock_final_report = {
        "hiring_recommendation": "STRONG_HIRE",
        "executive_summary": "Candidate demonstrated strong distributed systems metrics and database mastery.",
        "key_strengths": ["Production PostgreSQL & FastAPI optimization"],
        "focus_areas_for_next_interview": ["Deepen Kubernetes operator patterns"],
    }

    with patch(
        "app.modules.interviews.graph.generate_structured_json",
        new_callable=AsyncMock,
        return_value=mock_final_report,
    ), patch("app.modules.interviews.graph._has_active_llm", return_value=True):
        state = await synthesize_final_report_node(state)
        assert "STRONG_HIRE" in state["final_report"]
        assert "9.0/10" in state["final_report"]


@pytest.mark.asyncio
async def test_interview_api_endpoints():
    session_id = uuid.uuid4()
    user_id = uuid.uuid4()
    cv_id = uuid.uuid4()
    job_id = uuid.uuid4()

    mock_start_response = {
        "session_id": str(session_id),
        "user_id": str(user_id),
        "cv_profile_id": str(cv_id),
        "job_id": str(job_id),
        "job_title": "Senior AI Engineer",
        "company_name": "GenAI Labs",
        "status": "IN_PROGRESS",
        "current_question_index": 1,
        "max_questions": 4,
        "current_stage": "WARMUP_EXPERIENCE",
        "average_score": None,
        "overall_feedback": None,
        "messages": [
            {
                "id": str(uuid.uuid4()),
                "role": "interviewer",
                "content": "**Question 1 (WARMUP_EXPERIENCE):** Walk me through your RAG pipeline architecture.",
                "step_number": 1,
                "feedback": {"stage": "WARMUP_EXPERIENCE", "max_questions": 4},
            }
        ],
        "latest_evaluation": None,
        "llm_provider": "gemini",
    }

    with patch(
        "app.modules.interviews.router.start_interview_session",
        new_callable=AsyncMock,
        return_value=mock_start_response,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            res = await client.post(
                "/api/v1/interviews/start",
                json={
                    "cv_profile_id": str(cv_id),
                    "job_id": str(job_id),
                    "max_questions": 4,
                },
            )
            assert res.status_code == 201
            data = res.json()
            assert data["status"] == "IN_PROGRESS"
            assert data["current_stage"] == "WARMUP_EXPERIENCE"
            assert len(data["messages"]) == 1
