"""
Central export for all SQLAlchemy domain models.
Ensures that all tables are registered on Base.metadata for Alembic auto-generation.
"""
from app.core.base_model import Base, UUIDPrimaryKeyMixin, TimestampMixin
from app.modules.users.models import User
from app.modules.cv_processing.models import CvProfile
from app.modules.jobs.models import Job
from app.modules.matching.models import JobMatch
from app.modules.applications.models import Application
from app.modules.interviews.models import InterviewSession, InterviewMessage

__all__ = [
    "Base",
    "UUIDPrimaryKeyMixin",
    "TimestampMixin",
    "User",
    "CvProfile",
    "Job",
    "JobMatch",
    "Application",
    "InterviewSession",
    "InterviewMessage",
]
