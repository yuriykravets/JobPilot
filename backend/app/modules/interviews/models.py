import uuid
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.users.models import User
    from app.modules.jobs.models import Job


class InterviewSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Represents an ongoing or completed AI mock interview session.
    Managed by the LangGraph interview state machine.
    """
    __tablename__ = "interview_sessions"

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

    # Status: 'IN_PROGRESS', 'COMPLETED', 'ABANDONED'
    status: Mapped[str] = mapped_column(String(50), default="IN_PROGRESS", index=True, nullable=False)
    
    # Final synthesized performance review generated upon completion
    overall_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="interview_sessions")
    job: Mapped["Job"] = relationship("Job", back_populates="interview_sessions")
    messages: Mapped[List["InterviewMessage"]] = relationship(
        "InterviewMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InterviewMessage.step_number",
    )

    def __repr__(self) -> str:
        return f"<InterviewSession(id={self.id}, user={self.user_id}, status='{self.status}')>"


class InterviewMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A single turn/message in an AI mock interview session.
    Stores the role (interviewer/candidate), content, and turn-by-turn rubric evaluation.
    """
    __tablename__ = "interview_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Role: 'interviewer', 'candidate', 'system'
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Turn-by-turn rubric feedback:
    # Example: {"score": 8.5, "strengths": ["STAR method used"], "improvements": ["Provide concrete metrics"]}
    feedback: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Relationships
    session: Mapped["InterviewSession"] = relationship("InterviewSession", back_populates="messages")

    def __repr__(self) -> str:
        return f"<InterviewMessage(session={self.session_id}, step={self.step_number}, role='{self.role}')>"
