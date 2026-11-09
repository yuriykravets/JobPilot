from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Text, Numeric, Integer, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.core.base_model import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.matching.models import JobMatch
    from app.modules.applications.models import Application
    from app.modules.interviews.models import InterviewSession


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Vacancies ingested for Ukraine (UA), Europe (EU), and USA (US).
    Holds structured requirements, salary range, and a 768-dim vector embedding.
    """
    __tablename__ = "jobs"

    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # 'UA', 'EU', 'US', 'REMOTE'

    raw_description: Mapped[str] = mapped_column(Text, nullable=False)

    # Normalized skills lists for deterministic matching
    required_skills: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    preferred_skills: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)

    min_experience_years: Mapped[float] = mapped_column(Numeric(4, 1), default=0.0, nullable=False)

    # Compensation
    salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # Ingestion Source & Deduplication
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)

    # 768-dimensional embedding from job title + summary + requirements
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(768), nullable=True)

    # Relationships
    matches: Mapped[List["JobMatch"]] = relationship(
        "JobMatch", back_populates="job", cascade="all, delete-orphan"
    )
    applications: Mapped[List["Application"]] = relationship(
        "Application", back_populates="job", cascade="all, delete-orphan"
    )
    interview_sessions: Mapped[List["InterviewSession"]] = relationship(
        "InterviewSession", back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, title='{self.title}', company='{self.company_name}', region='{self.region}')>"
