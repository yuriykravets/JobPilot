from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App Information
    APP_NAME: str = "JobPilot"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # PostgreSQL Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://jobpilot:jobpilot_dev@localhost:5432/jobpilot",
        description="Async connection string for SQLAlchemy asyncpg",
    )
    DATABASE_SYNC_URL: str = Field(
        default="postgresql+psycopg2://jobpilot:jobpilot_dev@localhost:5432/jobpilot",
        description="Sync connection string for Alembic migrations",
    )

    # Redis Cache & Queue
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Connection URL for Redis",
    )

    # LLM & AI Configuration
    # Supported providers: "gemini" | "azure"
    LLM_PROVIDER: str = Field(
        default="gemini",
        description="Active LLM provider: 'gemini' or 'azure'",
    )

    # Google Gemini
    GEMINI_API_KEY: str = Field(
        default="",
        description="Google Gemini API key for embeddings and reasoning",
    )

    # Azure OpenAI
    AZURE_OPENAI_API_KEY: str = Field(
        default="",
        description="Azure OpenAI API key (found in Azure Portal under Azure OpenAI resource -> Keys and Endpoint)",
    )
    AZURE_OPENAI_ENDPOINT: str = Field(
        default="",
        description="Azure OpenAI Endpoint URL (e.g., https://my-resource.openai.azure.com/)",
    )
    AZURE_OPENAI_DEPLOYMENT_NAME: str = Field(
        default="gpt-4o-mini",
        description="Azure OpenAI Chat Deployment name configured in Azure AI Studio",
    )
    AZURE_OPENAI_API_VERSION: str = Field(
        default="2024-08-01-preview",
        description="Azure OpenAI API Version for enterprise API stability",
    )
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = Field(
        default="text-embedding-3-small",
        description="Azure OpenAI Embedding Deployment name (optional)",
    )

    # Langfuse Observability
    LANGFUSE_PUBLIC_KEY: str = Field(default="")
    LANGFUSE_SECRET_KEY: str = Field(default="")
    LANGFUSE_HOST: str = Field(default="https://cloud.langfuse.com")

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
