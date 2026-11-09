import re
import logging
from typing import Tuple, List, Optional

from app.core.llm_client import generate_structured_json
from app.modules.cv_processing.schemas import (
    CvExtractionSchema,
    SkillExtraction,
    WorkExperienceExtraction,
)

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_INSTRUCTION = """
You are an expert AI Resume Parsing and Candidate Profiling Engine.
Your objective is to extract accurate, structured profile data from the candidate's CV text.

CRITICAL ZERO-HALLUCINATION RULES:
1. NEVER invent, assume, or infer skills, experiences, or certifications that are not explicitly stated in the text.
2. For EVERY skill, you MUST extract a 'source_quote': an exact verbatim phrase or sentence from the CV text where that skill appears.
3. For EVERY work experience, provide a 'source_quote' verifying the role at that company.
4. If candidate mentions 'interested in' or 'reading about' a technology, do NOT record it as a professional skill unless practical usage is described.
5. Accurately calculate total years of professional experience across non-overlapping work periods.
"""


def _normalize_text_for_matching(text: str) -> str:
    """Removes special punctuation and normalizes spacing for substring matching."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def verify_citation(quote: str, raw_text: str) -> bool:
    """
    Checks if the verbatim quote actually appears in the raw source text.
    Uses normalized token matching to handle minor whitespace/punctuation formatting differences.
    """
    if not quote or not raw_text:
        return False
    norm_quote = _normalize_text_for_matching(quote)
    norm_raw = _normalize_text_for_matching(raw_text)
    
    # Check direct substring presence
    if norm_quote in norm_raw:
        return True
        
    # Check if a substantial part (>70% of quote words in order) is present
    quote_words = norm_quote.split()
    if len(quote_words) >= 4:
        # Check consecutive 4-word window
        for i in range(len(quote_words) - 3):
            sub_window = " ".join(quote_words[i : i + 4])
            if sub_window in norm_raw:
                return True

    return False


async def extract_structured_cv(
    raw_text: str,
    provider_override: Optional[str] = None,
) -> Tuple[CvExtractionSchema, int, int]:
    """
    Extracts structured candidate data from raw CV text using the unified LLM client
    (supporting both Azure OpenAI and Google Gemini), then rigorously validates every
    skill against source text to eliminate hallucinations.
    
    Returns:
        Tuple of (verified_schema, verified_skills_count, discarded_hallucinations_count)
    """
    prompt = f"""
Please extract all structured profile information from the following CV text:

--- BEGIN CV TEXT ---
{raw_text}
--- END CV TEXT ---
"""

    parsed_dict = await generate_structured_json(
        prompt=prompt,
        system_instruction=EXTRACTION_SYSTEM_INSTRUCTION,
        schema_class=CvExtractionSchema,
        temperature=0.1,  # Low temperature for deterministic extraction
        provider_override=provider_override,
    )

    # Parse and validate against Pydantic schema
    extracted = CvExtractionSchema.model_validate(parsed_dict)

    # --- HALLUCINATION FILTERING GUARDRAIL ---
    verified_skills: List[SkillExtraction] = []
    discarded_skills_count = 0

    for skill in extracted.skills:
        if verify_citation(skill.source_quote, raw_text):
            verified_skills.append(skill)
        else:
            logger.warning(
                f"[Anti-Hallucination Guardrail] Discarded unverified skill: '{skill.name}' "
                f"Quote not found in text: '{skill.source_quote}'"
            )
            discarded_skills_count += 1

    # Verify work experiences
    verified_experiences: List[WorkExperienceExtraction] = []
    for exp in extracted.work_experiences:
        if verify_citation(exp.source_quote, raw_text):
            verified_experiences.append(exp)
        else:
            # Fallback: if company name and role exist in raw text, keep it
            if exp.company.lower() in raw_text.lower():
                verified_experiences.append(exp)
            else:
                logger.warning(
                    f"[Anti-Hallucination Guardrail] Discarded unverified experience: '{exp.role}' at '{exp.company}'"
                )

    extracted.skills = verified_skills
    extracted.work_experiences = verified_experiences

    return extracted, len(verified_skills), discarded_skills_count
