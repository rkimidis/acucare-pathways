"""Tests for messaging service.

Sprint 5 tests covering:
- Delivery receipt updates message status
- Message template rendering
- Provider abstraction
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.messaging import (
    DeliveryReceipt,
    Message,
    MessageChannel,
    MessageStatus,
    MessageTemplate,
    MessageTemplateType,
)
from app.services.messaging import (
    MessagingService,
    SMSProvider,
    EmailProvider,
)


class TestDeliveryReceiptProcessing:
    """Tests that delivery receipts update message status."""

    @pytest.mark.asyncio
    async def test_delivery_receipt_updates_message_status(self) -> None:
        """Processing delivery receipt updates the message status."""
        mock_session = AsyncMock()

        # Mock existing message
        mock_message = MagicMock()
        mock_message.id = "message-123"
        mock_message.channel = MessageChannel.SMS
        mock_message.status = MessageStatus.SENT

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_message))
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        service = MessagingService(mock_session)

        receipt = await service.process_delivery_receipt(
            provider="twilio",
            provider_message_id="sms_abc123",
            provider_status="delivered",
            raw_payload={"MessageSid": "sms_abc123", "MessageStatus": "delivered"},
            provider_timestamp=datetime.now(timezone.utc),
        )

        # Verify message status was updated
        mock_message.update_status.assert_called_once_with(MessageStatus.DELIVERED)

        # Verify receipt was created
        assert mock_session.add.called

    @pytest.mark.asyncio
    async def test_delivery_receipt_handles_failure(self) -> None:
        """Delivery receipt correctly handles failure status."""
        mock_session = AsyncMock()

        mock_message = MagicMock()
        mock_message.id = "message-456"
        mock_message.channel = MessageChannel.SMS
        mock_message.status = MessageStatus.SENT

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_message))
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        service = MessagingService(mock_session)

        receipt = await service.process_delivery_receipt(
            provider="twilio",
            provider_message_id="sms_def456",
            provider_status="failed",
            raw_payload={"MessageSid": "sms_def456", "MessageStatus": "failed"},
        )

        # Verify message status was updated to FAILED
        mock_message.update_status.assert_called_once_with(MessageStatus.FAILED)

    @pytest.mark.asyncio
    async def test_delivery_receipt_returns_none_for_unknown_message(self) -> None:
        """Delivery receipt returns None if message not found."""
        mock_session = AsyncMock()

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        service = MessagingService(mock_session)

        receipt = await service.process_delivery_receipt(
            provider="twilio",
            provider_message_id="unknown_message",
            provider_status="delivered",
            raw_payload={},
        )

        assert receipt is None

    @pytest.mark.asyncio
    async def test_email_delivery_receipt_with_open_tracking(self) -> None:
        """Email delivery receipt correctly handles opened status."""
        mock_session = AsyncMock()

        mock_message = MagicMock()
        mock_message.id = "message-789"
        mock_message.channel = MessageChannel.EMAIL
        mock_message.status = MessageStatus.DELIVERED

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_message))
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        service = MessagingService(mock_session)

        receipt = await service.process_delivery_receipt(
            provider="sendgrid",
            provider_message_id="email_abc123",
            provider_status="opened",
            raw_payload={"event": "opened", "sg_message_id": "email_abc123"},
        )

        # Verify message status was updated to OPENED
        mock_message.update_status.assert_called_once_with(MessageStatus.OPENED)


class TestProviderStatusMapping:
    """Tests for provider status mapping."""

    def test_sms_provider_maps_delivered(self) -> None:
        """SMS provider correctly maps 'delivered' status."""
        provider = SMSProvider()
        status = provider.map_status("delivered")
        assert status == MessageStatus.DELIVERED

    def test_sms_provider_maps_failed(self) -> None:
        """SMS provider correctly maps failure statuses."""
        provider = SMSProvider()

        assert provider.map_status("failed") == MessageStatus.FAILED
        assert provider.map_status("undelivered") == MessageStatus.FAILED

    def test_sms_provider_maps_queued(self) -> None:
        """SMS provider correctly maps intermediate statuses."""
        provider = SMSProvider()

        assert provider.map_status("queued") == MessageStatus.PENDING
        assert provider.map_status("sending") == MessageStatus.SENDING
        assert provider.map_status("sent") == MessageStatus.SENT

    def test_email_provider_maps_bounced(self) -> None:
        """Email provider correctly maps bounced status."""
        provider = EmailProvider()
        status = provider.map_status("bounced")
        assert status == MessageStatus.BOUNCED

    def test_email_provider_maps_opened(self) -> None:
        """Email provider correctly maps opened status."""
        provider = EmailProvider()
        status = provider.map_status("opened")
        assert status == MessageStatus.OPENED

    def test_email_provider_maps_clicked(self) -> None:
        """Email provider correctly maps clicked status."""
        provider = EmailProvider()
        status = provider.map_status("clicked")
        assert status == MessageStatus.CLICKED

    def test_provider_handles_unknown_status(self) -> None:
        """Providers return PENDING for unknown statuses."""
        sms_provider = SMSProvider()
        email_provider = EmailProvider()

        assert sms_provider.map_status("unknown_status") == MessageStatus.PENDING
        assert email_provider.map_status("unknown_status") == MessageStatus.PENDING


class TestMessageTemplateRendering:
    """Tests for message template rendering."""

    def test_template_renders_variables(self) -> None:
        """Template correctly substitutes variables."""
        template = MessageTemplate(
            id="template-123",
            code="APPOINTMENT_REMINDER",
            template_type=MessageTemplateType.APPOINTMENT_REMINDER,
            channel=MessageChannel.SMS,
            subject=None,
            body="Hi {{patient_name}}, your appointment is on {{date}} at {{time}}.",
        )

        subject, body = template.render({
            "patient_name": "John",
            "date": "Monday 15th",
            "time": "10:00 AM",
        })

        assert subject is None
        assert "John" in body
        assert "Monday 15th" in body
        assert "10:00 AM" in body
        assert "{{" not in body

    def test_template_renders_subject_for_email(self) -> None:
        """Email template renders both subject and body."""
        template = MessageTemplate(
            id="template-456",
            code="APPOINTMENT_REMINDER",
            template_type=MessageTemplateType.APPOINTMENT_REMINDER,
            channel=MessageChannel.EMAIL,
            subject="Reminder: Your appointment on {{date}}",
            body="Dear {{patient_name}},\n\nThis is a reminder about your appointment.",
        )

        subject, body = template.render({
            "patient_name": "Jane",
            "date": "Tuesday 16th",
        })

        assert "Tuesday 16th" in subject
        assert "Jane" in body

    def test_template_renders_html_body(self) -> None:
        """Template correctly renders HTML body."""
        template = MessageTemplate(
            id="template-789",
            code="WELCOME",
            template_type=MessageTemplateType.WELCOME,
            channel=MessageChannel.EMAIL,
            subject="Welcome to AcuCare",
            body="Welcome, {{patient_name}}!",
            html_body="<h1>Welcome, {{patient_name}}!</h1><p>We're glad you're here.</p>",
        )

        html = template.render_html({"patient_name": "Bob"})

        assert html is not None
        assert "Bob" in html
        assert "<h1>" in html

    def test_template_returns_none_for_missing_html(self) -> None:
        """Template returns None if no HTML body."""
        template = MessageTemplate(
            id="template-abc",
            code="SMS_ONLY",
            template_type=MessageTemplateType.APPOINTMENT_REMINDER,
            channel=MessageChannel.SMS,
            body="Your appointment reminder.",
            html_body=None,
        )

        html = template.render_html({})
        assert html is None


class TestMessageStatusUpdate:
    """Tests for message status update method."""

    def test_update_status_sets_sent_timestamp(self) -> None:
        """Updating to SENT sets sent_at timestamp."""
        message = Message(
            id="msg-123",
            patient_id="patient-123",
            channel=MessageChannel.SMS,
            recipient_address="+447123456789",
            body="Test message",
            status=MessageStatus.PENDING,
        )

        message.update_status(MessageStatus.SENT)

        assert message.status == MessageStatus.SENT
        assert message.sent_at is not None

    def test_update_status_sets_delivered_timestamp(self) -> None:
        """Updating to DELIVERED sets delivered_at timestamp."""
        message = Message(
            id="msg-456",
            patient_id="patient-456",
            channel=MessageChannel.EMAIL,
            recipient_address="test@example.com",
            body="Test message",
            status=MessageStatus.SENT,
        )

        message.update_status(MessageStatus.DELIVERED)

        assert message.status == MessageStatus.DELIVERED
        assert message.delivered_at is not None

    def test_update_status_sets_error_on_failure(self) -> None:
        """Updating to FAILED stores error message."""
        message = Message(
            id="msg-789",
            patient_id="patient-789",
            channel=MessageChannel.SMS,
            recipient_address="+447987654321",
            body="Test message",
            status=MessageStatus.SENDING,
        )

        message.update_status(MessageStatus.FAILED, error="Invalid phone number")

        assert message.status == MessageStatus.FAILED
        assert message.error_message == "Invalid phone number"

    def test_can_retry_checks_conditions(self) -> None:
        """can_retry correctly checks retry conditions."""
        message = Message(
            id="msg-abc",
            patient_id="patient-abc",
            channel=MessageChannel.SMS,
            recipient_address="+447111222333",
            body="Test message",
            status=MessageStatus.FAILED,
            retry_count=0,
            max_retries=3,
        )

        assert message.can_retry() is True

        # Exhaust retries
        message.retry_count = 3
        assert message.can_retry() is False

        # Non-failed status
        message.retry_count = 0
        message.status = MessageStatus.DELIVERED
        assert message.can_retry() is False
