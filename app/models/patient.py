"""Patient model and related entities for UK psychiatric clinic.

Includes:
- Patient: canonical identity + contact + demographics
- PatientAddress: address history
- PatientContact: emergency contact, GP, next-of-kin
- PatientPreferences: communication and accessibility preferences
- PatientClinicalProfile: structured clinical context (non-diagnostic)
- PatientIdentifier: NHS number and other identifiers
- PatientRecordUpdate: provenance log for staff edits
- PatientMagicLink: passwordless authentication
"""

from datetime import date, datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BaseNoId, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.consent import Consent
    from app.models.questionnaire import QuestionnaireResponse
    from app.models.triage_case import TriageCase


# =============================================================================
# Enums
# =============================================================================


class SexAtBirth(str, Enum):
    """Sex assigned at birth options."""
    MALE = "male"
    FEMALE = "female"
    INTERSEX = "intersex"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class ContactMethod(str, Enum):
    """Preferred contact method options."""
    EMAIL = "email"
    SMS = "sms"
    PHONE = "phone"


class AddressType(str, Enum):
    """Address type options."""
    HOME = "home"
    CURRENT = "current"
    BILLING = "billing"
    OTHER = "other"


class ContactType(str, Enum):
    """Contact type options (GP, emergency, etc.)."""
    EMERGENCY = "emergency"
    GP = "gp"
    NEXT_OF_KIN = "next_of_kin"
    OTHER = "other"


class AppointmentFormatPreference(str, Enum):
    """Appointment format preference options."""
    IN_PERSON = "in_person"
    VIDEO = "video"
    PHONE = "phone"
    NO_PREFERENCE = "no_preference"


class PreviousTreatment(str, Enum):
    """Previous mental health treatment options."""
    NONE = "none"
    YES_UNKNOWN = "yes_unknown"
    YES_TALKING_THERAPY = "yes_talking_therapy"
    YES_PSYCHIATRY = "yes_psychiatry"
    YES_INPATIENT = "yes_inpatient"


class SubstanceUseLevel(str, Enum):
    """Substance use level options."""
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    UNKNOWN = "unknown"


class IdentifierType(str, Enum):
    """Identifier type options."""
    NHS_NUMBER = "nhs_number"
    PRIVATE_ID = "private_id"
    OTHER = "other"


class RecordUpdateSource(str, Enum):
    """Source of record update."""
    INTAKE = "intake"
    STAFF_EDIT = "staff_edit"
    IMPORT = "import"
    SYSTEM = "system"


class RecordUpdateActorType(str, Enum):
    """Actor type for record updates."""
    STAFF = "staff"
    SYSTEM = "system"


# =============================================================================
# Patient Model
# =============================================================================


