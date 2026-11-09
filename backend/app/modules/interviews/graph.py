"""
Stateful Multi-Turn AI Interview State Machine (LangGraph Pattern)
------------------------------------------------------------------
Architectural Highlights for Technical Interviews:
1. Explicit Graph State (`InterviewGraphState`):
   Tracks candidate context, verified CV skills, identified skill gaps against the target job,
   conversation history, current stage, and per-turn rubric evaluations.
2. Deterministic Stage Progression & Conditional Routing:
   - Question 1: WARMUP_EXPERIENCE (Verifies a core claim on the candidate's CV)
   - Question 2: CORE_TECHNICAL (Deep-dives into a primary required skill for the job)
   - Question 3: SKILL_GAP_PROBE (Probes transferable knowledge around a missing/gap skill)
   - Question 4+: BEHAVIORAL_STAR (Evaluates leadership, debugging under pressure, or architecture trade-offs using STAR)
3. Dual-Provider LLM Execution + Heuristic Fallback:
   Routes through `generate_structured_json` (Google Gemini or Azure OpenAI) with strict Pydantic
   schemas, falling back cleanly to deterministic evaluation if no API keys are present.
"""

import logging
from typing import List, Dict, Any, Optional, TypedDict

from app.config import settings
from app.core.llm_client import generate_structured_json
from app.modules.interviews.schemas import (
    TurnRubricEvaluation,
    LlmInterviewTurnOutput,
    LlmInitialQuestionOutput,
    LlmFinalReportOutput,
)

logger = logging.getLogger(__name__)

# Ordered stages in the interview state machine
INTERVIEW_STAGES = [
    "WARMUP_EXPERIENCE",
    "CORE_TECHNICAL",
    "SKILL_GAP_PROBE",
    "BEHAVIORAL_STAR",
]


class InterviewGraphState(TypedDict, total=False):
    """
    State dictionary passed across nodes in the Interview State Machine.
    """
    candidate_role: str
    candidate_years: float
    verified_skills: List[str]
    missing_skills: List[str]
    cv_summary: str
    job_title: str
    company_name: str
    job_required_skills: List[str]
    job_description: str
    question_index: int        # 1-based index of the question being answered/generated
    max_questions: int
    current_stage: str
    last_question: str
    candidate_answer: str
    transcript: List[Dict[str, str]]
    turn_scores: List[float]
    latest_evaluation: Optional[Dict[str, Any]]
    next_question: Optional[str]
    final_report: Optional[str]
    is_completed: bool
    provider: str


def get_stage_for_question(question_index: int, max_questions: int) -> str:
    """
    Conditional edge router: determines the interview stage for a given 1-based question index.
    """
    if question_index > max_questions:
        return "COMPLETED"
    idx = min(question_index - 1, len(INTERVIEW_STAGES) - 1)
    return INTERVIEW_STAGES[max(0, idx)]


def _has_active_llm() -> bool:
    return bool(
        settings.GEMINI_API_KEY
        or (settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY)
    )


async def generate_opening_question_node(state: InterviewGraphState) -> InterviewGraphState:
    """
    Node 1: Generates the personalized welcome and Question #1 (WARMUP_EXPERIENCE).
    """
    stage = get_stage_for_question(1, state.get("max_questions", 4))
    state["current_stage"] = stage
    provider = state.get("provider") or settings.LLM_PROVIDER

    top_skills = ", ".join(state.get("verified_skills", [])[:5]) or "Software Engineering"
    req_skills = ", ".join(state.get("job_required_skills", [])[:5]) or "Modern Stack"

    if not _has_active_llm():
        welcome = (
            f"Welcome! I'm your AI Technical Interviewer for the {state['job_title']} role at {state['company_name']}."
        )
        first_q = (
            f"Looking at your background in {top_skills}, walk me through the most technically challenging "
            f"production system you architected recently and how it relates to {req_skills}."
        )
        state["next_question"] = f"{welcome}\n\n**Question 1 ({stage}):** {first_q}"
        return state

    system_prompt = (
        "You are a Staff Engineer conducting a technical interview. "
        "Be concise, realistic, and ground your first question in the candidate's actual CV skills and target job."
    )
    user_prompt = f"""
Target Job: {state['job_title']} at {state['company_name']}
Required Job Skills: {req_skills}
Candidate Role & Experience: {state.get('candidate_role')} ({state.get('candidate_years')} years)
Candidate Verified Skills: {top_skills}
Candidate CV Excerpt: {state.get('cv_summary', '')[:400]}

Generate a warm 1-sentence welcome and Question #1 (Stage: {stage}) asking about a specific project or skill from their CV relevant to {state['company_name']}.
"""
    try:
        res = await generate_structured_json(
            prompt=user_prompt,
            system_instruction=system_prompt,
            schema_class=LlmInitialQuestionOutput,
            temperature=0.3,
            provider_override=provider,
        )
        welcome = res.get("welcome_message", f"Welcome to your {state['job_title']} interview at {state['company_name']}.")
        first_q = res.get("first_question", f"Tell me about your recent production experience with {top_skills}.")
        state["next_question"] = f"{welcome}\n\n**Question 1 ({stage}):** {first_q}"
    except Exception as e:
        logger.warning(f"[InterviewGraph] Opening question LLM fallback: {e}")
        state["next_question"] = (
            f"Welcome to your mock interview for **{state['job_title']}** at **{state['company_name']}**.\n\n"
            f"**Question 1 ({stage}):** Based on your experience with {top_skills}, what is the most complex "
            f"architectural trade-off you solved in production?"
        )

    return state


