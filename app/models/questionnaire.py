"""Questionnaire models for versioned clinical assessments."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class QuestionnaireDefinition(Base, TimestampMixin):
    """Versioned questionnaire definition.

    Questionnaires are immutable once published. New versions are created
    for updates to maintain audit trail and reproducibility.
    """

    __tablename__ = "questionnaire_definitions"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # JSON schema defining questions, validation rules, and structure
    schema: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )
    # SHA256 hash of schema for integrity verification
    schema_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    # Display order for multi-questionnaire flows
    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    # Reference to previous version (if applicable)
    previous_version_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("questionnaire_definitions.id"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<QuestionnaireDefinition {self.name} v{self.version}>"


class QuestionnaireResponse(Base, TimestampMixin):
    """Patient's response to a questionnaire.

    Responses are immutable once submitted. Links to specific
    questionnaire version for reproducibility.
    """

    __tablename__ = "questionnaire_responses"

    triage_case_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("triage_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    questionnaire_definition_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("questionnaire_definitions.id"),
        nullable=False,
    )
    # Patient's answers as JSON
    answers: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )
    # Computed scores (if applicable)
    computed_scores: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    # Whether response is complete
    is_complete: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    # Timestamp when response was submitted
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # Time taken to complete (seconds)
    completion_time_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<QuestionnaireResponse case={self.triage_case_id[:8]}...>"
