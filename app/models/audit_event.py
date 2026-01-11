"""Append-only audit event model for compliance and traceability."""

from enum import Enum

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ActorType(str, Enum):
    """Type of actor performing the action."""

    SYSTEM = "system"
    STAFF = "staff"
    PATIENT = "patient"


class AuditEvent(Base, TimestampMixin):
    """Append-only audit event for compliance tracking.

    IMPORTANT: This model intentionally has no update or delete
    operations. All events are immutable once created.

    Used for:
    - CQC compliance (Safe/Well-led)
    - UK GDPR audit trail
    - Security monitoring
    - Clinical decision audit
    """

    __tablename__ = "audit_events"

    # Actor information
    actor_type: Mapped[ActorType] = mapped_column(
        String(50),
        nullable=False,
    )
    actor_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,  # Null for system actions
    )
    actor_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Action performed
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    action_category: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,  # e.g., "auth", "triage", "clinical", "admin"
    )

    # Entity affected
    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    entity_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
        index=True,
    )

    # Additional context
    event_metadata: Mapped[dict | None] = mapped_column(
        "metadata",  # Keep DB column name for compatibility
        JSON,
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Request context
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # Supports IPv6
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    request_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<AuditEvent {self.action} by {self.actor_type}:{self.actor_id} "
            f"on {self.entity_type}:{self.entity_id}>"
        )
