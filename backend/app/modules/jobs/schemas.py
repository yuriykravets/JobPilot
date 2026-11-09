import uuid
from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class JobRegion(str, Enum):
    UA = "UA"          # Ukraine
    EU = "EU"          # Europe
    US = "US"          # United States
    REMOTE = "REMOTE"  # Global Remote


class JobCreateSchema(BaseModel):
    title: str = Field(min_length=2, max_length=255, description="Vacancy title (e.g. 'Senior Android Engineer')")
    company_name: str = Field(min_length=2, max_length=255, description="Hiring company name")
    location: str = Field(min_length=2, max_length=255, description="Location description (e.g. 'Kyiv, Ukraine' or 'Remote')")
    region: JobRegion = Field(default=JobRegion.UA, description="Target geographical region: UA, EU, US, REMOTE")
    raw_description: str = Field(min_length=20, description="Full job description text")
    required_skills: List[str] = Field(default_factory=list, description="Must-have technical skills")
    preferred_skills: List[str] = Field(default_factory=list, description="Nice-to-have technical skills")
    min_experience_years: float = Field(default=0.0, ge=0.0, description="Minimum years of professional experience")
    salary_min: Optional[int] = Field(default=None, ge=0, description="Minimum compensation (monthly or annual)")
    salary_max: Optional[int] = Field(default=None, ge=0, description="Maximum compensation")
    salary_currency: str = Field(default="USD", max_length=3, description="Currency code (USD, EUR, UAH)")
    source_url: Optional[str] = Field(default=None, description="Original job posting URL")
    external_id: Optional[str] = Field(default=None, description="Idempotency key for deduplication")


class JobFilterParams(BaseModel):
    region: Optional[JobRegion] = None
    search_query: Optional[str] = None
    skill: Optional[str] = None
    min_salary: Optional[int] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class JobResponse(BaseModel):
    id: uuid.UUID
    title: str
    company_name: str
    location: str
    region: str
    raw_description: str
    required_skills: List[str]
    preferred_skills: List[str]
    min_experience_years: float
    salary_min: Optional[int]
    salary_max: Optional[int]
    salary_currency: str
    source_url: Optional[str]
    external_id: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedJobsResponse(BaseModel):
    items: List[JobResponse]
    total: int
    limit: int
    offset: int
    has_more: bool
