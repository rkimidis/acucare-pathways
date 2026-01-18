"""Triage case model for patient assessment workflow."""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class TriageTier(str, Enum):
    """Triage tier classification.

    Determined by deterministic rules engine, not AI.
    RED/AMBER cases have booking restrictions.
    """

    RED = "red"  # Urgent - immediate clinical review required
    AMBER = "amber"  # Moderate - requires clinical review before booking
    GREEN = "green"  # Routine - patient can self-book
    BLUE = "blue"  # Low intensity - digital/self-help pathway


class TriageCaseStatus(str, Enum):
    """Triage case workflow status."""

    PENDING = "pending"  # Awaiting triage assessment
    IN_REVIEW = "in_review"  # Under clinical review
    TRIAGED = "triaged"  # Triage completed, tier assigned
    ESCALATED = "escalated"  # Escalated for urgent review
    CLOSED = "closed"  # Case closed


class TriageCase(Base, TimestampMixin, SoftDeleteMixin):
    """Triage case representing a patient's assessment journey.

    Contains questionnaire responses and deterministic tier assignment.
    All changes are tracked via audit events.
    """

    __tablename__ = "triage_cases"

    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[TriageCaseStatus] = mapped_column(
        String(50),
        default=TriageCaseStatus.PENDING,
        nullable=False,
    )
    tier: Mapped[TriageTier | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )
    # ID of the questionnaire definition version used
    questionnaire_version_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("questionnaire_definitions.id"),
        nullable=True,
    )
    # ID of the ruleset version used for triage
    ruleset_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    # SHA256 hash of the ruleset used (for auditability)
    ruleset_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    # Deterministic rule output explaining tier assignment
    tier_explanation: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    # Clinician assigned for review (legacy field)
    assigned_clinician_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id"),
        nullable=True,
    )
    # Current assignment owner (soft assignment model)
    assigned_to_user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # Clinical notes (staff only)
    clinical_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Pathway assigned by rules engine
    pathway: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Safeguards: Whether clinician review is required
    clinician_review_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Safeguards: Whether patient can self-book appointments
    self_book_allowed: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Source referral (if applicable)
    referral_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("referrals.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Escalation tracking
    escalated_at: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    escalated_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    escalation_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # SLA Timer Fields
    # When triage evaluation was completed (tier assigned)
    triaged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # SLA deadline for clinician review (calculated based on tier)
    sla_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    # SLA target in minutes based on tier (RED=15, AMBER=60, GREEN=480, BLUE=1440)
    sla_target_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    # Whether SLA has been breached
    sla_breached: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    # When clinician review was completed
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # Clinician who completed the review
    reviewed_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # PDF Note Export
    triage_note_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    triage_note_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<TriageCase {self.id[:8]}... tier={self.tier} status={self.status}>"

    def calculate_sla_deadline(self) -> datetime | None:
        """Calculate SLA deadline based on tier.

        SLA targets (UK Private Psychiatric standard):
        - RED: 15 minutes (crisis)
        - AMBER: 60 minutes (urgent)
        - GREEN: 8 hours (480 minutes)
        - BLUE: 24 hours (1440 minutes)
        """
        from datetime import timedelta

        if not self.triaged_at or not self.tier:
            return None

        sla_minutes = {
            TriageTier.RED: 15,
            TriageTier.AMBER: 60,
            TriageTier.GREEN: 480,
            TriageTier.BLUE: 1440,
        }

        minutes = sla_minutes.get(self.tier, 480)
        self.sla_target_minutes = minutes
        return self.triaged_at + timedelta(minutes=minutes)
