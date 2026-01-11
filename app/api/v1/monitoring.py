"""Monitoring API endpoints for waiting list check-ins.

Sprint 5: Patient check-in submission, staff alert management,
and monitoring schedule control.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    CurrentPatient,
    CurrentUser,
    DbSession,
    require_permissions,
)
from app.services.monitoring import (
    CheckInAlreadyCompletedError,
    CheckInNotFoundError,
    MonitoringService,
)
from app.services.rbac import Permission
from app.services.audit import write_audit_event
from app.models.audit_event import ActorType

router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================


class CheckInResponse(BaseModel):
    """Check-in response."""

    id: str
    patient_id: str
    triage_case_id: str
    sequence_number: int
    status: str
    scheduled_for: datetime
    expires_at: datetime | None
    completed_at: datetime | None
    phq2_total: int | None
    gad2_total: int | None
    wellbeing_rating: int | None
    requires_escalation: bool
    escalation_reason: str | None

    class Config:
        from_attributes = True


class SubmitCheckInRequest(BaseModel):
    """Request to submit check-in response."""

    # PHQ-2 questions (0-3 each)
    phq2_q1: int = Field(ge=0, le=3, description="Little interest or pleasure in doing things")
    phq2_q2: int = Field(ge=0, le=3, description="Feeling down, depressed, or hopeless")
    # GAD-2 questions (0-3 each)
    gad2_q1: int = Field(ge=0, le=3, description="Feeling nervous, anxious, or on edge")
    gad2_q2: int = Field(ge=0, le=3, description="Not being able to stop or control worrying")
    # Risk questions
    suicidal_ideation: bool = False
    self_harm: bool = False
    # Additional fields
    wellbeing_rating: int | None = Field(None, ge=1, le=10)
    patient_comments: str | None = Field(None, max_length=2000)
    wants_callback: bool = False


class MonitoringScheduleResponse(BaseModel):
    """Monitoring schedule response."""

    id: str
    triage_case_id: str
    is_active: bool
    frequency_days: int
    next_checkin_date: datetime | None
    last_checkin_date: datetime | None
    consecutive_missed: int
    paused: bool
    paused_until: datetime | None
    pause_reason: str | None

    class Config:
        from_attributes = True


class PauseMonitoringRequest(BaseModel):
    """Request to pause monitoring."""

    until: datetime
    reason: str | None = Field(None, max_length=500)


class MonitoringAlertResponse(BaseModel):
    """Monitoring alert response."""

    id: str
    patient_id: str
    triage_case_id: str
    checkin_id: str | None
    alert_type: str
    severity: str
    title: str
    description: str
    phq2_score: int | None
    gad2_score: int | None
    is_active: bool
    acknowledged_at: datetime | None
    acknowledged_by: str | None
    resolved_at: datetime | None
    resolved_by: str | None
    resolution_notes: str | None
    action_taken: str | None
    escalated_to_amber: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ResolveAlertRequest(BaseModel):
    """Request to resolve an alert."""

    notes: str | None = Field(None, max_length=2000)
    action: str | None = Field(None, max_length=100)


class AlertCountsResponse(BaseModel):
    """Alert counts by severity."""

    critical: int
    high: int
    medium: int
    low: int
    total: int


class DutyQueueResponse(BaseModel):
    """Duty queue response with alerts and counts."""

    alerts: list[MonitoringAlertResponse]
    counts: AlertCountsResponse


# ============================================================================
# Patient Endpoints
# ============================================================================


@router.get(
    "/patient/checkin",
    response_model=CheckInResponse | None,
)
async def get_pending_checkin(
    patient: CurrentPatient,
    session: DbSession,
    triage_case_id: str | None = None,
) -> CheckInResponse | None:
    """Get the patient's pending check-in, if any."""
    service = MonitoringService(session)
    checkin = await service.get_pending_checkin(
        patient_id=patient.id,
        triage_case_id=triage_case_id,
    )

    if not checkin:
        return None

    return CheckInResponse.model_validate(checkin)