async def evaluate_and_advance_node(state: InterviewGraphState) -> InterviewGraphState:
    """
    Node 2: Evaluates the candidate's answer against the rubric AND generates either:
    - The next adaptive question (if question_index < max_questions), OR
    - Marks the state ready for final report synthesis (if question_index >= max_questions).
    """
    current_q_idx = state.get("question_index", 1)
    max_q = state.get("max_questions", 4)
    evaluated_stage = get_stage_for_question(current_q_idx, max_q)
    next_q_idx = current_q_idx + 1
    next_stage = get_stage_for_question(next_q_idx, max_q)
    is_final_turn = current_q_idx >= max_q
    provider = state.get("provider") or settings.LLM_PROVIDER

    answer_text = state.get("candidate_answer", "").strip()
    word_count = len(answer_text.split())

    # Stage-specific directive for the next question
    missing_list = state.get("missing_skills", [])
    req_list = state.get("job_required_skills", [])

    if is_final_turn:
        next_q_directive = "This was the final question. Provide a brief concluding thank-you statement."
    elif next_stage == "CORE_TECHNICAL":
        focus_skill = req_list[0] if req_list else "distributed systems"
        next_q_directive = f"Generate Question #{next_q_idx} (Stage: CORE_TECHNICAL): Ask a deep technical edge-case or architecture question about {focus_skill}."
    elif next_stage == "SKILL_GAP_PROBE":
        gap_skill = missing_list[0] if missing_list else (req_list[-1] if req_list else "scalability")
        next_q_directive = (
            f"Generate Question #{next_q_idx} (Stage: SKILL_GAP_PROBE): The job requires '{gap_skill}', which was a gap on the CV. "
            f"Ask how they would approach learning or applying transferable concepts to '{gap_skill}'."
        )
    else:
        next_q_directive = (
            f"Generate Question #{next_q_idx} (Stage: BEHAVIORAL_STAR): Ask a behavioral STAR question about resolving a production incident, bottleneck, or technical disagreement."
        )

    if not _has_active_llm():
        # Deterministic heuristic evaluation for offline/test environments
        base_score = min(9.2, max(5.5, 5.0 + (word_count / 25.0)))
        eval_obj = TurnRubricEvaluation(
            score=round(base_score, 1),
            technical_accuracy=round(base_score, 1),
            communication_clarity=round(min(9.5, base_score + 0.3), 1),
            stage=evaluated_stage,
            strengths=["Addressed the core prompt directly", "Clear communication structure"],
            improvements=["Include concrete production metrics (latency, throughput, error rates)", "Explicitly frame trade-offs using the STAR method"],
            ideal_answer_hint="State the Situation/Task, quantify the architectural bottleneck, explain why you chose your approach over alternatives, and give measurable Results.",
        )
        state["latest_evaluation"] = eval_obj.model_dump()
        state["current_stage"] = next_stage
        state["is_completed"] = is_final_turn
        if not is_final_turn:
            state["next_question"] = f"**Question {next_q_idx} ({next_stage}):** {next_q_directive}"
        return state

    system_prompt = """
You are a Bar-Raiser Principal Engineer and Interview Coach.
1. Evaluate the candidate's answer objectively on a 0-10 scale (technical accuracy, clarity/STAR structure).
2. Give 2-3 specific strengths, 2 concrete improvements, and a concise 'ideal_answer_hint'.
3. Generate the next question according to the requested stage directive.
"""
    user_prompt = f"""
Job Role: {state['job_title']} at {state['company_name']}
Required Skills: {', '.join(req_list)}
Missing Skill Gaps on CV: {', '.join(missing_list) if missing_list else 'None'}

Current Question (#{current_q_idx}, Stage: {evaluated_stage}):
{state.get('last_question', '')}

Candidate's Answer:
{answer_text}

Next Step Directive:
{next_q_directive}
"""
    try:
        res = await generate_structured_json(
            prompt=user_prompt,
            system_instruction=system_prompt,
            schema_class=LlmInterviewTurnOutput,
            temperature=0.25,
            provider_override=provider,
        )
        eval_data = res.get("evaluation", {})
        eval_data["stage"] = evaluated_stage
        validated_eval = TurnRubricEvaluation.model_validate(eval_data)
        state["latest_evaluation"] = validated_eval.model_dump()
        state["current_stage"] = next_stage
        state["is_completed"] = is_final_turn

        if not is_final_turn:
            raw_next_q = res.get("next_question", next_q_directive)
            state["next_question"] = f"**Question {next_q_idx} ({next_stage}):** {raw_next_q}"
        else:
            state["next_question"] = res.get("next_question", "Thank you for completing all interview questions!")

    except Exception as e:
        logger.warning(f"[InterviewGraph] Turn evaluation LLM fallback: {e}")
        base_score = min(9.0, max(6.0, 5.5 + (word_count / 30.0)))
        fallback_eval = TurnRubricEvaluation(
            score=round(base_score, 1),
            technical_accuracy=round(base_score, 1),
            communication_clarity=round(base_score, 1),
            stage=evaluated_stage,
            strengths=["Demonstrated relevant domain familiarity"],
            improvements=["Quantify system scale and operational impact with concrete numbers"],
            ideal_answer_hint="Combine deep architectural mechanics with measurable business/engineering outcomes.",
        )
        state["latest_evaluation"] = fallback_eval.model_dump()
        state["current_stage"] = next_stage
        state["is_completed"] = is_final_turn
        if not is_final_turn:
            state["next_question"] = f"**Question {next_q_idx} ({next_stage}):** {next_q_directive}"

    return state


