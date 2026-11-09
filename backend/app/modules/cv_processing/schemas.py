import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, ConfigDict


class ContactInfo(BaseModel):
    email: Optional[str] = Field(default=None, description="Candidate contact email if found in the text")
    phone: Optional[str] = Field(default=None, description="Candidate contact phone number")
    linkedin_url: Optional[str] = Field(default=None, description="LinkedIn profile URL")
    github_url: Optional[str] = Field(default=None, description="GitHub profile URL")
    location: Optional[str] = Field(default=None, description="City, Country or general location")


class SkillExtraction(BaseModel):
    name: str = Field(description="Name of the skill or technology (e.g., 'Kotlin', 'FastAPI', 'PostgreSQL')")
    category: str = Field(
        default="Tools & Other",
        description="Category: 'Languages', 'Frameworks & Libraries', 'Databases & Storage', 'Cloud & DevOps', 'Architecture & Testing', or 'Tools & Other'",
    )
    years_of_experience: Optional[float] = Field(
        default=None,
        description="Years of experience with this skill if explicitly stated or directly calculable from dates",
    )
    source_quote: str = Field(
        description="VERBATIM exact quote from the CV text demonstrating this skill. MUST match characters from the text exactly to prove zero hallucination.",
    )


class WorkExperienceExtraction(BaseModel):
    company: str = Field(description="Company or organization name")
    role: str = Field(description="Job title or role held")
    start_date: Optional[str] = Field(default=None, description="Start date (e.g., 'June 2021' or '2021-06')")
    end_date: Optional[str] = Field(default=None, description="End date (e.g., 'Present' or 'January 2024')")
    responsibilities: List[str] = Field(
        default_factory=list,
        description="Key responsibilities and achievements in this role",
    )
    skills_used: List[str] = Field(
        default_factory=list,
        description="Technologies and skills applied in this specific role",
    )
    source_quote: str = Field(
        description="VERBATIM snippet from the CV describing this position for provenance verification.",
    )


class EducationExtraction(BaseModel):
    institution: str = Field(description="University, college, or educational institution name")
    degree: Optional[str] = Field(default=None, description="Degree obtained (e.g., 'Bachelor of Science')")
    field_of_study: Optional[str] = Field(default=None, description="Major or area of study")
    graduation_year: Optional[int] = Field(default=None, description="Year of graduation if provided")


class CvExtractionSchema(BaseModel):
    """
    Root schema passed to the Gemini LLM for structured extraction.
    Every skill and experience requires verbatim citations for hallucination filtering.
    """
    full_name: Optional[str] = Field(default=None, description="Candidate's full name")
    target_role: Optional[str] = Field(
        default=None,
        description="Primary professional title (e.g., 'Senior Android Engineer', 'Backend Developer')",
    )
    summary: Optional[str] = Field(default=None, description="Professional summary / profile overview")
    total_years_of_experience: Optional[float] = Field(
        default=None,
        description="Total professional years of experience calculated from employment history",
    )
    contact: ContactInfo = Field(default_factory=ContactInfo)
    skills: List[SkillExtraction] = Field(default_factory=list)
    work_experiences: List[WorkExperienceExtraction] = Field(default_factory=list)
    education: List[EducationExtraction] = Field(default_factory=list)


# --- API Request / Response Schemas ---

class CvProfileResponse(BaseModel):
    """
    API response model returning the parsed and stored CV profile.
    """
    id: uuid.UUID
    user_id: uuid.UUID
    target_role: Optional[str]
    years_of_experience: Optional[float]
    structured_data: Dict[str, Any]
    work_experiences: List[Dict[str, Any]]
    skills: List[Dict[str, Any]]
    verified_skills_count: int
    discarded_hallucinations_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
