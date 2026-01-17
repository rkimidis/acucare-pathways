"""Scheduling API endpoints for appointments and availability.

Sprint 5: Patient booking, clinician availability management,
and appointment lifecycle.
"""

from datetime import date, datetime, time
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
from app.models.scheduling import (
    AppointmentStatus,
    BookingSource,
    CancellationRequest,
    CancellationRequestStatus,
    CancellationRequestType,
)
from app.services.rbac import Permission
from app.services.scheduling import (
    BookingNotAllowedError,
    ClinicianNotFoundError,
    NoAvailabilityError,
    SchedulingService,
    SelfBookBlockedError,
    SlotNotAvailableError,
)

router = APIRouter()


# ============================================================================
# Request/Response Schemas
# ============================================================================


class ClinicianProfileResponse(BaseModel):
    """Clinician profile response."""

    id: str
    user_id: str
    title: str
    specialties: list[str]
    bio: str | None
    accepting_new_patients: bool
    can_handle_crisis: bool
    default_appointment_duration: int

    class Config:
        from_attributes = True


class AvailabilitySlotResponse(BaseModel):
    """Availability slot response."""

    id: str
    clinician_id: str
    day_of_week: int
    start_time: str
    end_time: str
    is_active: bool
    location: str | None
    is_remote: bool

    class Config:
        from_attributes = True


class CreateAvailabilitySlotRequest(BaseModel):
    """Request to create availability slot."""

    day_of_week: int = Field(ge=0, le=6)
    start_time: str = Field(description="HH:MM format")
    end_time: str = Field(description="HH:MM format")
    location: str | None = None
    is_remote: bool = False


class UpdateAvailabilitySlotRequest(BaseModel):
    """Request to update availability slot."""

    is_active: bool | None = None
    start_time: str | None = None
    end_time: str | None = None
    location: str | None = None


class AppointmentTypeResponse(BaseModel):
    """Appointment type response."""

    id: str
    code: str
    name: str
    description: str | None
    duration_minutes: int
    buffer_minutes: int
    self_book_tiers: list[str]
    allow_remote: bool
    color: str

    class Config:
        from_attributes = True


class AvailableSlotResponse(BaseModel):
    """Available booking slot response."""

    start: str
    end: str
    clinician_id: str
    is_remote: bool
    location: str | None


class BookAppointmentRequest(BaseModel):
    """Request to book an appointment."""

    clinician_id: str
    appointment_type_id: str
    scheduled_start: datetime
    triage_case_id: str | None = None
    is_remote: bool = False
    location: str | None = None
    patient_notes: str | None = Field(None, max_length=2000)


class StaffBookAppointmentRequest(BookAppointmentRequest):
    """Staff request to book appointment for patient."""

    patient_id: str


class AppointmentResponse(BaseModel):
    """Appointment response."""

    id: str
    patient_id: str
    clinician_id: str
    appointment_type_id: str
    triage_case_id: str | None
    scheduled_start: datetime
    scheduled_end: datetime
    status: str
    booking_source: str
    is_remote: bool
    location: str | None
    video_link: str | None
    patient_notes: str | None
    reminder_sent_at: datetime | None

    class Config:
        from_attributes = True


class UpdateAppointmentStatusRequest(BaseModel):
    """Request to update appointment status."""

    status: str
    cancellation_reason: str | None = Field(None, max_length=1000)


class SelfBookCheckResponse(BaseModel):
    """Response for self-book eligibility check."""

    allowed: bool
    reason: str | None


class CancelAppointmentRequest(BaseModel):
    """Request body for patient cancellation."""

    reason: str | None = Field(None, max_length=2000)


class CancelAppointmentResponse(BaseModel):
    """Response for cancellation attempt."""

    success: bool
    message: str
    cancelled: bool  # True if immediately cancelled
    request_submitted: bool  # True if request created for staff review
    request_id: str | None  # If request was created
    safety_workflow_triggered: bool
    appointment_id: str | None  # If cancelled, the appointment ID


class RescheduleAppointmentRequest(BaseModel):
    """Request body for patient reschedule."""

    new_scheduled_start: datetime
    new_clinician_id: str | None = None


class RescheduleAppointmentResponse(BaseModel):
    """Response for reschedule attempt."""

    success: bool
    message: str
    rescheduled: bool  # True if immediately rescheduled
    request_submitted: bool  # True if request created for staff review
    request_id: str | None  # If request was created
    new_appointment_id: str | None  # If rescheduled, the new appointment ID