async def synthesize_final_report_node(state: InterviewGraphState) -> InterviewGraphState:
    """
    Node 3: Executed when `is_completed` is True. Synthesizes all turn evaluations and transcript
    into an actionable Executive Interview Scorecard & Study Plan.
    """
    scores = state.get("turn_scores", [])
    avg_score = round(sum(scores) / len(scores), 1) if scores else 7.5
    provider = state.get("provider") or settings.LLM_PROVIDER

    if not _has_active_llm():
        rec = "STRONG_HIRE" if avg_score >= 8.5 else ("HIRE" if avg_score >= 7.0 else "NEEDS_PREPARATION")
        state["final_report"] = (
            f"### Hiring Signal: {rec} (Avg Score: {avg_score}/10)\n\n"
            f"**Executive Summary:** Completed {len(scores)}-stage technical and behavioral interview for "
            f"**{state['job_title']}** at **{state['company_name']}**. Demonstrated solid foundation in "
            f"{', '.join(state.get('verified_skills', [])[:3]) or 'core engineering'}.\n\n"
            f"**Next Steps Before Real Interview:**\n"
            f"- Prepare 2 quantified STAR stories with latency/scale metrics.\n"
            f"- Review gap areas: {', '.join(state.get('missing_skills', [])[:3]) or 'System Design trade-offs'}."
        )
        return state

    transcript_text = "\n".join(
        [f"{m['role'].upper()}: {m['content'][:300]}" for m in state.get("transcript", [])]
    )
    system_prompt = (
        "You are a Hiring Committee Chair synthesizing a candidate's mock interview performance. "
        "Provide an honest hiring signal, a concise executive summary, key strengths, and focus areas."
    )
    user_prompt = f"""
Job: {state['job_title']} at {state['company_name']}
Average Turn Score: {avg_score}/10 across {len(scores)} questions.
Missing Skill Gaps on CV: {', '.join(state.get('missing_skills', [])) or 'None'}

Interview Transcript Summary:
{transcript_text}
"""
    try:
        res = await generate_structured_json(
            prompt=user_prompt,
            system_instruction=system_prompt,
            schema_class=LlmFinalReportOutput,
            temperature=0.2,
            provider_override=provider,
        )
        rec = res.get("hiring_recommendation", "HIRE")
        summary = res.get("executive_summary", "")
        strengths = "\n".join([f"- {s}" for s in res.get("key_strengths", [])])
        focus = "\n".join([f"- {f}" for f in res.get("focus_areas_for_next_interview", [])])

        state["final_report"] = (
            f"### Hiring Signal: {rec} (Average Score: {avg_score}/10)\n\n"
            f"{summary}\n\n"
            f"**Key Strengths Demonstrated:**\n{strengths}\n\n"
            f"**Action Plan for Your Real Interview:**\n{focus}"
        )
    except Exception as e:
        logger.warning(f"[InterviewGraph] Final report synthesis fallback: {e}")
        state["final_report"] = (
            f"### Interview Completed (Average Score: {avg_score}/10)\n\n"
            f"Strong engagement across {len(scores)} questions for **{state['job_title']}** at **{state['company_name']}**. "
            f"Focus on quantifying production impact and reviewing {', '.join(state.get('missing_skills', [])[:2]) or 'system design'}."
        )

    return state
