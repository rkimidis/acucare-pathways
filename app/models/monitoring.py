"""Waiting list monitoring models.

Sprint 5: Check-in tracking for patients on the waiting list,
including mini-assessments (PHQ-2/GAD-2) and deterioration detection.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class CheckInStatus(str, Enum):
    """Status of a waiting list check-in."""

    SCHEDULED = "scheduled"  # Check-in is scheduled to be sent
    SENT = "sent"  # Check-in request sent to patient
    PENDING = "pending"  # Awaiting patient response
    COMPLETED = "completed"  # Patient completed check-in
    MISSED = "missed"  # Patient did not respond in time
    CANCELLED = "cancelled"  # Check-in was cancelled


class EscalationReason(str, Enum):
    """Reason for escalating a case from check-in."""

    PHQ2_ELEVATED = "phq2_elevated"  # PHQ-2 score >= 3
    GAD2_ELEVATED = "gad2_elevated"  # GAD-2 score >= 3
    SUICIDAL_IDEATION = "suicidal_ideation"  # Positive response to SI question
    SELF_HARM = "self_harm"  # Reported self-harm
    PATIENT_REQUEST = "patient_request"  # Patient requested urgent review
    DETERIORATION = "deterioration"  # Overall score deterioration
    NO_RESPONSE = "no_response"  # Multiple missed check-ins


class WaitingListCheckIn(Base, TimestampMixin, SoftDeleteMixin):
    """Weekly check-in record for patients on the waiting list.

    Tracks scheduled check-ins, patient responses, and any escalations
    triggered by deterioration or risk indicators.
    """

    __tablename__ = "waiting_list_checkins"

    # Patient and triage case
    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    triage_case_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("triage_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Check-in sequence (1st, 2nd, 3rd, etc.)
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    # Status
    status: Mapped[CheckInStatus] = mapped_column(
        String(30),
        default=CheckInStatus.SCHEDULED,
        nullable=False,
        index=True,
    )
    # Scheduling
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # PHQ-2 responses (2 questions, 0-3 each, total 0-6)
    phq2_q1: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    phq2_q2: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    phq2_total: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    # GAD-2 responses (2 questions, 0-3 each, total 0-6)
    gad2_q1: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    gad2_q2: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    gad2_total: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    # Risk screening questions
    suicidal_ideation: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    self_harm: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    # Patient wellbeing rating (1-10)
    wellbeing_rating: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    # Free-text comments
    patient_comments: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Whether patient wants to speak to someone
    wants_callback: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    # Escalation tracking
    requires_escalation: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    escalation_reason: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    escalation_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    escalated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    escalated_by_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    # Staff review
    reviewed_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    staff_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Raw response data for auditing
    raw_response: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    # Reminder tracking
    reminders_sent: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_reminder_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def calculate_scores(self) -> None:
        """Calculate PHQ-2 and GAD-2 totals from individual responses."""
        if self.phq2_q1 is not None and self.phq2_q2 is not None:
            self.phq2_total = self.phq2_q1 + self.phq2_q2

        if self.gad2_q1 is not None and self.gad2_q2 is not None:
            self.gad2_total = self.gad2_q1 + self.gad2_q2

    def check_escalation_needed(self) -> tuple[bool, str | None]:
        """Check if this check-in requires escalation.

        Returns (needs_escalation, reason) tuple.

        Escalation triggers:
        - PHQ-2 >= 3 (depression screening positive)
        - GAD-2 >= 3 (anxiety screening positive)
        - Any suicidal ideation
        - Any self-harm reported
        - Patient requesting callback with low wellbeing
        """
        # Immediate escalation for safety concerns
        if self.suicidal_ideation:
            return True, EscalationReason.SUICIDAL_IDEATION

        if self.self_harm:
            return True, EscalationReason.SELF_HARM

        # PHQ-2 threshold (>= 3 suggests major depression)
        if self.phq2_total is not None and self.phq2_total >= 3:
            return True, EscalationReason.PHQ2_ELEVATED

        # GAD-2 threshold (>= 3 suggests anxiety disorder)
        if self.gad2_total is not None and self.gad2_total >= 3:
            return True, EscalationReason.GAD2_ELEVATED

        # Patient-requested escalation with distress
        if self.wants_callback and self.wellbeing_rating is not None and self.wellbeing_rating <= 3:
            return True, EscalationReason.PATIENT_REQUEST

        return False, None

    def __repr__(self) -> str:
        return f"<WaitingListCheckIn {self.id[:8]}... seq={self.sequence_number} status={self.status}>"


class MonitoringSchedule(Base, TimestampMixin):
    """Configuration for patient monitoring schedules.

    Defines how often check-ins are sent and when to escalate
    for non-response.
    """

    __tablename__ = "monitoring_schedules"

    triage_case_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("triage_cases.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    # Whether monitoring is active
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    # Check-in frequency in days
    frequency_days: Mapped[int] = mapped_column(
        Integer,
        default=7,  # Weekly
        nullable=False,
    )
    # How many reminders before marking as missed
    max_reminders: Mapped[int] = mapped_column(
        Integer,
        default=2,
        nullable=False,
    )
    # Hours to wait before each reminder
    reminder_interval_hours: Mapped[int] = mapped_column(
        Integer,
        default=24,
        nullable=False,
    )
    # Hours until check-in expires
    expiry_hours: Mapped[int] = mapped_column(
        Integer,
        default=72,  # 3 days
        nullable=False,
    )
    # Number of consecutive missed check-ins before escalation
    missed_threshold_escalation: Mapped[int] = mapped_column(
        Integer,
        default=2,
        nullable=False,
    )
    # Last check-in date
    last_checkin_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # Next scheduled check-in
    next_checkin_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    # Count of consecutive missed check-ins
    consecutive_missed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    # Whether to pause monitoring (e.g., patient on vacation)
    paused: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    paused_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    pause_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<MonitoringSchedule case={self.triage_case_id[:8]}... active={self.is_active}>"


class MonitoringAlert(Base, TimestampMixin):
    """Alert generated by the monitoring system for staff review.

    Aggregates escalation triggers and missed check-ins for
    efficient staff workflow.
    """

    __tablename__ = "monitoring_alerts"

    # Related entities
    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    triage_case_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("triage_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    checkin_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("waiting_list_checkins.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Alert type
    alert_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    # Alert details
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    # Score data for context
    phq2_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    gad2_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    acknowledged_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolution_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Action taken
    action_taken: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    # Whether case was escalated to AMBER
    escalated_to_amber: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    def acknowledge(self, user_id: str) -> None:
        """Mark alert as acknowledged."""
        from app.db.base import utc_now

        self.acknowledged_at = utc_now()
        self.acknowledged_by = user_id

    def resolve(self, user_id: str, notes: str | None = None, action: str | None = None) -> None:
        """Mark alert as resolved."""
        from app.db.base import utc_now

        self.is_active = False
        self.resolved_at = utc_now()
        self.resolved_by = user_id
        self.resolution_notes = notes
        self.action_taken = action

    def __repr__(self) -> str:
        return f"<MonitoringAlert {self.alert_type} severity={self.severity} active={self.is_active}>"