class CancellationRequestResponse(BaseModel):
    """Response for a cancellation/reschedule request."""

    id: str
    appointment_id: str
    patient_id: str
    triage_case_id: str | None
    request_type: str
    tier_at_request: str
    reason: str | None
    safety_concern_flagged: bool
    status: str
    within_24h: bool
    requested_new_start: datetime | None
    requested_new_clinician_id: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    review_notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewCancellationRequest(BaseModel):
    """Request body for staff review of cancellation request."""

    notes: str | None = Field(None, max_length=2000)


class DenyCancellationRequest(BaseModel):
    """Request body for denying a cancellation request."""

    denial_reason: str = Field(..., min_length=1, max_length=2000)


# ============================================================================
# Patient Endpoints
# ============================================================================


@router.get(
    "/patient/clinicians",
    response_model=list[ClinicianProfileResponse],
)
async def list_clinicians_for_patient(
    patient: CurrentPatient,
    session: DbSession,
    specialty: str | None = None,
) -> list[ClinicianProfileResponse]:
    """List available clinicians for patient booking."""
    service = SchedulingService(session)
    clinicians = await service.list_clinicians(specialty=specialty, accepting_new=True)

    return [ClinicianProfileResponse.model_validate(c) for c in clinicians]


@router.get(
    "/patient/appointment-types",
    response_model=list[AppointmentTypeResponse],
)
async def list_appointment_types_for_patient(
    patient: CurrentPatient,
    session: DbSession,
) -> list[AppointmentTypeResponse]:
    """List bookable appointment types."""
    service = SchedulingService(session)
    types = await service.get_appointment_types(bookable_only=True)

    return [AppointmentTypeResponse.model_validate(t) for t in types]


@router.get(
    "/patient/self-book-check",
    response_model=SelfBookCheckResponse,
)
async def check_self_book_eligibility(
    patient: CurrentPatient,
    session: DbSession,
    triage_case_id: str = Query(...),
    appointment_type_id: str = Query(...),
) -> SelfBookCheckResponse:
    """Check if patient can self-book for their tier."""
    service = SchedulingService(session)
    allowed, reason = await service.check_self_book_allowed(
        triage_case_id, appointment_type_id
    )

    return SelfBookCheckResponse(allowed=allowed, reason=reason)


@router.get(
    "/patient/available-slots",
    response_model=list[AvailableSlotResponse],
)
async def get_available_slots_for_patient(
    patient: CurrentPatient,
    session: DbSession,
    clinician_id: str = Query(...),
    appointment_type_id: str = Query(...),
    start_date: date = Query(...),
    end_date: date = Query(...),
) -> list[AvailableSlotResponse]:
    """Get available booking slots for a clinician."""
    service = SchedulingService(session)

    try:
        slots = await service.get_available_slots(
            clinician_id=clinician_id,
            appointment_type_id=appointment_type_id,
            start_date=start_date,
            end_date=end_date,
        )
    except ClinicianNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinician not found",
        )

    return [AvailableSlotResponse(**s) for s in slots]


@router.post(
    "/patient/appointments",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def book_appointment_patient(
    patient: CurrentPatient,
    session: DbSession,
    request: BookAppointmentRequest,
) -> AppointmentResponse:
    """Book an appointment (patient self-booking)."""
    service = SchedulingService(session)

    try:
        appointment = await service.book_appointment(
            patient_id=patient.id,
            clinician_id=request.clinician_id,
            appointment_type_id=request.appointment_type_id,
            scheduled_start=request.scheduled_start,
            triage_case_id=request.triage_case_id,
            booking_source=BookingSource.PATIENT_SELF_BOOK,
            is_remote=request.is_remote,
            location=request.location,
            patient_notes=request.patient_notes,
        )
    except SelfBookBlockedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except SlotNotAvailableError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This time slot is no longer available",
        )

    return AppointmentResponse.model_validate(appointment)


@router.get(
    "/patient/appointments",
    response_model=list[AppointmentResponse],
)
async def get_patient_appointments(
    patient: CurrentPatient,
    session: DbSession,
    include_past: bool = False,
) -> list[AppointmentResponse]:
    """Get patient's appointments."""
    service = SchedulingService(session)
    appointments = await service.get_patient_appointments(
        patient_id=patient.id,
        include_past=include_past,
    )

    return [AppointmentResponse.model_validate(a) for a in appointments]


