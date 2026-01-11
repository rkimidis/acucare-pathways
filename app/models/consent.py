"""Consent model for tracking patient consent."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Consent(Base, TimestampMixin):
    """Patient consent record.

    Tracks explicit consent given by patients for various purposes.
    Consent records are immutable - new records are created for updates.
    """

    __tablename__ = "consents"

    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Version of consent form/policy patient agreed to
    consent_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    # Communication channels patient consented to (email, sms, phone, etc.)
    channels: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    # Timestamp when consent was explicitly given
    agreed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    # IP address for audit purposes
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )
    # User agent for audit purposes
    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    # Specific consent items checked (e.g., {"data_processing": true, "marketing": false})
    consent_items: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    def __repr__(self) -> str:
        return f"<Consent patient={self.patient_id[:8]}... v{self.consent_version}>"
