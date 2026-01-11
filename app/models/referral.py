"""Referral model for patient intake."""

from enum import Enum

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class ReferralSource(str, Enum):
    """Source of the referral."""

    GP = "gp"
    SELF = "self"
    NHS = "nhs"
    PRIVATE_HOSPITAL = "private_hospital"
    EMPLOYER = "employer"
    INSURANCE = "insurance"
    OTHER = "other"


class ReferralStatus(str, Enum):
    """Status of the referral."""

    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WAITLISTED = "waitlisted"
    CONVERTED = "converted"  # Converted to triage case


class Referral(Base, TimestampMixin, SoftDeleteMixin):
    """Referral model for tracking patient intake from various sources.

    Referrals represent the initial contact before a patient becomes
    a triage case. They capture source information and are converted
    to triage cases upon acceptance.
    """

    __tablename__ = "referrals"

    # Patient reference (optional - may not exist yet)
    patient_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Referral details
    source: Mapped[ReferralSource] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    status: Mapped[ReferralStatus] = mapped_column(
        String(50),
        default=ReferralStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Patient contact info (before patient record exists)
    patient_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    patient_first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    patient_last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    patient_phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    patient_dob: Mapped[str | None] = mapped_column(
        String(20),  # ISO date format
        nullable=True,
    )

    # Referrer information
    referrer_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    referrer_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    referrer_phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    referrer_organization: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Clinical information
    presenting_complaint: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    urgency_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    clinical_history: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Additional metadata
    referral_metadata: Mapped[dict | None] = mapped_column(
        "metadata",  # Keep DB column name for compatibility
        JSON,
        nullable=True,
    )

    # Processing
    reviewed_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Converted triage case reference
    triage_case_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("triage_cases.id", ondelete="SET NULL"),
        nullable=True,
    )

    @property
    def patient_full_name(self) -> str:
        """Return patient's full name from referral data."""
        return f"{self.patient_first_name} {self.patient_last_name}"

    def __repr__(self) -> str:
        return f"<Referral {self.id[:8]}... {self.source} status={self.status}>"