@router.post(
    "/patient/appointments/{appointment_id}/cancel",
    response_model=CancelAppointmentResponse,
)
async def cancel_appointment_patient(
    appointment_id: str,
    patient: CurrentPatient,
    session: DbSession,
    request: CancelAppointmentRequest | None = None,
) -> CancelAppointmentResponse:
    """Cancel an appointment (patient-initiated).

    Behavior depends on tier and time window:
    - GREEN/BLUE 24h+: Immediate cancellation
    - GREEN/BLUE <24h: Creates request for staff review
    - AMBER: Creates request (staff arranges)
    - RED: Creates request + safety messaging

    If reason contains safety concerns, triggers safety workflow.
    """
    service = SchedulingService(session)

    try:
        result, message, safety_flagged = await service.cancel_appointment_patient(
            appointment_id=appointment_id,
            patient_id=patient.id,
            reason=request.reason if request else None,
        )

        from app.models.scheduling import Appointment

        if isinstance(result, Appointment):
            return CancelAppointmentResponse(
                success=True,
                message=message,
                cancelled=True,
                request_submitted=False,
                request_id=None,
                safety_workflow_triggered=False,
                appointment_id=result.id,
            )
        else:  # CancellationRequest
            return CancelAppointmentResponse(
                success=True,
                message=message,
                cancelled=False,
                request_submitted=True,
                request_id=result.id,
                safety_workflow_triggered=safety_flagged,
                appointment_id=None,
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/patient/appointments/{appointment_id}/reschedule",
    response_model=RescheduleAppointmentResponse,
)
async def reschedule_appointment_patient(
    appointment_id: str,
    patient: CurrentPatient,
    session: DbSession,
    request: RescheduleAppointmentRequest,
) -> RescheduleAppointmentResponse:
    """Reschedule an appointment (patient-initiated).

    Behavior depends on tier and time window:
    - GREEN/BLUE 24h+: Immediate reschedule (max 2 per appointment)
    - GREEN/BLUE <24h: Creates request for staff review
    - AMBER/RED: Creates request (staff arranges)
    """
    service = SchedulingService(session)

    try:
        result, message = await service.reschedule_appointment_patient(
            appointment_id=appointment_id,
            patient_id=patient.id,
            new_scheduled_start=request.new_scheduled_start,
            new_clinician_id=request.new_clinician_id,
        )

        from app.models.scheduling import Appointment

        if isinstance(result, Appointment):
            return RescheduleAppointmentResponse(
                success=True,
                message=message,
                rescheduled=True,
                request_submitted=False,
                request_id=None,
                new_appointment_id=result.id,
            )
        else:  # CancellationRequest
            return RescheduleAppointmentResponse(
                success=True,
                message=message,
                rescheduled=False,
                request_submitted=True,
                request_id=result.id,
                new_appointment_id=None,
            )
    except SlotNotAvailableError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The requested time slot is not available",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# Staff Endpoints
# ============================================================================


