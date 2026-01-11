"""Messaging service for patient communications.

Sprint 5: Handles message sending, template rendering, provider abstraction,
and delivery receipt processing for SMS and email.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Sequence
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utc_now
from app.models.messaging import (
    DeliveryReceipt,
    Message,
    MessageChannel,
    MessageStatus,
    MessageTemplate,
    MessageTemplateType,
)
from app.models.patient import Patient

logger = logging.getLogger(__name__)


class MessageProviderError(Exception):
    """Base exception for messaging provider errors."""

    pass


class MessageProvider(ABC):
    """Abstract base class for messaging providers."""

    @abstractmethod
    async def send(
        self,
        recipient: str,
        subject: str | None,
        body: str,
        html_body: str | None = None,
        **kwargs: Any,
    ) -> tuple[str, dict]:
        """Send a message and return (provider_message_id, metadata).

        Raises MessageProviderError on failure.
        """
        pass

    @abstractmethod
    def map_status(self, provider_status: str) -> MessageStatus:
        """Map provider-specific status to internal MessageStatus."""
        pass


class SMSProvider(MessageProvider):
    """SMS provider abstraction for UK SMS gateways.

    Supports Twilio, MessageBird, or other SMS providers.
    """

    def __init__(
        self,
        provider_name: str = "twilio",
        account_sid: str = "",
        auth_token: str = "",
        from_number: str = "",
    ):
        self.provider_name = provider_name
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

    async def send(
        self,
        recipient: str,
        subject: str | None,
        body: str,
        html_body: str | None = None,
        **kwargs: Any,
    ) -> tuple[str, dict]:
        """Send SMS message."""
        # In production, this would call the actual SMS API
        # For now, we simulate the send
        logger.info(f"Sending SMS to {recipient}: {body[:50]}...")

        # Simulate provider response
        message_id = f"sms_{uuid4().hex[:16]}"

        return message_id, {
            "provider": self.provider_name,
            "from": self.from_number,
            "to": recipient,
            "segments": len(body) // 160 + 1,
        }

    def map_status(self, provider_status: str) -> MessageStatus:
        """Map Twilio-style status to internal status."""
        status_map = {
            "queued": MessageStatus.PENDING,
            "sending": MessageStatus.SENDING,
            "sent": MessageStatus.SENT,
            "delivered": MessageStatus.DELIVERED,
            "undelivered": MessageStatus.FAILED,
            "failed": MessageStatus.FAILED,
        }
        return status_map.get(provider_status.lower(), MessageStatus.PENDING)


class EmailProvider(MessageProvider):
    """Email provider abstraction.

    Supports SMTP, SendGrid, AWS SES, or other email providers.
    """

    def __init__(
        self,
        provider_name: str = "smtp",
        smtp_host: str = "",
        smtp_port: int = 587,
        smtp_user: str = "",
        smtp_password: str = "",
        from_email: str = "",
        from_name: str = "AcuCare Pathways",
    ):
        self.provider_name = provider_name
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.from_name = from_name

    async def send(
        self,
        recipient: str,
        subject: str | None,
        body: str,
        html_body: str | None = None,
        **kwargs: Any,
    ) -> tuple[str, dict]:
        """Send email message."""
        # In production, this would send via SMTP or API
        logger.info(f"Sending email to {recipient}: {subject}")

        # Simulate provider response
        message_id = f"email_{uuid4().hex[:16]}"

        return message_id, {
            "provider": self.provider_name,
            "from": f"{self.from_name} <{self.from_email}>",
            "to": recipient,
            "has_html": html_body is not None,
        }

    def map_status(self, provider_status: str) -> MessageStatus:
        """Map email provider status to internal status."""
        status_map = {
            "queued": MessageStatus.PENDING,
            "sent": MessageStatus.SENT,
            "delivered": MessageStatus.DELIVERED,
            "opened": MessageStatus.OPENED,
            "clicked": MessageStatus.CLICKED,
            "bounced": MessageStatus.BOUNCED,
            "dropped": MessageStatus.REJECTED,
            "failed": MessageStatus.FAILED,
        }
        return status_map.get(provider_status.lower(), MessageStatus.PENDING)


class MessagingService:
    """Service for managing patient communications."""

    def __init__(
        self,
        session: AsyncSession,
        sms_provider: MessageProvider | None = None,
        email_provider: MessageProvider | None = None,
    ):
        self.session = session
        self.sms_provider = sms_provider or SMSProvider()
        self.email_provider = email_provider or EmailProvider()

    def _get_provider(self, channel: MessageChannel) -> MessageProvider:
        """Get the appropriate provider for a channel."""
        if channel == MessageChannel.SMS:
            return self.sms_provider
        elif channel == MessageChannel.EMAIL:
            return self.email_provider
        else:
            raise ValueError(f"Unsupported channel: {channel}")

    async def get_template(
        self,
        template_type: MessageTemplateType,
        channel: MessageChannel,
    ) -> MessageTemplate | None:
        """Get active template for a type and channel."""
        result = await self.session.execute(
            select(MessageTemplate).where(
                MessageTemplate.template_type == template_type,
                MessageTemplate.channel == channel,
                MessageTemplate.is_active == True,
                MessageTemplate.is_deleted == False,
            ).order_by(MessageTemplate.version.desc())
        )
        return result.scalar_one_or_none()

    async def get_templates(
        self,
        template_type: MessageTemplateType | None = None,
    ) -> Sequence[MessageTemplate]:
        """Get templates, optionally filtered by type."""
        query = select(MessageTemplate).where(
            MessageTemplate.is_active == True,
            MessageTemplate.is_deleted == False,
        )

        if template_type:
            query = query.where(MessageTemplate.template_type == template_type)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def create_template(
        self,
        code: str,
        template_type: MessageTemplateType,
        channel: MessageChannel,
        body: str,
        subject: str | None = None,
        html_body: str | None = None,
        variables: dict | None = None,
    ) -> MessageTemplate:
        """Create a new message template."""
        template = MessageTemplate(
            id=str(uuid4()),
            code=code,
            template_type=template_type,
            channel=channel,
            subject=subject,
            body=body,
            html_body=html_body,
            variables=variables,
        )

        self.session.add(template)
        await self.session.commit()
        await self.session.refresh(template)

        return template

    async def send_message(
        self,
        patient_id: str,
        channel: MessageChannel,
        recipient_address: str,
        body: str,
        subject: str | None = None,
        html_body: str | None = None,
        template_id: str | None = None,
        appointment_id: str | None = None,
        triage_case_id: str | None = None,
        checkin_id: str | None = None,
        scheduled_at: datetime | None = None,
        metadata: dict | None = None,
    ) -> Message:
        """Send a message to a patient.

        If scheduled_at is provided, the message will be queued for later sending.
        """
        # Create message record
        message = Message(
            id=str(uuid4()),
            patient_id=patient_id,
            template_id=template_id,
            channel=channel,
            recipient_address=recipient_address,
            subject=subject,
            body=body,
            html_body=html_body,
            appointment_id=appointment_id,
            triage_case_id=triage_case_id,
            checkin_id=checkin_id,
            scheduled_at=scheduled_at,
            metadata=metadata,
            status=MessageStatus.PENDING,
        )

        self.session.add(message)

        # If not scheduled, send immediately
        if not scheduled_at or scheduled_at <= utc_now():
            try:
                provider = self._get_provider(channel)
                provider_id, provider_meta = await provider.send(
                    recipient=recipient_address,
                    subject=subject,
                    body=body,
                    html_body=html_body,
                )

                message.provider = provider_meta.get("provider", "unknown")
                message.provider_message_id = provider_id
                message.status = MessageStatus.SENT
                message.sent_at = utc_now()

                if metadata:
                    message.message_metadata = {**(message.message_metadata or {}), **provider_meta}
                else:
                    message.message_metadata = provider_meta

            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                message.status = MessageStatus.FAILED
                message.error_message = str(e)

        await self.session.commit()
        await self.session.refresh(message)

        return message

    async def send_from_template(
        self,
        patient_id: str,
        template_type: MessageTemplateType,
        channel: MessageChannel,
        recipient_address: str,
        context: dict,
        appointment_id: str | None = None,
        triage_case_id: str | None = None,
        checkin_id: str | None = None,
        scheduled_at: datetime | None = None,
    ) -> Message:
        """Send a message using a template with variable substitution."""
        template = await self.get_template(template_type, channel)

        if not template:
            raise ValueError(f"No active template found for {template_type} ({channel})")

        subject, body = template.render(context)
        html_body = template.render_html(context)

        return await self.send_message(
            patient_id=patient_id,
            channel=channel,
            recipient_address=recipient_address,
            body=body,
            subject=subject,
            html_body=html_body,
            template_id=template.id,
            appointment_id=appointment_id,
            triage_case_id=triage_case_id,
            checkin_id=checkin_id,
            scheduled_at=scheduled_at,
            metadata={"template_code": template.code, "context_keys": list(context.keys())},
        )

    async def process_delivery_receipt(
        self,
        provider: str,
        provider_message_id: str,
        provider_status: str,
        raw_payload: dict,
        provider_timestamp: datetime | None = None,
    ) -> DeliveryReceipt | None:
        """Process a delivery receipt webhook from a messaging provider.

        Updates the message status and creates a receipt record.
        """
        # Find the message
        result = await self.session.execute(
            select(Message).where(
                Message.provider_message_id == provider_message_id,
            )
        )
        message = result.scalar_one_or_none()

        if not message:
            logger.warning(f"Message not found for provider ID: {provider_message_id}")
            return None

        # Get provider and map status
        msg_provider = self._get_provider(message.channel)
        mapped_status = msg_provider.map_status(provider_status)

        # Create delivery receipt
        receipt = DeliveryReceipt(
            id=str(uuid4()),
            message_id=message.id,
            provider=provider,
            provider_message_id=provider_message_id,
            provider_status=provider_status,
            mapped_status=mapped_status,
            raw_payload=raw_payload,
            provider_timestamp=provider_timestamp,
            processed=True,
            processed_at=utc_now(),
        )

        self.session.add(receipt)

        # Update message status
        message.update_status(mapped_status)

        await self.session.commit()
        await self.session.refresh(receipt)

        logger.info(
            f"Processed delivery receipt: message={message.id[:8]}, "
            f"status={provider_status} -> {mapped_status}"
        )

        return receipt

    async def get_message(self, message_id: str) -> Message | None:
        """Get a message by ID."""
        result = await self.session.execute(
            select(Message).where(
                Message.id == message_id,
                Message.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def get_patient_messages(
        self,
        patient_id: str,
        channel: MessageChannel | None = None,
        limit: int = 50,
    ) -> Sequence[Message]:
        """Get messages for a patient."""
        query = select(Message).where(
            Message.patient_id == patient_id,
            Message.is_deleted == False,
        )

        if channel:
            query = query.where(Message.channel == channel)

        query = query.order_by(Message.created_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def retry_failed_message(self, message_id: str) -> Message | None:
        """Retry sending a failed message."""
        message = await self.get_message(message_id)

        if not message:
            return None

        if not message.can_retry():
            logger.warning(f"Message {message_id} cannot be retried")
            return message

        message.retry_count += 1
        message.status = MessageStatus.PENDING

        try:
            provider = self._get_provider(message.channel)
            provider_id, provider_meta = await provider.send(
                recipient=message.recipient_address,
                subject=message.subject,
                body=message.body,
                html_body=message.html_body,
            )

            message.provider_message_id = provider_id
            message.status = MessageStatus.SENT
            message.sent_at = utc_now()
            message.error_message = None

        except Exception as e:
            logger.error(f"Retry failed for message {message_id}: {e}")
            message.status = MessageStatus.FAILED
            message.error_message = str(e)

        await self.session.commit()
        await self.session.refresh(message)

        return message

    async def get_pending_scheduled_messages(self) -> Sequence[Message]:
        """Get messages scheduled to be sent now."""
        now = utc_now()

        result = await self.session.execute(
            select(Message).where(
                Message.status == MessageStatus.PENDING,
                Message.scheduled_at.isnot(None),
                Message.scheduled_at <= now,
                Message.is_deleted == False,
            )
        )
        return result.scalars().all()
