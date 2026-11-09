import asyncio
import logging
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types

from app.config import settings
from app.core.llm_client import get_azure_client

logger = logging.getLogger(__name__)

GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
TARGET_DIMENSIONS = 768


def build_cv_embedding_text(
    target_role: Optional[str],
    summary: Optional[str],
    skills: List[Dict[str, Any]],
    work_experiences: List[Dict[str, Any]],
) -> str:
    """
    Transforms structured CV data into a rich semantic string optimized for vector similarity.
    """
    parts = []
    if target_role:
        parts.append(f"Target Role: {target_role}")

    if summary:
        parts.append(f"Profile Summary: {summary}")

    skill_names = [s.get("name", "") for s in skills if s.get("name")]
    if skill_names:
        parts.append(f"Technical Skills: {', '.join(skill_names)}")

    exp_bullets = []
    for exp in work_experiences[:3]:  # Focus on top 3 most recent experiences
        role = exp.get("role", "")
        company = exp.get("company", "")
        responsibilities = exp.get("responsibilities", [])
        if role and company:
            exp_bullets.append(f"{role} at {company}: {'; '.join(responsibilities[:3])}")
    
    if exp_bullets:
        parts.append("Work History: " + " | ".join(exp_bullets))

    return "\n".join(parts)


def build_job_embedding_text(
    title: str,
    company: str,
    location: str,
    required_skills: List[str],
    preferred_skills: List[str],
    description: str,
) -> str:
    """
    Transforms job posting details into a rich semantic string optimized for vector similarity.
    """
    parts = [
        f"Job Title: {title}",
        f"Company: {company}",
        f"Location: {location}",
    ]
    if required_skills:
        parts.append(f"Must-have Skills: {', '.join(required_skills)}")
    if preferred_skills:
        parts.append(f"Preferred Skills: {', '.join(preferred_skills)}")

    # Shorten description to primary overview (~400 characters)
    clean_desc = " ".join(description.split())[:400]
    parts.append(f"Description Overview: {clean_desc}")

    return "\n".join(parts)


async def generate_embedding(
    text: str,
    provider_override: Optional[str] = None,
) -> Optional[List[float]]:
    """
    Generates a 768-dimensional float embedding using either:
    - Azure OpenAI ('text-embedding-3-small' with dimensions=768 Matryoshka reduction)
    - Google Gemini ('gemini-embedding-001' with output_dimensionality=768)
    Both produce normalized 768-dim vectors compatible with our PostgreSQL Vector(768) HNSW index.
    """
    if not text or not text.strip():
        return None

    clean_text = text.strip()
    provider = (provider_override or settings.LLM_PROVIDER).lower().strip()

    # 1. Try Azure OpenAI Embeddings if configured as primary provider
    if provider == "azure":
        azure_client = get_azure_client()
        if azure_client:
            deployment = settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT or "text-embedding-3-small"
            try:
                response = await azure_client.embeddings.create(
                    model=deployment,
                    input=clean_text,
                    dimensions=TARGET_DIMENSIONS,
                )
                if response.data and len(response.data) > 0:
                    return response.data[0].embedding
            except Exception as e:
                logger.error(f"[Azure OpenAI Embeddings] Failed with deployment '{deployment}': {e}")
                # If Gemini key is available as fallback, continue; otherwise return None
                if not settings.GEMINI_API_KEY:
                    return None

    # 2. Gemini Embeddings (Primary when LLM_PROVIDER='gemini' or fallback)
    if not settings.GEMINI_API_KEY:
        logger.warning("Neither Azure Embedding nor GEMINI_API_KEY is configured; skipping embedding generation.")
        return None

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    try:
        response = await client.aio.models.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            contents=clean_text,
            config=types.EmbedContentConfig(output_dimensionality=TARGET_DIMENSIONS),
        )
        if response.embeddings and len(response.embeddings) > 0:
            return response.embeddings[0].values
    except Exception as e:
        logger.error(f"Failed to generate embedding with {GEMINI_EMBEDDING_MODEL}: {e}")

    return None


async def generate_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """
    Generates embeddings for multiple texts concurrently using asyncio.gather.
    """
    tasks = [generate_embedding(t) for t in texts]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r if isinstance(r, list) else None for r in results]
