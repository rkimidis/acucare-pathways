"""Patient model and magic link authentication."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class Patient(Base, TimestampMixin, SoftDeleteMixin):
    """Patient model.

    Represents a patient registered with the clinic. Contains minimal
    identifying information with clinical data stored separately.
    """

    __tablename__ = "patients"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    date_of_birth: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    nhs_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        unique=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Consent tracking
    consent_given_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    privacy_policy_version: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    # Relationships
    magic_links: Mapped[list["PatientMagicLink"]] = relationship(
        "PatientMagicLink",
        back_populates="patient",
        lazy="selectin",
    )

    @property
    def full_name(self) -> str:
        """Return patient's full name."""
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<Patient {self.email}>"


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