@router.get(
    "/staff/clinicians",
    response_model=list[ClinicianProfileResponse],
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def list_clinicians_staff(
    user: CurrentUser,
    session: DbSession,
    specialty: str | None = None,
    accepting_new: bool | None = None,
) -> list[ClinicianProfileResponse]:
    """List clinician profiles (staff view)."""
    service = SchedulingService(session)
    clinicians = await service.list_clinicians(
        specialty=specialty,
        accepting_new=accepting_new if accepting_new is not None else True,
    )

    return [ClinicianProfileResponse.model_validate(c) for c in clinicians]


@router.get(
    "/staff/clinicians/{clinician_id}/availability",
    response_model=list[AvailabilitySlotResponse],
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_clinician_availability(
    clinician_id: str,
    user: CurrentUser,
    session: DbSession,
    day_of_week: int | None = None,
) -> list[AvailabilitySlotResponse]:
    """Get availability slots for a clinician."""
    service = SchedulingService(session)
    slots = await service.get_availability_slots(
        clinician_id=clinician_id,
        day_of_week=day_of_week,
    )

    return [
        AvailabilitySlotResponse(
            id=s.id,
            clinician_id=s.clinician_id,
            day_of_week=s.day_of_week,
            start_time=s.start_time.strftime("%H:%M"),
            end_time=s.end_time.strftime("%H:%M"),
            is_active=s.is_active,
            location=s.location,
            is_remote=s.is_remote,
        )
        for s in slots
    ]


@router.post(
    "/staff/clinicians/{clinician_id}/availability",
    response_model=AvailabilitySlotResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def create_availability_slot(
    clinician_id: str,
    user: CurrentUser,
    session: DbSession,
    request: CreateAvailabilitySlotRequest,
) -> AvailabilitySlotResponse:
    """Create an availability slot for a clinician."""
    service = SchedulingService(session)

    # Parse time strings
    start = datetime.strptime(request.start_time, "%H:%M").time()
    end = datetime.strptime(request.end_time, "%H:%M").time()

    slot = await service.create_availability_slot(
        clinician_id=clinician_id,
        day_of_week=request.day_of_week,
        start_time=start,
        end_time=end,
        location=request.location,
        is_remote=request.is_remote,
    )

    return AvailabilitySlotResponse(
        id=slot.id,
        clinician_id=slot.clinician_id,
        day_of_week=slot.day_of_week,
        start_time=slot.start_time.strftime("%H:%M"),
        end_time=slot.end_time.strftime("%H:%M"),
        is_active=slot.is_active,
        location=slot.location,
        is_remote=slot.is_remote,
    )


@router.patch(
    "/staff/availability/{slot_id}",
    response_model=AvailabilitySlotResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def update_availability_slot(
    slot_id: str,
    user: CurrentUser,
    session: DbSession,
    request: UpdateAvailabilitySlotRequest,
) -> AvailabilitySlotResponse:
    """Update an availability slot."""
    service = SchedulingService(session)

    start = datetime.strptime(request.start_time, "%H:%M").time() if request.start_time else None
    end = datetime.strptime(request.end_time, "%H:%M").time() if request.end_time else None

    slot = await service.update_availability_slot(
        slot_id=slot_id,
        is_active=request.is_active,
        start_time=start,
        end_time=end,
        location=request.location,
    )

    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability slot not found",
        )

    return AvailabilitySlotResponse(
        id=slot.id,
        clinician_id=slot.clinician_id,
        day_of_week=slot.day_of_week,
        start_time=slot.start_time.strftime("%H:%M"),
        end_time=slot.end_time.strftime("%H:%M"),
        is_active=slot.is_active,
        location=slot.location,
        is_remote=slot.is_remote,
    )


@router.post(
    "/staff/appointments",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def book_appointment_staff(
    user: CurrentUser,
    session: DbSession,
    request: StaffBookAppointmentRequest,
) -> AppointmentResponse:
    """Book an appointment on behalf of a patient (staff booking)."""
    service = SchedulingService(session)

    try:
        appointment = await service.book_appointment(
            patient_id=request.patient_id,
            clinician_id=request.clinician_id,
            appointment_type_id=request.appointment_type_id,
            scheduled_start=request.scheduled_start,
            triage_case_id=request.triage_case_id,
            booking_source=BookingSource.STAFF_BOOKED,
            booked_by=user.id,
            is_remote=request.is_remote,
            location=request.location,
            patient_notes=request.patient_notes,
        )
    except SlotNotAvailableError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This time slot is no longer available",
        )

    return AppointmentResponse.model_validate(appointment)


@router.get(
    "/staff/clinicians/{clinician_id}/appointments",
    response_model=list[AppointmentResponse],
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_clinician_appointments(
    clinician_id: str,
    user: CurrentUser,
    session: DbSession,
    start_date: date | None = None,
    end_date: date | None = None,
    status_filter: str | None = None,
) -> list[AppointmentResponse]:
    """Get appointments for a clinician."""
    service = SchedulingService(session)

    apt_status = None
    if status_filter:
        try:
            apt_status = AppointmentStatus(status_filter)
        except ValueError:
            pass

    appointments = await service.get_clinician_appointments(
        clinician_id=clinician_id,
        start_date=start_date,
        end_date=end_date,
        status=apt_status,
    )

    return [AppointmentResponse.model_validate(a) for a in appointments]


@router.get(
    "/staff/appointments/{appointment_id}",
    response_model=AppointmentResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_appointment_staff(
    appointment_id: str,
    user: CurrentUser,
    session: DbSession,
) -> AppointmentResponse:
    """Get a single appointment."""
    service = SchedulingService(session)
    appointment = await service.get_appointment(appointment_id)

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    return AppointmentResponse.model_validate(appointment)


@router.patch(
    "/staff/appointments/{appointment_id}/status",
    response_model=AppointmentResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def update_appointment_status_staff(
    appointment_id: str,
    user: CurrentUser,
    session: DbSession,
    request: UpdateAppointmentStatusRequest,
) -> AppointmentResponse:
    """Update appointment status (staff)."""
    service = SchedulingService(session)

    try:
        new_status = AppointmentStatus(request.status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {request.status}",
        )

    appointment = await service.update_appointment_status(
        appointment_id=appointment_id,
        new_status=new_status,
        cancelled_by=user.id if new_status == AppointmentStatus.CANCELLED else None,
        cancellation_reason=request.cancellation_reason,
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    return AppointmentResponse.model_validate(appointment)


@router.get(
    "/staff/appointment-types",
    response_model=list[AppointmentTypeResponse],
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def list_appointment_types_staff(
    user: CurrentUser,
    session: DbSession,
    bookable_only: bool = False,
) -> list[AppointmentTypeResponse]:
    """List all appointment types (staff view)."""
    service = SchedulingService(session)
    types = await service.get_appointment_types(bookable_only=bookable_only)

    return [AppointmentTypeResponse.model_validate(t) for t in types]


# ============================================================================
# Staff Cancellation Request Management
# ============================================================================


@router.get(
    "/staff/cancellation-requests",
    response_model=list[CancellationRequestResponse],
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def list_cancellation_requests(
    user: CurrentUser,
    session: DbSession,
    status: str | None = Query(None, description="Filter by status: pending, approved, denied"),
    safety_flagged_only: bool = Query(False, description="Only show safety-flagged requests"),
) -> list[CancellationRequestResponse]:
    """List cancellation/reschedule requests requiring staff review.

    Priority should be given to:
    1. Safety-flagged requests (immediate attention)
    2. AMBER/RED tier requests
    3. Within-24h requests from GREEN/BLUE
    """
    service = SchedulingService(session)

    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = CancellationRequestStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}. Valid values: pending, approved, denied, auto_approved",
            )

    requests = await service.list_cancellation_requests(
        status=status_filter,
        safety_flagged_only=safety_flagged_only,
    )

    return [CancellationRequestResponse.model_validate(r) for r in requests]


@router.get(
    "/staff/cancellation-requests/{request_id}",
    response_model=CancellationRequestResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_cancellation_request(
    request_id: str,
    user: CurrentUser,
    session: DbSession,
) -> CancellationRequestResponse:
    """Get details of a specific cancellation request."""
    service = SchedulingService(session)
    request = await service.get_cancellation_request(request_id)

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cancellation request not found",
        )

    return CancellationRequestResponse.model_validate(request)


@router.post(
    "/staff/cancellation-requests/{request_id}/approve",
    response_model=CancellationRequestResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def approve_cancellation_request(
    request_id: str,
    user: CurrentUser,
    session: DbSession,
    body: ReviewCancellationRequest | None = None,
) -> CancellationRequestResponse:
    """Approve a cancellation or reschedule request.

    For cancellation requests: Cancels the appointment.
    For reschedule requests: Creates new appointment at requested time.
    """
    service = SchedulingService(session)

    try:
        request = await service.approve_cancellation_request(
            request_id=request_id,
            staff_user_id=user.id,
            notes=body.notes if body else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return CancellationRequestResponse.model_validate(request)


@router.post(
    "/staff/cancellation-requests/{request_id}/deny",
    response_model=CancellationRequestResponse,
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def deny_cancellation_request(
    request_id: str,
    user: CurrentUser,
    session: DbSession,
    body: DenyCancellationRequest,
) -> CancellationRequestResponse:
    """Deny a cancellation or reschedule request.

    The patient will be notified that their request was denied
    with the provided reason.
    """
    service = SchedulingService(session)

    try:
        request = await service.deny_cancellation_request(
            request_id=request_id,
            staff_user_id=user.id,
            denial_reason=body.denial_reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return CancellationRequestResponse.model_validate(request)