@router.post(
    "/patient/checkin/{checkin_id}",
    response_model=CheckInResponse,
)
async def submit_checkin(
    checkin_id: str,
    patient: CurrentPatient,
    session: DbSession,
    request: SubmitCheckInRequest,
) -> CheckInResponse:
    """Submit a check-in response."""
    service = MonitoringService(session)

    # Verify the check-in belongs to this patient
    checkin = await service.get_checkin(checkin_id)

    if not checkin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Check-in not found",
        )

    if checkin.patient_id != patient.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to submit this check-in",
        )

    try:
        updated = await service.submit_checkin_response(
            checkin_id=checkin_id,
            phq2_q1=request.phq2_q1,
            phq2_q2=request.phq2_q2,
            gad2_q1=request.gad2_q1,
            gad2_q2=request.gad2_q2,
            suicidal_ideation=request.suicidal_ideation,
            self_harm=request.self_harm,
            wellbeing_rating=request.wellbeing_rating,
            patient_comments=request.patient_comments,
            wants_callback=request.wants_callback,
            raw_response=request.model_dump(),
        )

        # Audit log the check-in submission
        await write_audit_event(
            session=session,
            actor_type=ActorType.PATIENT,
            actor_id=patient.id,
            action="checkin.submitted",
            action_category="clinical",
            entity_type="waiting_list_checkin",
            entity_id=checkin_id,
            description="Patient submitted check-in response",
            metadata={
                "sequence_number": updated.sequence_number,
                "phq2_total": updated.phq2_total,
                "gad2_total": updated.gad2_total,
                "suicidal_ideation": updated.suicidal_ideation,
                "self_harm": updated.self_harm,
                "wellbeing_rating": updated.wellbeing_rating,
                "wants_callback": updated.wants_callback,
                "requires_escalation": updated.requires_escalation,
                "escalation_reason": updated.escalation_reason,
            },
        )

    except CheckInAlreadyCompletedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Check-in has already been completed",
        )

    return CheckInResponse.model_validate(updated)


@router.get(
    "/patient/checkins",
    response_model=list[CheckInResponse],
)
async def get_patient_checkin_history(
    patient: CurrentPatient,
    session: DbSession,
    limit: int = Query(10, le=50),
) -> list[CheckInResponse]:
    """Get patient's check-in history."""
    service = MonitoringService(session)
    checkins = await service.get_patient_checkins(
        patient_id=patient.id,
        limit=limit,
    )

    return [CheckInResponse.model_validate(c) for c in checkins]


# ============================================================================
# Staff Endpoints
# ============================================================================


