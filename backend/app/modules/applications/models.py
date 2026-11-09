import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.users.models import User
    from app.modules.jobs.models import Job


class Application(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Candidate's job application tracker (Kanban board item).
    """
    __tablename__ = "applications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Status: 'SAVED', 'APPLIED', 'INTERVIEWING', 'OFFER', 'REJECTED'
    status: Mapped[str] = mapped_column(String(50), default="SAVED", index=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="applications")
    job: Mapped["Job"] = relationship("Job", back_populates="applications")

    def __repr__(self) -> str:
        return f"<Application(user={self.user_id}, job={self.job_id}, status='{self.status}')>"
