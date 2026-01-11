"""Messaging API endpoints for patient communications.

Sprint 5: Message sending, template management, and delivery webhooks.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentPatient,
    CurrentUser,
    DbSession,
    require_permissions,
)
from app.models.messaging import MessageChannel, MessageTemplateType
from app.services.intake_recovery import IntakeRecoveryService
from app.services.messaging import MessagingService
from app.services.rbac import Permission

router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================


class MessageTemplateResponse(BaseModel):
    """Message template response."""

    id: str
    code: str
    template_type: str
    channel: str
    subject: str | None
    body: str
    is_active: bool
    version: int
    variables: dict | None

    class Config:
        from_attributes = True


class CreateTemplateRequest(BaseModel):
    """Request to create a message template."""

    code: str = Field(max_length=50)
    template_type: str
    channel: str
    subject: str | None = Field(None, max_length=255)
    body: str
    html_body: str | None = None
    variables: dict | None = None


class MessageResponse(BaseModel):
    """Message response."""

    id: str
    patient_id: str
    channel: str
    recipient_address: str
    subject: str | None
    status: str
    provider: str | None
    scheduled_at: datetime | None
    sent_at: datetime | None
    delivered_at: datetime | None
    error_message: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class SendMessageRequest(BaseModel):
    """Request to send a message."""

    patient_id: str
    channel: str
    recipient_address: str
    body: str
    subject: str | None = None
    html_body: str | None = None
    template_id: str | None = None
    appointment_id: str | None = None
    triage_case_id: str | None = None
    scheduled_at: datetime | None = None


class SendFromTemplateRequest(BaseModel):
    """Request to send a message from a template."""

    patient_id: str
    template_type: str
    channel: str
    recipient_address: str
    context: dict
    appointment_id: str | None = None
    triage_case_id: str | None = None
    checkin_id: str | None = None
    scheduled_at: datetime | None = None


class DeliveryReceiptRequest(BaseModel):
    """Delivery receipt webhook payload."""

    provider: str
    provider_message_id: str
    status: str
    timestamp: datetime | None = None
    raw_payload: dict = Field(default_factory=dict)


class DeliveryReceiptResponse(BaseModel):
    """Delivery receipt response."""

    id: str
    message_id: str
    provider: str
    provider_status: str
    mapped_status: str
    processed: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Staff Endpoints
# ============================================================================


@router.get(
    "/templates",
    response_model=list[MessageTemplateResponse],
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def list_templates(
    user: CurrentUser,
    session: DbSession,
    template_type: str | None = None,
) -> list[MessageTemplateResponse]:
    """List message templates."""
    service = MessagingService(session)

    ttype = None
    if template_type:
        try:
            ttype = MessageTemplateType(template_type)
        except ValueError:
            pass

    templates = await service.get_templates(template_type=ttype)

    return [MessageTemplateResponse.model_validate(t) for t in templates]


@router.post(
    "/templates",
    response_model=MessageTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def create_template(
    user: CurrentUser,
    session: DbSession,
    request: CreateTemplateRequest,
) -> MessageTemplateResponse:
    """Create a message template."""
    service = MessagingService(session)

    try:
        template_type = MessageTemplateType(request.template_type)
        channel = MessageChannel(request.channel)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    template = await service.create_template(
        code=request.code,
        template_type=template_type,
        channel=channel,
        body=request.body,
        subject=request.subject,
        html_body=request.html_body,
        variables=request.variables,
    )

    return MessageTemplateResponse.model_validate(template)


@router.post(
    "/send",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def send_message(
    user: CurrentUser,
    session: DbSession,
    request: SendMessageRequest,
) -> MessageResponse:
    """Send a message to a patient."""
    service = MessagingService(session)

    try:
        channel = MessageChannel(request.channel)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel: {request.channel}",
        )

    message = await service.send_message(
        patient_id=request.patient_id,
        channel=channel,
        recipient_address=request.recipient_address,
        body=request.body,
        subject=request.subject,
        html_body=request.html_body,
        template_id=request.template_id,
        appointment_id=request.appointment_id,
        triage_case_id=request.triage_case_id,
        scheduled_at=request.scheduled_at,
    )

    return MessageResponse.model_validate(message)


@router.post(
    "/send-from-template",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def send_from_template(
    user: CurrentUser,
    session: DbSession,
    request: SendFromTemplateRequest,
) -> MessageResponse:
    """Send a message using a template."""
    service = MessagingService(session)

    try:
        template_type = MessageTemplateType(request.template_type)
        channel = MessageChannel(request.channel)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    try:
        message = await service.send_from_template(
            patient_id=request.patient_id,
            template_type=template_type,
            channel=channel,
            recipient_address=request.recipient_address,
            context=request.context,
            appointment_id=request.appointment_id,
            triage_case_id=request.triage_case_id,
            checkin_id=request.checkin_id,
            scheduled_at=request.scheduled_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return MessageResponse.model_validate(message)


@router.get(
    "/messages/{message_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_message(
    message_id: str,
    user: CurrentUser,
    session: DbSession,
) -> MessageResponse:
    """Get a specific message."""
    service = MessagingService(session)
    message = await service.get_message(message_id)

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    return MessageResponse.model_validate(message)


@router.get(
    "/patient/{patient_id}/messages",
    response_model=list[MessageResponse],
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_patient_messages(
    patient_id: str,
    user: CurrentUser,
    session: DbSession,
    channel: str | None = None,
    limit: int = Query(50, le=200),
) -> list[MessageResponse]:
    """Get messages for a patient."""
    service = MessagingService(session)

    msg_channel = None
    if channel:
        try:
            msg_channel = MessageChannel(channel)
        except ValueError:
            pass

    messages = await service.get_patient_messages(
        patient_id=patient_id,
        channel=msg_channel,
        limit=limit,
    )

    return [MessageResponse.model_validate(m) for m in messages]


@router.post(
    "/messages/{message_id}/retry",
    response_model=MessageResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def retry_message(
    message_id: str,
    user: CurrentUser,
    session: DbSession,
) -> MessageResponse:
    """Retry sending a failed message."""
    service = MessagingService(session)
    message = await service.retry_failed_message(message_id)

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    return MessageResponse.model_validate(message)


# ============================================================================
# Webhook Endpoints (no auth required for provider callbacks)
# ============================================================================


@router.post(
    "/webhooks/delivery",
    response_model=DeliveryReceiptResponse,
)
async def receive_delivery_receipt(
    request_body: DeliveryReceiptRequest,
    session: DbSession,
) -> DeliveryReceiptResponse:
    """Receive delivery receipt webhook from messaging provider.

    This endpoint is called by SMS/email providers to report message status.
    """
    service = MessagingService(session)

    receipt = await service.process_delivery_receipt(
        provider=request_body.provider,
        provider_message_id=request_body.provider_message_id,
        provider_status=request_body.status,
        raw_payload=request_body.raw_payload,
        provider_timestamp=request_body.timestamp,
    )

    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found for provider ID",
        )

    return DeliveryReceiptResponse.model_validate(receipt)


@router.post(
    "/webhooks/twilio",
)
async def twilio_webhook(
    request: Request,
    session: DbSession,
) -> dict:
    """Handle Twilio-specific webhook format."""
    form_data = await request.form()

    message_sid = form_data.get("MessageSid", "")
    message_status = form_data.get("MessageStatus", "")

    if not message_sid or not message_status:
        return {"status": "ignored", "reason": "missing fields"}

    service = MessagingService(session)

    receipt = await service.process_delivery_receipt(
        provider="twilio",
        provider_message_id=str(message_sid),
        provider_status=str(message_status),
        raw_payload=dict(form_data),
        provider_timestamp=None,
    )

    if receipt:
        return {"status": "processed", "receipt_id": receipt.id}

    return {"status": "ignored", "reason": "message not found"}


@router.post(
    "/webhooks/sendgrid",
)
async def sendgrid_webhook(
    request: Request,
    session: DbSession,
) -> dict:
    """Handle SendGrid-specific webhook format."""
    events = await request.json()

    if not isinstance(events, list):
        events = [events]

    processed = 0
    service = MessagingService(session)

    for event in events:
        message_id = event.get("sg_message_id", "").split(".")[0]
        event_type = event.get("event", "")

        if message_id and event_type:
            receipt = await service.process_delivery_receipt(
                provider="sendgrid",
                provider_message_id=message_id,
                provider_status=event_type,
                raw_payload=event,
                provider_timestamp=datetime.fromtimestamp(event.get("timestamp", 0))
                if event.get("timestamp")
                else None,
            )

            if receipt:
                processed += 1

    return {"status": "processed", "count": processed}


# ============================================================================
# Intake Recovery Endpoints
# ============================================================================


class IntakeRecoveryStatsResponse(BaseModel):
    """Statistics about abandoned intakes."""

    total_incomplete: int
    under_24h: int
    needs_24h_reminder: int
    awaiting_72h: int = Field(alias="24h_sent_awaiting_72h")
    needs_72h_reminder: int
    final_reminder_sent: int = Field(alias="72h_sent_final")

    class Config:
        from_attributes = True
        populate_by_name = True


class IntakeRecoveryJobResponse(BaseModel):
    """Result of running the intake recovery job."""

    reminders_24h_sent: int = Field(alias="24h_reminders_sent")
    reminders_24h_failed: int = Field(alias="24h_reminders_failed")
    reminders_72h_sent: int = Field(alias="72h_reminders_sent")
    reminders_72h_failed: int = Field(alias="72h_reminders_failed")
    total_cases: int

    class Config:
        from_attributes = True
        populate_by_name = True


class SendReminderRequest(BaseModel):
    """Request to send an intake reminder."""

    channel: str = "email"


@router.get(
    "/intake-recovery/stats",
    response_model=IntakeRecoveryStatsResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_intake_recovery_stats(
    user: CurrentUser,
    session: DbSession,
) -> IntakeRecoveryStatsResponse:
    """Get statistics about abandoned intakes.

    Shows counts of incomplete intakes at various stages of the recovery funnel.
    """
    service = IntakeRecoveryService(session)
    stats = await service.get_recovery_stats()
    return IntakeRecoveryStatsResponse(**stats)


@router.post(
    "/intake-recovery/run",
    response_model=IntakeRecoveryJobResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def run_intake_recovery_job(
    user: CurrentUser,
    session: DbSession,
    channel: str = Query("email", description="Communication channel: email or sms"),
) -> IntakeRecoveryJobResponse:
    """Manually run the intake recovery job.

    Sends 24h and 72h reminders to all eligible patients with incomplete intakes.
    This is typically run by a scheduler but can be triggered manually.
    """
    try:
        msg_channel = MessageChannel(channel)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel: {channel}. Use 'email' or 'sms'.",
        )

    service = IntakeRecoveryService(session)
    results = await service.run_recovery_job(channel=msg_channel)
    return IntakeRecoveryJobResponse(**results)


@router.post(
    "/intake-recovery/send-24h/{triage_case_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def send_24h_reminder(
    triage_case_id: str,
    user: CurrentUser,
    session: DbSession,
    request: SendReminderRequest,
) -> MessageResponse:
    """Send 24h intake reminder for a specific case.

    Only sends if the case meets criteria (incomplete, 24h reminder not yet sent).
    """
    try:
        channel = MessageChannel(request.channel)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel: {request.channel}",
        )

    service = IntakeRecoveryService(session)
    message = await service.send_24h_reminder(triage_case_id, channel)

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found, already reminded, or intake complete",
        )

    return MessageResponse.model_validate(message)


@router.post(
    "/intake-recovery/send-72h/{triage_case_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def send_72h_reminder(
    triage_case_id: str,
    user: CurrentUser,
    session: DbSession,
    request: SendReminderRequest,
) -> MessageResponse:
    """Send 72h final intake reminder for a specific case.

    Only sends if the case meets criteria (incomplete, 24h sent, 72h not yet sent).
    """
    try:
        channel = MessageChannel(request.channel)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel: {request.channel}",
        )

    service = IntakeRecoveryService(session)
    message = await service.send_72h_reminder(triage_case_id, channel)

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found, 24h not sent yet, or 72h already sent",
        )

    return MessageResponse.model_validate(message)
