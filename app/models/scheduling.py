"""Scheduling models for clinician availability and appointments.

Sprint 5: Clinician profiles, availability slots, appointment types,
and booking management with tier-based access control.
"""

from datetime import datetime, time
from enum import Enum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class ClinicalSpecialty(str, Enum):
    """Clinical specialties for matching clinicians to patients."""

    PSYCHIATRY = "psychiatry"
    PSYCHOLOGY = "psychology"
    CBT = "cbt"  # Cognitive Behavioral Therapy
    PSYCHOTHERAPY = "psychotherapy"
    COUNSELLING = "counselling"
    ADDICTION = "addiction"
    EATING_DISORDERS = "eating_disorders"
    TRAUMA = "trauma"
    CHILD_ADOLESCENT = "child_adolescent"
    GERIATRIC = "geriatric"
    CRISIS_INTERVENTION = "crisis_intervention"


class ClinicianProfile(Base, TimestampMixin, SoftDeleteMixin):
    """Extended profile for clinical staff with specialties and availability.

    Links to User model for authentication, provides clinical-specific
    attributes for scheduling and patient matching.
    """

    __tablename__ = "clinician_profiles"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    # Professional registration number (e.g., GMC, HCPC)
    registration_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    registration_body: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    # Clinical title (e.g., "Consultant Psychiatrist", "Clinical Psychologist")
    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    # Specialties as array for flexible matching
    specialties: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)),
        default=list,
        nullable=False,
    )
    # Bio for patient-facing display
    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Whether clinician accepts new patients
    accepting_new_patients: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    # Maximum appointments per day (capacity management)
    max_daily_appointments: Mapped[int] = mapped_column(
        Integer,
        default=8,
        nullable=False,
    )
    # Default appointment duration in minutes
    default_appointment_duration: Mapped[int] = mapped_column(
        Integer,
        default=50,
        nullable=False,
    )
    # Can handle RED tier emergencies
    can_handle_crisis: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", lazy="joined")
    availability_slots: Mapped[list["AvailabilitySlot"]] = relationship(
        "AvailabilitySlot",
        back_populates="clinician",
        cascade="all, delete-orphan",
    )
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment",
        back_populates="clinician",
        foreign_keys="Appointment.clinician_id",
    )

    def __repr__(self) -> str:
        return f"<ClinicianProfile {self.title}>"


class DayOfWeek(int, Enum):
    """Day of week for recurring availability."""

    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class AvailabilitySlot(Base, TimestampMixin):
    """Recurring availability slot for a clinician.

    Represents a regular weekly availability window that can be
    used to generate bookable appointment slots.
    """

    __tablename__ = "availability_slots"

    clinician_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("clinician_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_of_week: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )
    end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )
    # Whether slot is currently active
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    # Effective date range (for temporary changes)
    effective_from: Mapped[datetime | None] = mapped_column(
        Date,
        nullable=True,
    )
    effective_until: Mapped[datetime | None] = mapped_column(
        Date,
        nullable=True,
    )
    # Location (for multi-site clinics)
    location: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    # Whether this is a video consultation slot
    is_remote: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    clinician: Mapped["ClinicianProfile"] = relationship(
        "ClinicianProfile",
        back_populates="availability_slots",
    )

    def __repr__(self) -> str:
        return f"<AvailabilitySlot {self.day_of_week} {self.start_time}-{self.end_time}>"


