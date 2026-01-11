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
from app.models.scheduling import AppointmentStatus, BookingSource
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
    response_model=AppointmentResponse,
)
async def cancel_appointment_patient(
    appointment_id: str,
    patient: CurrentPatient,
    session: DbSession,
    cancellation_reason: str | None = None,
) -> AppointmentResponse:
    """Cancel an appointment (patient-initiated)."""
    service = SchedulingService(session)

    appointment = await service.get_appointment(appointment_id)

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    if appointment.patient_id != patient.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this appointment",
        )

    updated = await service.update_appointment_status(
        appointment_id=appointment_id,
        new_status=AppointmentStatus.CANCELLED,
        cancelled_by=patient.id,
        cancellation_reason=cancellation_reason,
    )

    return AppointmentResponse.model_validate(updated)


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
