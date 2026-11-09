"""
Unified Multi-Provider LLM Client Abstraction (Azure OpenAI & Google Gemini)
---------------------------------------------------------------------------
Architectural Notes for Enterprise & Technical Interviews:

1. Azure OpenAI vs Direct OpenAI:
   - Resource & Endpoint: Azure provisions a dedicated cloud resource (e.g., https://<company-res>.openai.azure.com/).
   - Deployments: In direct OpenAI, requests specify model names ("gpt-4o"). In Azure OpenAI, you deploy a model
     under a custom Deployment Name (e.g., "jobpilot-gpt4o-mini"). The SDK's 'model' argument maps to this deployment name.
   - API Versioning: Azure mandates explicit API version strings (e.g., '2024-08-01-preview', '2024-10-21') ensuring
     deterministic contracts without unexpected model updates.
   - Security & Compliance: Azure provides enterprise data isolation (customer data is never used for training),
     regional data residency (e.g., West Europe / East US / Sweden Central), private endpoints (VNet), and Entra ID (RBAC)
     authentication via Cognitive Services OpenAI User role without static API keys.

2. Resilience & Rate-Limiting (TPM / RPM):
   - Azure enforces Tokens-Per-Minute (TPM) and Requests-Per-Minute (RPM) quotas per deployment.
   - Production systems implement exponential backoff with jitter on HTTP 429 (RateLimitError).
"""

import asyncio
import json
import logging
import random
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel
from openai import AsyncAzureOpenAI, RateLimitError, APIError
from google import genai
from google.genai import types as genai_types

from app.config import settings

logger = logging.getLogger(__name__)

# Max retries for transient HTTP 429 / 5xx errors from LLM gateways
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1.0


def get_azure_client() -> Optional[AsyncAzureOpenAI]:
    """
    Constructs an asynchronous Azure OpenAI client.
    Can authenticate via API key or Entra ID / DefaultAzureCredential.
    """
    if not settings.AZURE_OPENAI_ENDPOINT or not settings.AZURE_OPENAI_API_KEY:
        return None

    return AsyncAzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )


def get_gemini_client() -> Optional[genai.Client]:
    """
    Constructs a Google Gemini client using google-genai SDK.
    """
    if not settings.GEMINI_API_KEY:
        return None
    return genai.Client(api_key=settings.GEMINI_API_KEY)


async def generate_structured_json(
    prompt: str,
    system_instruction: str,
    schema_class: Optional[Type[BaseModel]] = None,
    temperature: float = 0.2,
    provider_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes a structured JSON LLM completion supporting Azure OpenAI and Google Gemini.
    
    Features:
    - Automatic provider switching via settings.LLM_PROVIDER ("azure" or "gemini")
    - Exponential backoff with random jitter for Azure 429 RateLimit handling
    - Robust JSON response extraction and Pydantic validation
    """
    provider = provider_override or settings.LLM_PROVIDER.lower().strip()

    if provider == "azure":
        return await _generate_azure_json(
            prompt=prompt,
            system_instruction=system_instruction,
            schema_class=schema_class,
            temperature=temperature,
        )
    elif provider == "gemini":
        return await _generate_gemini_json(
            prompt=prompt,
            system_instruction=system_instruction,
            schema_class=schema_class,
            temperature=temperature,
        )
    else:
        raise ValueError(f"Unsupported LLM provider '{provider}'. Must be 'azure' or 'gemini'.")


async def _generate_azure_json(
    prompt: str,
    system_instruction: str,
    schema_class: Optional[Type[BaseModel]] = None,
    temperature: float = 0.2,
) -> Dict[str, Any]:
    """
    Calls Azure OpenAI with structured JSON output and exponential backoff retry logic.
    """
    client = get_azure_client()
    if not client:
        raise ValueError(
            "Azure OpenAI is selected as provider, but AZURE_OPENAI_ENDPOINT or "
            "AZURE_OPENAI_API_KEY is not configured."
        )

    deployment = settings.AZURE_OPENAI_DEPLOYMENT_NAME or "gpt-4o-mini"
    
    # Instruction to strictly ensure valid JSON is returned with target Pydantic JSON schema
    schema_hint = ""
    if schema_class:
        schema_json = json.dumps(schema_class.model_json_schema(), indent=2)
        schema_hint = f"\n\nExpected JSON Schema:\n{schema_json}"

    json_system_prompt = (
        f"{system_instruction}\n\n"
        "CRITICAL REQUIREMENT: Output must be a strictly valid, parseable JSON object matching the requested schema."
        f"{schema_hint}"
    )

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                f"[Azure OpenAI] Requesting completion on deployment '{deployment}' "
                f"(Attempt {attempt}/{MAX_RETRIES})"
            )
            response = await client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": json_system_prompt},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=temperature,
            )

            raw_content = response.choices[0].message.content or "{}"
            parsed = json.loads(raw_content)

            if schema_class:
                # Validate against target Pydantic schema
                validated = schema_class.model_validate(parsed)
                return validated.model_dump()
            return parsed

        except RateLimitError as e:
            # Azure OpenAI Token Per Minute (TPM) quota hit
            sleep_time = (BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))) + random.uniform(0.1, 0.5)
            logger.warning(
                f"[Azure OpenAI RateLimit 429] Deployment '{deployment}' hit rate limit: {e}. "
                f"Retrying in {sleep_time:.2f}s..."
            )
            if attempt == MAX_RETRIES:
                raise
            await asyncio.sleep(sleep_time)

        except (json.JSONDecodeError, APIError) as e:
            logger.error(f"[Azure OpenAI Error] Attempt {attempt} failed: {e}")
            if attempt == MAX_RETRIES:
                raise
            await asyncio.sleep(1.0)


async def _generate_gemini_json(
    prompt: str,
    system_instruction: str,
    schema_class: Optional[Type[BaseModel]] = None,
    temperature: float = 0.2,
) -> Dict[str, Any]:
    """
    Calls Google Gemini with structured JSON output and fallback model cascade.
    """
    client = get_gemini_client()
    if not client:
        raise ValueError("Google Gemini is selected, but GEMINI_API_KEY is not configured.")

    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    last_error = None

    for model_name in models_to_try:
        try:
            config_kwargs: Dict[str, Any] = {
                "system_instruction": system_instruction,
                "response_mime_type": "application/json",
                "temperature": temperature,
            }
            if schema_class:
                config_kwargs["response_schema"] = schema_class

            logger.info(f"[Gemini] Requesting completion using model '{model_name}'")
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config=genai_types.GenerateContentConfig(**config_kwargs),
            )

            if response.text:
                parsed = json.loads(response.text)
                if schema_class:
                    validated = schema_class.model_validate(parsed)
                    return validated.model_dump()
                return parsed

        except Exception as e:
            logger.warning(f"[Gemini] Model '{model_name}' failed: {e}. Trying fallback...")
            last_error = e

    raise RuntimeError(f"All Gemini models failed to generate valid structured JSON. Last error: {last_error}")