@router.get(
    "/staff/alerts",
    response_model=list[MonitoringAlertResponse],
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def list_monitoring_alerts(
    user: CurrentUser,
    session: DbSession,
    severity: str | None = None,
    active_only: bool = True,
    limit: int = Query(100, le=500),
) -> list[MonitoringAlertResponse]:
    """List monitoring alerts for staff review."""
    service = MonitoringService(session)
    alerts = await service.get_active_alerts(
        severity=severity,
        limit=limit,
    )

    return [MonitoringAlertResponse.model_validate(a) for a in alerts]


@router.get(
    "/staff/alerts/counts",
    response_model=AlertCountsResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_alert_counts(
    user: CurrentUser,
    session: DbSession,
) -> AlertCountsResponse:
    """Get counts of active alerts by severity."""
    service = MonitoringService(session)
    counts = await service.get_duty_queue_count()

    return AlertCountsResponse(
        critical=counts["critical"],
        high=counts["high"],
        medium=counts["medium"],
        low=counts["low"],
        total=counts["total"],
    )


@router.get(
    "/staff/duty-queue",
    response_model=DutyQueueResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_duty_queue(
    user: CurrentUser,
    session: DbSession,
    include_acknowledged: bool = False,
    limit: int = Query(50, le=200),
) -> DutyQueueResponse:
    """Get the duty queue - prioritized list of escalated cases needing review.

    Returns alerts ordered by severity (critical first) then by creation time.
    Used by clinical staff to work through escalated cases efficiently.
    """
    service = MonitoringService(session)

    alerts = await service.get_duty_queue(
        include_acknowledged=include_acknowledged,
        limit=limit,
    )
    counts = await service.get_duty_queue_count()

    return DutyQueueResponse(
        alerts=[MonitoringAlertResponse.model_validate(a) for a in alerts],
        counts=AlertCountsResponse(
            critical=counts["critical"],
            high=counts["high"],
            medium=counts["medium"],
            low=counts["low"],
            total=counts["total"],
        ),
    )


@router.post(
    "/staff/alerts/{alert_id}/acknowledge",
    response_model=MonitoringAlertResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def acknowledge_alert(
    alert_id: str,
    user: CurrentUser,
    session: DbSession,
) -> MonitoringAlertResponse:
    """Acknowledge a monitoring alert."""
    service = MonitoringService(session)
    alert = await service.acknowledge_alert(alert_id, user.id)

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    return MonitoringAlertResponse.model_validate(alert)


@router.post(
    "/staff/alerts/{alert_id}/resolve",
    response_model=MonitoringAlertResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def resolve_alert(
    alert_id: str,
    user: CurrentUser,
    session: DbSession,
    request: ResolveAlertRequest,
) -> MonitoringAlertResponse:
    """Resolve a monitoring alert."""
    service = MonitoringService(session)
    alert = await service.resolve_alert(
        alert_id=alert_id,
        user_id=user.id,
        notes=request.notes,
        action=request.action,
    )

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    return MonitoringAlertResponse.model_validate(alert)


@router.get(
    "/staff/schedules/{triage_case_id}",
    response_model=MonitoringScheduleResponse | None,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_monitoring_schedule(
    triage_case_id: str,
    user: CurrentUser,
    session: DbSession,
) -> MonitoringScheduleResponse | None:
    """Get monitoring schedule for a triage case."""
    service = MonitoringService(session)
    schedule = await service.get_monitoring_schedule(triage_case_id)

    if not schedule:
        return None

    return MonitoringScheduleResponse.model_validate(schedule)


@router.post(
    "/staff/schedules/{triage_case_id}",
    response_model=MonitoringScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def create_monitoring_schedule(
    triage_case_id: str,
    user: CurrentUser,
    session: DbSession,
    frequency_days: int = Query(7, ge=1, le=30),
) -> MonitoringScheduleResponse:
    """Create a monitoring schedule for a triage case."""
    service = MonitoringService(session)

    # Check if schedule already exists
    existing = await service.get_monitoring_schedule(triage_case_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Monitoring schedule already exists for this case",
        )

    schedule = await service.create_monitoring_schedule(
        triage_case_id=triage_case_id,
        frequency_days=frequency_days,
    )

    return MonitoringScheduleResponse.model_validate(schedule)


@router.post(
    "/staff/schedules/{triage_case_id}/pause",
    response_model=MonitoringScheduleResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def pause_monitoring(
    triage_case_id: str,
    user: CurrentUser,
    session: DbSession,
    request: PauseMonitoringRequest,
) -> MonitoringScheduleResponse:
    """Pause monitoring for a case."""
    service = MonitoringService(session)
    schedule = await service.pause_monitoring(
        triage_case_id=triage_case_id,
        until=request.until,
        reason=request.reason,
    )

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring schedule not found",
        )

    return MonitoringScheduleResponse.model_validate(schedule)


@router.post(
    "/staff/schedules/{triage_case_id}/resume",
    response_model=MonitoringScheduleResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def resume_monitoring(
    triage_case_id: str,
    user: CurrentUser,
    session: DbSession,
) -> MonitoringScheduleResponse:
    """Resume paused monitoring for a case."""
    service = MonitoringService(session)
    schedule = await service.resume_monitoring(triage_case_id)

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring schedule not found",
        )

    return MonitoringScheduleResponse.model_validate(schedule)


@router.get(
    "/staff/checkins/{checkin_id}",
    response_model=CheckInResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_checkin_staff(
    checkin_id: str,
    user: CurrentUser,
    session: DbSession,
) -> CheckInResponse:
    """Get a specific check-in (staff view)."""
    service = MonitoringService(session)
    checkin = await service.get_checkin(checkin_id)

    if not checkin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Check-in not found",
        )

    return CheckInResponse.model_validate(checkin)