class Patient(Base, TimestampMixin, SoftDeleteMixin):
    """Patient model.

    Represents a patient registered with the clinic. This is the canonical
    record for patient identity, contact information, and demographics.
    Clinical data and questionnaire responses are stored separately.
    """

    __tablename__ = "patients"

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    preferred_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    date_of_birth: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    sex_at_birth: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    gender_identity: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    ethnicity: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    preferred_language: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    interpreter_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # -------------------------------------------------------------------------
    # Contact
    # -------------------------------------------------------------------------
    phone_e164: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    preferred_contact_method: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    can_leave_voicemail: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    consent_to_sms: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    consent_to_email: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # -------------------------------------------------------------------------
    # Location
    # -------------------------------------------------------------------------
    postcode: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    country: Mapped[str | None] = mapped_column(
        String(5),
        nullable=True,
        default="GB",
    )

    # -------------------------------------------------------------------------
    # Safeguarding / Practical
    # -------------------------------------------------------------------------
    has_dependents: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    is_pregnant_or_postnatal: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    reasonable_adjustments_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # -------------------------------------------------------------------------
    # Status flags
    # -------------------------------------------------------------------------
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    is_dummy: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # -------------------------------------------------------------------------
    # Behavior tracking (for booking policy enforcement)
    # -------------------------------------------------------------------------
    cancellation_count_90d: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    no_show_count_90d: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_behavior_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # -------------------------------------------------------------------------
    # Legacy fields (kept for backward compatibility)
    # -------------------------------------------------------------------------
    nhs_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        unique=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # -------------------------------------------------------------------------
    # Consent tracking
    # -------------------------------------------------------------------------
    consent_given_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    privacy_policy_version: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # -------------------------------------------------------------------------
    # Linked contacts (FK to patient_contacts)
    # -------------------------------------------------------------------------
    primary_gp_contact_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patient_contacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    emergency_contact_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patient_contacts.id", ondelete="SET NULL"),
        nullable=True,
    )

    # -------------------------------------------------------------------------
    # Relationships
    # -------------------------------------------------------------------------
    magic_links: Mapped[list["PatientMagicLink"]] = relationship(
        "PatientMagicLink",
        back_populates="patient",
        lazy="selectin",
    )
    addresses: Mapped[list["PatientAddress"]] = relationship(
        "PatientAddress",
        back_populates="patient",
        lazy="selectin",
    )
    contacts: Mapped[list["PatientContact"]] = relationship(
        "PatientContact",
        back_populates="patient",
        foreign_keys="PatientContact.patient_id",
        lazy="selectin",
    )
    preferences: Mapped["PatientPreferences | None"] = relationship(
        "PatientPreferences",
        back_populates="patient",
        uselist=False,
        lazy="selectin",
    )
    clinical_profile: Mapped["PatientClinicalProfile | None"] = relationship(
        "PatientClinicalProfile",
        back_populates="patient",
        uselist=False,
        lazy="selectin",
    )
    identifiers: Mapped[list["PatientIdentifier"]] = relationship(
        "PatientIdentifier",
        back_populates="patient",
        lazy="selectin",
    )
    record_updates: Mapped[list["PatientRecordUpdate"]] = relationship(
        "PatientRecordUpdate",
        back_populates="patient",
        lazy="noload",
    )

    # Linked contact relationships
    primary_gp_contact: Mapped["PatientContact | None"] = relationship(
        "PatientContact",
        foreign_keys=[primary_gp_contact_id],
        lazy="selectin",
    )
    emergency_contact: Mapped["PatientContact | None"] = relationship(
        "PatientContact",
        foreign_keys=[emergency_contact_id],
        lazy="selectin",
    )

    @property
    def full_name(self) -> str:
        """Return patient's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def display_name(self) -> str:
        """Return preferred name if set, otherwise full name."""
        if self.preferred_name:
            return self.preferred_name
        return self.full_name

    def __repr__(self) -> str:
        return f"<Patient {self.email}>"


# =============================================================================
# Patient Address
# =============================================================================


class PatientAddress(Base, TimestampMixin):
    """Patient address record.

    Stores address history with type classification (home, current, etc.).
    """

    __tablename__ = "patient_addresses"

    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    line1: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    line2: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    county: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    postcode: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    country: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        default="GB",
    )
    valid_from: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    valid_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="addresses",
    )

    def __repr__(self) -> str:
        return f"<PatientAddress {self.type} {self.postcode}>"


# =============================================================================
# Patient Contact (GP, Emergency, Next-of-Kin)
# =============================================================================


class PatientContact(Base, TimestampMixin):
    """Patient contact record (GP, emergency contact, next-of-kin, etc.)."""

    __tablename__ = "patient_contacts"

    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    contact_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    relationship_to_patient: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    phone_e164: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    organisation: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="contacts",
        foreign_keys=[patient_id],
    )

    def __repr__(self) -> str:
        return f"<PatientContact {self.contact_type} {self.name}>"


# =============================================================================
# Patient Preferences
# =============================================================================


class PatientPreferences(BaseNoId, TimestampMixin):
    """Patient communication and accessibility preferences.

    One-to-one with Patient (patient_id is the primary key).
    """

    __tablename__ = "patient_preferences"

    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    communication_channel_preference: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    appointment_format_preference: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    requires_accessibility_support: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    accessibility_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    reasonable_adjustments_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="preferences",
    )

    def __repr__(self) -> str:
        return f"<PatientPreferences {self.patient_id}>"


# =============================================================================
# Patient Clinical Profile
# =============================================================================


class PatientClinicalProfile(BaseNoId, TimestampMixin):
    """Structured clinical context (non-diagnostic).

    One-to-one with Patient (patient_id is the primary key).
    Contains essential clinical information for triage and care planning.
    """

    __tablename__ = "patient_clinical_profile"

    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    presenting_problem: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    previous_mental_health_treatment: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    current_psych_medication: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    current_medication_list: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    physical_health_conditions: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    physical_health_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    substance_use_level: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    neurodevelopmental_needs: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    risk_notes_staff_only: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="clinical_profile",
    )

    def __repr__(self) -> str:
        return f"<PatientClinicalProfile {self.patient_id}>"


# =============================================================================
# Patient Identifier (NHS Number, etc.)
# =============================================================================


class PatientIdentifier(Base, TimestampMixin):
    """Patient identifier record (NHS number, private ID, etc.).

    Allows multiple identifiers per patient with verification status.
    """

    __tablename__ = "patient_identifiers"

    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    id_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    id_value: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="identifiers",
    )

    def __repr__(self) -> str:
        return f"<PatientIdentifier {self.id_type}:{self.id_value[:4]}...>"


# =============================================================================
# Patient Record Update (Provenance Ledger)
# =============================================================================


class PatientRecordUpdate(Base):
    """Provenance log for patient record edits.

    Human-readable change log for staff edits, separate from general audit.
    """

    __tablename__ = "patient_record_updates"

    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    actor_user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )
    actor_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )
    changed_fields: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="record_updates",
    )

    def __repr__(self) -> str:
        return f"<PatientRecordUpdate {self.patient_id} {self.source}>"


# =============================================================================
# Patient Magic Link (Authentication)
# =============================================================================


class PatientMagicLink(Base, TimestampMixin):
    """Magic link for passwordless patient authentication.

    Tokens are single-use and expire based on TTL settings.
    """

    __tablename__ = "patient_magic_links"

    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
    )
    token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Security tracking
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Relationships
    patient: Mapped["Patient"] = relationship(
        "Patient",
        back_populates="magic_links",
    )

    @property
    def is_expired(self) -> bool:
        """Check if the magic link has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the magic link is valid (not used and not expired)."""
        return not self.is_used and not self.is_expired

    def __repr__(self) -> str:
        return f"<PatientMagicLink {self.token[:8]}... expired={self.is_expired}>"
