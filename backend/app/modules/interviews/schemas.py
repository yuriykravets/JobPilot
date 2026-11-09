import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TurnRubricEvaluation(BaseModel):
    """
    Structured rubric evaluation produced by the Evaluator Node for each candidate answer.
    """
    score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Overall score for this answer from 0.0 to 10.0",
    )
    technical_accuracy: float = Field(
        default=8.0,
        ge=0.0,
        le=10.0,
        description="Technical depth and correctness score (0-10)",
    )
    communication_clarity: float = Field(
        default=8.0,
        ge=0.0,
        le=10.0,
        description="Clarity, structure, and STAR method adherence (0-10)",
    )
    stage: str = Field(
        default="TECHNICAL_DEEP_DIVE",
        description="Interview stage of the question being evaluated",
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="Specific strong points demonstrated in the candidate's response",
    )
    improvements: List[str] = Field(
        default_factory=list,
        description="Concrete areas where the answer could be deeper or better structured",
    )
    ideal_answer_hint: str = Field(
        default="",
        description="Concise example of what a 10/10 senior-level answer should mention",
    )


class LlmInterviewTurnOutput(BaseModel):
    """
    Combined structured output from the Interviewer State Graph turn:
    1. Evaluates the candidate's latest answer against the rubric
    2. Generates the next adaptive interview question (or closing statement)
    """
    evaluation: TurnRubricEvaluation
    next_question: str = Field(
        ...,
        description="The next adaptive interview question (or closing remarks if completing)",
    )


class LlmInitialQuestionOutput(BaseModel):
    """Structured output for the opening question of an interview session."""
    welcome_message: str = Field(
        ...,
        description="Brief professional welcome tailored to the candidate and company",
    )
    first_question: str = Field(
        ...,
        description="First technical warm-up question grounded in the candidate's CV and target role",
    )


class LlmFinalReportOutput(BaseModel):
    """Structured output for the final synthesized interview evaluation."""
    hiring_recommendation: str = Field(
        ...,
        description="Overall hiring signal: 'STRONG_HIRE', 'HIRE', 'LEAN_HIRE', or 'NEEDS_PREPARATION'",
    )
    executive_summary: str = Field(
        ...,
        description="2-3 sentence executive summary of the candidate's interview performance",
    )
    key_strengths: List[str] = Field(default_factory=list)
    focus_areas_for_next_interview: List[str] = Field(default_factory=list)


class InterviewStartRequest(BaseModel):
    cv_profile_id: uuid.UUID
    job_id: uuid.UUID
    max_questions: int = Field(default=4, ge=2, le=8)
    provider: Optional[str] = Field(
        default=None,
        description="Optional LLM provider override ('gemini' or 'azure')",
    )


class InterviewAnswerRequest(BaseModel):
    answer: str = Field(..., min_length=2, description="Candidate's response to the current question")
    provider: Optional[str] = Field(
        default=None,
        description="Optional LLM provider override ('gemini' or 'azure')",
    )


class InterviewMessageResponse(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    step_number: int
    feedback: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


class InterviewSessionResponse(BaseModel):
    session_id: uuid.UUID
    user_id: uuid.UUID
    cv_profile_id: Optional[uuid.UUID] = None
    job_id: uuid.UUID
    job_title: str
    company_name: str
    status: str
    current_question_index: int
    max_questions: int
    current_stage: str
    average_score: Optional[float] = None
    overall_feedback: Optional[str] = None
    messages: List[InterviewMessageResponse] = Field(default_factory=list)
    latest_evaluation: Optional[TurnRubricEvaluation] = None
    llm_provider: str = "gemini"
