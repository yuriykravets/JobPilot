from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.cv_processing.models import CvProfile
    from app.modules.applications.models import Application
    from app.modules.interviews.models import InterviewSession


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Represents a registered JobPilot user (job seeker).
    """
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    cv_profile: Mapped[Optional["CvProfile"]] = relationship(
        "CvProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    applications: Mapped[List["Application"]] = relationship(
        "Application", back_populates="user", cascade="all, delete-orphan"
    )
    interview_sessions: Mapped[List["InterviewSession"]] = relationship(
        "InterviewSession", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', name='{self.full_name}')>"
