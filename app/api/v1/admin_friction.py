"""Admin friction reduction API endpoints.

Provides endpoints for:
- Patient-facing explanations (shareable with patients)
- Eligibility summaries (already computed from pathway rules)
- Appointment confirmation management
- Inactive patient outreach
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentPatient, CurrentUser, DbSession, require_permissions
from app.models.messaging import MessageChannel
from app.services.admin_friction import (
    AdminFrictionReductionService,
    AppointmentConfirmationService,
    EligibilityService,
    InactivePatientService,
    PatientExplanationService,
)
from app.services.rbac import Permission

router = APIRouter()


# =============================================================================
# Response Schemas
# =============================================================================


class PatientExplanationResponse(BaseModel):
    """Patient-friendly explanation of triage result."""

    tier: str
    title: str
    description: str
    what_happens_next: list[str]
    can_self_book: bool
    pathway_info: str | None = None


class EligibilitySummaryResponse(BaseModel):
    """Eligibility summary for a triage case."""

    case_id: str
    tier: str | None
    pathway: str | None
    status: str
    can_self_book: bool
    needs_clinical_review: bool
    booking_restrictions: list[str]
    eligible_appointment_types: list[str]
    required_specialties: list[str]
    patient_explanation: PatientExplanationResponse | None = None


class CaseSummaryResponse(BaseModel):
    """Complete case summary for staff."""

    eligibility: EligibilitySummaryResponse
    patient_explanation: PatientExplanationResponse | None
    rules_summary: list[str]
    shareable_text: str


class ConfirmationJobResponse(BaseModel):
    """Result of running confirmation job."""

    confirmation_requests_sent: int
    confirmation_requests_failed: int
    unconfirmed_flagged: int


class InactiveOutreachResponse(BaseModel):
    """Result of running inactive outreach job."""

    messages_sent: int
    messages_failed: int
    patients_processed: int


class AutomationJobsResponse(BaseModel):
    """Combined result of all automation jobs."""

    confirmation: ConfirmationJobResponse
    inactive_outreach: InactiveOutreachResponse


class AppointmentConfirmRequest(BaseModel):
    """Request to confirm an appointment."""

    confirmed: bool = True


# =============================================================================
# Staff Endpoints - Case Summary & Eligibility
# =============================================================================


@router.get(
    "/cases/{triage_case_id}/summary",
    response_model=CaseSummaryResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_case_summary(
    triage_case_id: str,
    user: CurrentUser,
    session: DbSession,
) -> CaseSummaryResponse:
    """Get complete case summary with patient-facing explanation.

    Returns all information staff need to discuss the case with a patient,
    eliminating the need to re-explain triage decisions manually.

    Includes:
    - Eligibility summary (from pathway rules)
    - Patient-friendly explanation (shareable)
    - Copy/paste text for patient communication
    """
    service = AdminFrictionReductionService(session)
    summary = await service.get_case_summary_for_staff(triage_case_id)

    if "error" in summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=summary["error"],
        )

    return CaseSummaryResponse(**summary)


@router.get(
    "/cases/{triage_case_id}/eligibility",
    response_model=EligibilitySummaryResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_eligibility_summary(
    triage_case_id: str,
    user: CurrentUser,
    session: DbSession,
) -> EligibilitySummaryResponse:
    """Get eligibility summary for a triage case.

    Returns clear eligibility information derived from pathway rules,
    eliminating the need for staff to manually check eligibility.

    Includes:
    - Self-booking eligibility
    - Booking restrictions
    - Eligible appointment types
    - Required clinician specialties
    """
    service = EligibilityService(session)
    eligibility = await service.get_eligibility_summary(triage_case_id)

    if "error" in eligibility:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=eligibility["error"],
        )

    return EligibilitySummaryResponse(**eligibility)


# =============================================================================
# Patient Endpoints - View Their Explanation
# =============================================================================


@router.get(
    "/patient/my-explanation",
    response_model=PatientExplanationResponse,
)
async def get_my_explanation(
    patient: CurrentPatient,
    session: DbSession,
) -> PatientExplanationResponse:
    """Get patient-friendly explanation of your triage result.

    Returns a clear explanation of:
    - What your tier means
    - What happens next
    - Whether you can self-book
    """
    from sqlalchemy import select
    from app.models.triage_case import TriageCase, TriageCaseStatus

    # Get patient's most recent triage case
    result = await session.execute(
        select(TriageCase)
        .where(
            TriageCase.patient_id == patient.id,
            TriageCase.status.in_([
                TriageCaseStatus.TRIAGED,
                TriageCaseStatus.IN_REVIEW,
            ]),
        )
        .order_by(TriageCase.created_at.desc())
        .limit(1)
    )
    case = result.scalar_one_or_none()

    if not case or not case.tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completed triage found",
        )

    explanation = PatientExplanationService.generate_tier_explanation(
        case.tier,
        case.pathway,
    )

    return PatientExplanationResponse(**explanation)


# =============================================================================
# Appointment Confirmation Endpoints
# =============================================================================


@router.post(
    "/appointments/{appointment_id}/confirm",
)
async def confirm_appointment(
    appointment_id: str,
    patient: CurrentPatient,
    session: DbSession,
) -> dict:
    """Confirm an appointment (patient action).

    Called when patient clicks confirm link in reminder email.
    """
    service = AppointmentConfirmationService(session)
    appointment = await service.confirm_appointment(
        appointment_id,
        confirmed_by_patient=True,
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    return {
        "status": "confirmed",
        "message": "Your appointment has been confirmed. We look forward to seeing you!",
    }


@router.post(
    "/automation/confirmation-job",
    response_model=ConfirmationJobResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def run_confirmation_job(
    user: CurrentUser,
    session: DbSession,
    channel: str = Query("email", description="Channel: email or sms"),
) -> ConfirmationJobResponse:
    """Run the appointment confirmation job manually.

    Sends confirmation requests to patients with upcoming appointments.
    Typically run by scheduler but can be triggered manually.
    """
    try:
        msg_channel = MessageChannel(channel)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel: {channel}",
        )

    service = AppointmentConfirmationService(session)
    results = await service.run_confirmation_job(msg_channel)
    return ConfirmationJobResponse(**results)


@router.get(
    "/appointments/unconfirmed",
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_unconfirmed_appointments(
    user: CurrentUser,
    session: DbSession,
    threshold_hours: int = Query(24, description="Hours before appointment"),
) -> list[dict]:
    """Get appointments that are still unconfirmed close to appointment time.

    These need staff attention for follow-up calls.
    """
    service = AppointmentConfirmationService(session)
    appointments = await service.get_unconfirmed_appointments(threshold_hours)

    return [
        {
            "id": a.id,
            "patient_id": a.patient_id,
            "scheduled_start": a.scheduled_start.isoformat(),
            "status": a.status.value,
            "reminder_sent_at": a.reminder_sent_at.isoformat() if a.reminder_sent_at else None,
        }
        for a in appointments
    ]


# =============================================================================
# Inactive Patient Outreach Endpoints
# =============================================================================


@router.post(
    "/automation/inactive-outreach-job",
    response_model=InactiveOutreachResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def run_inactive_outreach_job(
    user: CurrentUser,
    session: DbSession,
    channel: str = Query("email", description="Channel: email or sms"),
) -> InactiveOutreachResponse:
    """Run the inactive patient outreach job manually.

    Sends "still want this appointment?" messages to patients who
    haven't engaged recently. Typically run by scheduler.
    """
    try:
        msg_channel = MessageChannel(channel)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel: {channel}",
        )

    service = InactivePatientService(session)
    results = await service.run_inactive_outreach_job(msg_channel)
    return InactiveOutreachResponse(**results)


@router.get(
    "/appointments/inactive-patients",
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_inactive_patient_appointments(
    user: CurrentUser,
    session: DbSession,
) -> list[dict]:
    """Get appointments for patients who may have lost interest.

    Lists appointments where patient hasn't confirmed or engaged
    within the inactivity threshold.
    """
    service = InactivePatientService(session)
    appointments = await service.get_inactive_appointments()

    return [
        {
            "id": a.id,
            "patient_id": a.patient_id,
            "scheduled_start": a.scheduled_start.isoformat(),
            "created_at": a.created_at.isoformat(),
            "days_since_booking": (
                (service.session.get_bind().dialect.name if hasattr(service.session, 'get_bind') else 0) or
                14  # fallback
            ),
        }
        for a in appointments
    ]


# =============================================================================
# Combined Automation Endpoints
# =============================================================================


@router.post(
    "/automation/run-all",
    response_model=AutomationJobsResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def run_all_automation_jobs(
    user: CurrentUser,
    session: DbSession,
    channel: str = Query("email", description="Channel: email or sms"),
) -> AutomationJobsResponse:
    """Run all admin friction reduction automation jobs.

    Combines:
    - Appointment confirmation requests
    - Inactive patient outreach

    Returns combined results for monitoring.
    """
    try:
        msg_channel = MessageChannel(channel)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid channel: {channel}",
        )

    service = AdminFrictionReductionService(session)
    results = await service.run_all_automation_jobs(msg_channel)

    return AutomationJobsResponse(
        confirmation=ConfirmationJobResponse(**results["confirmation"]),
        inactive_outreach=InactiveOutreachResponse(**results["inactive_outreach"]),
    )


@router.get(
    "/automation/stats",
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_automation_stats(
    user: CurrentUser,
    session: DbSession,
) -> dict:
    """Get statistics about automated admin tasks.

    Shows counts of:
    - Pending confirmation requests
    - Unconfirmed appointments
    - Inactive patients needing outreach
    """
    confirmation_service = AppointmentConfirmationService(session)
    inactive_service = InactivePatientService(session)

    pending_confirmation = await confirmation_service.get_appointments_needing_confirmation()
    unconfirmed = await confirmation_service.get_unconfirmed_appointments(24)
    inactive = await inactive_service.get_inactive_appointments()

    return {
        "appointments_needing_confirmation": len(pending_confirmation),
        "unconfirmed_within_24h": len(unconfirmed),
        "inactive_patients_needing_outreach": len(inactive),
    }
