"""Score model for clinical assessment scores."""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ScoreType(str, Enum):
    """Types of clinical assessment scores."""

    PHQ9 = "phq9"  # Patient Health Questionnaire-9 (depression)
    GAD7 = "gad7"  # Generalized Anxiety Disorder-7
    AUDIT_C = "audit_c"  # Alcohol Use Disorders Identification Test - Consumption
    DAST10 = "dast10"  # Drug Abuse Screening Test


class SeverityBand(str, Enum):
    """Severity band classifications."""

    NONE = "none"
    MINIMAL = "minimal"
    MILD = "mild"
    MODERATE = "moderate"
    MODERATELY_SEVERE = "moderately_severe"
    SEVERE = "severe"


class Score(Base, TimestampMixin):
    """Clinical assessment score record.

    Stores computed scores from questionnaire responses.
    Linked to triage case and questionnaire response for traceability.
    """

    __tablename__ = "scores"

    triage_case_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("triage_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    questionnaire_response_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("questionnaire_responses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Score type (PHQ-9, GAD-7, AUDIT-C, etc.)
    score_type: Mapped[ScoreType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    # Version of the scoring algorithm used
    score_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    # Total score value
    total_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    # Maximum possible score for this assessment
    max_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    # Severity band classification
    severity_band: Mapped[SeverityBand] = mapped_column(
        String(50),
        nullable=False,
    )
    # Individual item scores as JSON
    item_scores: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    # Additional metadata (e.g., specific item flags)
    score_metadata: Mapped[dict | None] = mapped_column(
        "metadata",  # Keep DB column name for compatibility
        JSON,
        nullable=True,
    )
    # Timestamp when score was calculated
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Score {self.score_type.value}={self.total_score} ({self.severity_band.value})>"
