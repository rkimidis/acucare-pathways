"""Messaging models for notifications and communications.

Sprint 5: Message templates, delivery tracking, and provider abstraction
for SMS and email communications with patients.
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class MessageChannel(str, Enum):
    """Communication channel for messages."""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"  # Future: mobile app push notifications


class MessageTemplateType(str, Enum):
    """Type of message template."""

    # Appointment-related
    APPOINTMENT_INVITE = "appointment_invite"
    APPOINTMENT_REMINDER = "appointment_reminder"
    APPOINTMENT_CONFIRMATION = "appointment_confirmation"
    APPOINTMENT_CANCELLED = "appointment_cancelled"
    APPOINTMENT_RESCHEDULED = "appointment_rescheduled"
    # Waiting list monitoring
    CHECKIN_REQUEST = "checkin_request"
    CHECKIN_REMINDER = "checkin_reminder"
    CHECKIN_ESCALATION = "checkin_escalation"
    # Triage-related
    TRIAGE_COMPLETE = "triage_complete"
    TRIAGE_ESCALATION = "triage_escalation"
    # General
    WELCOME = "welcome"
    PASSWORD_RESET = "password_reset"
    MAGIC_LINK = "magic_link"


class MessageTemplate(Base, TimestampMixin, SoftDeleteMixin):
    """Template for system-generated messages.

    Supports variable substitution using {{variable}} syntax.
    Templates can be channel-specific for SMS vs email formatting.
    """

    __tablename__ = "message_templates"

    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    template_type: Mapped[MessageTemplateType] = mapped_column(
        String(50),
        nullable=False,
    )
    channel: Mapped[MessageChannel] = mapped_column(
        String(20),
        nullable=False,
    )
    # Template content
    subject: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,  # SMS doesn't have subject
    )
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    # HTML version for email (optional)
    html_body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Whether template is active
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    # Version for template history
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    # Metadata for variable documentation
    variables: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Relationships
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="template",
    )

    def render(self, context: dict) -> tuple[str | None, str]:
        """Render template with context variables.

        Returns (subject, body) tuple.
        """
        subject = self.subject
        body = self.body

        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            if subject:
                subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))

        return subject, body

    def render_html(self, context: dict) -> str | None:
        """Render HTML template with context variables."""
        if not self.html_body:
            return None

        html = self.html_body
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            html = html.replace(placeholder, str(value))

        return html

    def __repr__(self) -> str:
        return f"<MessageTemplate {self.code} ({self.channel})>"


class MessageStatus(str, Enum):
    """Status of a sent message."""

    PENDING = "pending"  # Queued for sending
    SENDING = "sending"  # In progress
    SENT = "sent"  # Sent to provider
    DELIVERED = "delivered"  # Confirmed delivery
    FAILED = "failed"  # Sending failed
    BOUNCED = "bounced"  # Email bounced
    REJECTED = "rejected"  # Rejected by provider
    OPENED = "opened"  # Email opened (if tracking enabled)
    CLICKED = "clicked"  # Link clicked (if tracking enabled)


class Message(Base, TimestampMixin, SoftDeleteMixin):
    """Individual message sent to a patient.

    Tracks full lifecycle from creation through delivery confirmation.
    Supports multiple channels and delivery receipt updates.
    """

    __tablename__ = "messages"

    # Recipient
    patient_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Template used (for auditing)
    template_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("message_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Message details
    channel: Mapped[MessageChannel] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    recipient_address: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    subject: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    html_body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Status tracking
    status: Mapped[MessageStatus] = mapped_column(
        String(30),
        default=MessageStatus.PENDING,
        nullable=False,
        index=True,
    )
    # Provider details
    provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    provider_message_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    # Timing
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # Error tracking
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    max_retries: Mapped[int] = mapped_column(
        Integer,
        default=3,
        nullable=False,
    )
    # Related entities for context
    appointment_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("appointments.id", ondelete="SET NULL"),
        nullable=True,
    )
    triage_case_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("triage_cases.id", ondelete="SET NULL"),
        nullable=True,
    )
    checkin_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("waiting_list_checkins.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Metadata for additional context
    message_metadata: Mapped[dict | None] = mapped_column(
        "metadata",  # Keep DB column name for compatibility
        JSON,
        nullable=True,
    )

    # Relationships
    template: Mapped["MessageTemplate"] = relationship(
        "MessageTemplate",
        back_populates="messages",
    )

    def update_status(self, new_status: MessageStatus, error: str | None = None) -> None:
        """Update message status with appropriate timestamps."""
        from app.db.base import utc_now

        self.status = new_status
        now = utc_now()

        if new_status == MessageStatus.SENT:
            self.sent_at = now
        elif new_status == MessageStatus.DELIVERED:
            self.delivered_at = now
        elif new_status == MessageStatus.OPENED:
            self.opened_at = now
        elif new_status in (MessageStatus.FAILED, MessageStatus.BOUNCED, MessageStatus.REJECTED):
            self.error_message = error

    def can_retry(self) -> bool:
        """Check if message can be retried."""
        return (
            self.status == MessageStatus.FAILED
            and self.retry_count < self.max_retries
        )

    def __repr__(self) -> str:
        return f"<Message {self.id[:8]}... {self.channel} status={self.status}>"


class DeliveryReceipt(Base, TimestampMixin):
    """Delivery receipt/webhook data from messaging providers.

    Stores raw provider callbacks for auditing and debugging.
    """

    __tablename__ = "delivery_receipts"

    message_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    provider_message_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    # Status reported by provider
    provider_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    # Mapped internal status
    mapped_status: Mapped[MessageStatus] = mapped_column(
        String(30),
        nullable=False,
    )
    # Raw webhook payload
    raw_payload: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )
    # Timestamp from provider
    provider_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # Processing details
    processed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    message: Mapped["Message"] = relationship("Message")

    def __repr__(self) -> str:
        return f"<DeliveryReceipt {self.provider} {self.provider_status}>"
