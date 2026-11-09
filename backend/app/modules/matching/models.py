import uuid
from typing import List, Dict, Any, TYPE_CHECKING
from sqlalchemy import Numeric, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.cv_processing.models import CvProfile
    from app.modules.jobs.models import Job


class JobMatch(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Explainable match scorecard between a candidate's CV profile and a Job vacancy.
    Combines:
    1. Deterministic score (exact skills, experience thresholds)
    2. Semantic score (pgvector cosine similarity)
    3. LLM reasoning score (nuanced evaluation of ambiguous requirements)
    """
    __tablename__ = "job_matches"

    cv_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cv_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Scores (0.00 to 100.00)
    overall_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    deterministic_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    semantic_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    llm_reasoning_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    # Explainable Breakdown
    # List of matched skills with candidate evidence: [{"skill": "Kotlin", "evidence": "4 years in CV"}]
    matching_skills: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    
    # List of missing requirements / gaps: [{"skill": "GraphQL", "severity": "preferred"}]
    missing_skills: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)

    # Actionable guidance on how to bridge gaps or position CV
    recommendations: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    cv_profile: Mapped["CvProfile"] = relationship("CvProfile", back_populates="job_matches")
    job: Mapped["Job"] = relationship("Job", back_populates="matches")

    def __repr__(self) -> str:
        return f"<JobMatch(cv={self.cv_profile_id}, job={self.job_id}, score={self.overall_score})>"