class AppointmentType(Base, TimestampMixin, SoftDeleteMixin):
    """Type of appointment with duration and booking rules.

    Defines appointment categories with tier-based access control
    for self-booking restrictions.
    """

    __tablename__ = "appointment_types"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Duration in minutes
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        default=50,
        nullable=False,
    )
    # Buffer time after appointment (minutes)
    buffer_minutes: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
    )
    # Which tiers can self-book this type
    self_book_tiers: Mapped[list[str]] = mapped_column(
        ARRAY(String(20)),
        default=lambda: ["green", "blue"],  # GREEN/BLUE can self-book
        nullable=False,
    )
    # Required specialties for clinician matching
    required_specialties: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)),
        default=list,
        nullable=False,
    )
    # Whether video consultations are allowed
    allow_remote: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    # Whether this type is available for patient booking
    is_bookable: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    # Display order for UI
    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    # Color for calendar display
    color: Mapped[str] = mapped_column(
        String(7),  # Hex color code
        default="#3b82f6",
        nullable=False,
    )

    # Relationships
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment",
        back_populates="appointment_type",
    )

    def can_self_book(self, tier: str) -> bool:
        """Check if a patient with given tier can self-book this type."""
        return tier.lower() in [t.lower() for t in self.self_book_tiers]

    def __repr__(self) -> str:
        return f"<AppointmentType {self.code}>"


class AppointmentStatus(str, Enum):
    """Status of an appointment."""

    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


class BookingSource(str, Enum):
    """Source of the booking."""

    PATIENT_SELF_BOOK = "patient_self_book"
    STAFF_BOOKED = "staff_booked"
    SYSTEM_SCHEDULED = "system_scheduled"


class Appointment(Base, TimestampMixin, SoftDeleteMixin):
    """Scheduled appointment between patient and clinician.

    Tracks the full lifecycle from booking through completion,
    with audit trail for changes.
    """

    __tablename__ = "appointments"

    # Patient and clinician
    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clinician_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("clinician_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Related triage case (for context and compliance)
    triage_case_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("triage_cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Appointment type
    appointment_type_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("appointment_types.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Scheduling details
    scheduled_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    scheduled_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    # Actual times (for reporting)
    actual_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    actual_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # Status
    status: Mapped[AppointmentStatus] = mapped_column(
        String(30),
        default=AppointmentStatus.SCHEDULED,
        nullable=False,
        index=True,
    )
    # Booking metadata
    booking_source: Mapped[BookingSource] = mapped_column(
        String(30),
        nullable=False,
    )
    booked_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Location
    location: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    is_remote: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    video_link: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    # Notes
    patient_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    staff_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Cancellation tracking
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Reminder tracking
    reminder_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # Reschedule tracking
    reschedule_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    rescheduled_from_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    clinician: Mapped["ClinicianProfile"] = relationship(
        "ClinicianProfile",
        back_populates="appointments",
        foreign_keys=[clinician_id],
    )
    appointment_type: Mapped["AppointmentType"] = relationship(
        "AppointmentType",
        back_populates="appointments",
    )

    def __repr__(self) -> str:
        return f"<Appointment {self.id[:8]}... {self.scheduled_start} status={self.status}>"


class CancellationRequestStatus(str, Enum):
    """Status of a cancellation/reschedule request."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    AUTO_APPROVED = "auto_approved"


class CancellationRequestType(str, Enum):
    """Type of cancellation request."""

    CANCEL = "cancel"
    RESCHEDULE = "reschedule"


class CancellationRequest(Base, TimestampMixin):
    """Request for cancellation or rescheduling requiring staff review.

    Created when:
    - AMBER/RED tier patients request cancel/reschedule
    - GREEN/BLUE patients request within 24h window
    - Safety concern detected in cancellation reason

    Staff must review and approve/deny these requests.
    """

    __tablename__ = "cancellation_requests"

    # Core relationships
    appointment_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    triage_case_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("triage_cases.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Request details
    request_type: Mapped[CancellationRequestType] = mapped_column(
        String(20),
        nullable=False,
    )
    tier_at_request: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    safety_concern_flagged: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    status: Mapped[CancellationRequestStatus] = mapped_column(
        String(20),
        default=CancellationRequestStatus.PENDING,
        nullable=False,
        index=True,
    )
    within_24h: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # For reschedule requests: requested new time
    requested_new_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    requested_new_clinician_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("clinician_profiles.id", ondelete="SET NULL"),
        nullable=True,
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
    review_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    appointment: Mapped["Appointment"] = relationship(
        "Appointment",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<CancellationRequest {self.id[:8]}... type={self.request_type} status={self.status}>"


# Import for type hints
from app.models.user import User
