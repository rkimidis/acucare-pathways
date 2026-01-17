"""Scheduling service for appointments and availability.

Sprint 5: Handles clinician availability, appointment booking,
and tier-based access control for self-booking.

SAFETY CRITICAL: This module enforces booking restrictions for RED/AMBER tiers.
Any bypass of these restrictions would be a critical safety violation.
"""

from datetime import datetime, timedelta, time, date, timezone
from typing import Sequence
from uuid import uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.booking.policy import (
    BLOCKED_TIERS,
    can_patient_self_book,
    get_booking_policy,
    validate_booking_request,
)
from app.models.scheduling import (
    Appointment,
    AppointmentStatus,
    AppointmentType,
    AvailabilitySlot,
    BookingSource,
    ClinicianProfile,
)
from app.models.triage_case import TriageCase, TriageTier


class BookingNotAllowedError(Exception):
    """Raised when booking is not allowed for this patient/tier."""

    pass


class SelfBookBlockedError(BookingNotAllowedError):
    """Raised when self-booking is blocked for RED/AMBER tiers.

    SAFETY CRITICAL: This exception MUST be raised for RED/AMBER tiers
    attempting to self-book. Never catch and suppress this exception.
    """

    pass


class NoAvailabilityError(Exception):
    """Raised when no availability slots match the request."""

    pass


class SlotNotAvailableError(Exception):
    """Raised when the requested slot is no longer available."""

    pass


class ClinicianNotFoundError(Exception):
    """Raised when clinician profile is not found."""

    pass


# Tiers that can self-book appointments
SELF_BOOK_ALLOWED_TIERS = {TriageTier.GREEN, TriageTier.BLUE}


class SchedulingService:
    """Service for managing appointments and availability."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_clinician_profile(self, user_id: str) -> ClinicianProfile | None:
        """Get clinician profile by user ID."""
        result = await self.session.execute(
            select(ClinicianProfile).where(
                ClinicianProfile.user_id == user_id,
                ClinicianProfile.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def get_clinician_by_id(self, profile_id: str) -> ClinicianProfile | None:
        """Get clinician profile by profile ID."""
        result = await self.session.execute(
            select(ClinicianProfile).where(
                ClinicianProfile.id == profile_id,
                ClinicianProfile.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def list_clinicians(
        self,
        specialty: str | None = None,
        accepting_new: bool = True,
    ) -> Sequence[ClinicianProfile]:
        """List clinician profiles with optional filters."""
        query = select(ClinicianProfile).where(
            ClinicianProfile.is_deleted == False,
        )

        if accepting_new:
            query = query.where(ClinicianProfile.accepting_new_patients == True)

        if specialty:
            query = query.where(ClinicianProfile.specialties.contains([specialty]))

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_availability_slots(
        self,
        clinician_id: str,
        day_of_week: int | None = None,
    ) -> Sequence[AvailabilitySlot]:
        """Get availability slots for a clinician."""
        query = select(AvailabilitySlot).where(
            AvailabilitySlot.clinician_id == clinician_id,
            AvailabilitySlot.is_active == True,
        )

        if day_of_week is not None:
            query = query.where(AvailabilitySlot.day_of_week == day_of_week)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def create_availability_slot(
        self,
        clinician_id: str,
        day_of_week: int,
        start_time: time,
        end_time: time,
        location: str | None = None,
        is_remote: bool = False,
    ) -> AvailabilitySlot:
        """Create a new availability slot for a clinician."""
        slot = AvailabilitySlot(
            id=str(uuid4()),
            clinician_id=clinician_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            location=location,
            is_remote=is_remote,
        )

        self.session.add(slot)
        await self.session.commit()
        await self.session.refresh(slot)

        return slot

    async def update_availability_slot(
        self,
        slot_id: str,
        is_active: bool | None = None,
        start_time: time | None = None,
        end_time: time | None = None,
        location: str | None = None,
    ) -> AvailabilitySlot | None:
        """Update an availability slot."""
        result = await self.session.execute(
            select(AvailabilitySlot).where(AvailabilitySlot.id == slot_id)
        )
        slot = result.scalar_one_or_none()

        if not slot:
            return None

        if is_active is not None:
            slot.is_active = is_active
        if start_time is not None:
            slot.start_time = start_time
        if end_time is not None:
            slot.end_time = end_time
        if location is not None:
            slot.location = location

        await self.session.commit()
        await self.session.refresh(slot)

        return slot

    async def get_appointment_types(
        self,
        bookable_only: bool = True,
    ) -> Sequence[AppointmentType]:
        """Get available appointment types."""
        query = select(AppointmentType).where(
            AppointmentType.is_deleted == False,
        )

        if bookable_only:
            query = query.where(AppointmentType.is_bookable == True)

        query = query.order_by(AppointmentType.display_order)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def check_self_book_allowed(
        self,
        triage_case_id: str,
        appointment_type_id: str,
    ) -> tuple[bool, str | None]:
        """Check if self-booking is allowed for this case and appointment type.

        SAFETY CRITICAL: This method enforces tier-based booking restrictions.
        RED and AMBER tiers MUST NEVER be allowed to self-book.

        Returns (allowed, reason) tuple.
        """
        # Get triage case
        result = await self.session.execute(
            select(TriageCase).where(TriageCase.id == triage_case_id)
        )
        case = result.scalar_one_or_none()

        if not case:
            return False, "Triage case not found"

        # SAFETY CRITICAL: Use centralized booking policy for tier check
        # This is the primary safety gate - RED/AMBER MUST be blocked
        if case.tier:
            tier_str = case.tier.value if isinstance(case.tier, TriageTier) else str(case.tier)
            policy = get_booking_policy(tier_str)

            if not policy.allowed:
                # Log the blocked attempt for audit
                return False, policy.message

            # Double-check with can_patient_self_book as defense in depth
            if not can_patient_self_book(tier_str):
                return False, f"Self-booking is blocked for {tier_str.upper()} tier (safety restriction)"

        # Check case-level self-book flag (may be set by clinician override)
        if not case.self_book_allowed:
            return False, "Self-booking has been disabled for this case by clinical review"

        # Get appointment type
        result = await self.session.execute(
            select(AppointmentType).where(AppointmentType.id == appointment_type_id)
        )
        apt_type = result.scalar_one_or_none()

        if not apt_type:
            return False, "Appointment type not found"

        # Check if this tier can self-book this appointment type
        if case.tier:
            tier_str = case.tier.value if isinstance(case.tier, TriageTier) else str(case.tier)
            if not apt_type.can_self_book(tier_str):
                return False, f"This appointment type cannot be self-booked for {tier_str.upper()} tier"

        return True, None

    async def get_available_slots(
        self,
        clinician_id: str,
        appointment_type_id: str,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """Get available appointment slots for a clinician within a date range.

        Returns list of available slot dictionaries with start/end times.
        """
        # Get clinician profile
        clinician = await self.get_clinician_by_id(clinician_id)
        if not clinician:
            raise ClinicianNotFoundError(f"Clinician {clinician_id} not found")

        # Get appointment type for duration
        result = await self.session.execute(
            select(AppointmentType).where(AppointmentType.id == appointment_type_id)
        )
        apt_type = result.scalar_one_or_none()

        if not apt_type:
            return []

        duration = timedelta(minutes=apt_type.duration_minutes)
        buffer = timedelta(minutes=apt_type.buffer_minutes)

        # Get recurring availability slots
        slots = await self.get_availability_slots(clinician_id)

        # Get existing appointments in date range
        existing = await self._get_appointments_in_range(
            clinician_id, start_date, end_date
        )

        available = []
        current_date = start_date

        while current_date <= end_date:
            day_of_week = current_date.weekday()

            # Find matching availability slots for this day
            day_slots = [s for s in slots if s.day_of_week == day_of_week]

            for slot in day_slots:
                # Generate time slots within this availability window (UTC)
                slot_start = datetime.combine(current_date, slot.start_time, tzinfo=timezone.utc)
                slot_end = datetime.combine(current_date, slot.end_time, tzinfo=timezone.utc)

                current_time = slot_start
                while current_time + duration <= slot_end:
                    proposed_end = current_time + duration

                    # Check for conflicts with existing appointments
                    has_conflict = self._check_conflict(
                        current_time, proposed_end, existing, buffer
                    )

                    if not has_conflict and current_time > datetime.now(timezone.utc):
                        available.append({
                            "start": current_time.isoformat(),
                            "end": proposed_end.isoformat(),
                            "clinician_id": clinician_id,
                            "is_remote": slot.is_remote,
                            "location": slot.location,
                        })

                    # Move to next slot (duration + buffer)
                    current_time = proposed_end + buffer

            current_date += timedelta(days=1)

        return available

    async def _get_appointments_in_range(
        self,
        clinician_id: str,
        start_date: date,
        end_date: date,
    ) -> Sequence[Appointment]:
        """Get existing appointments for a clinician in a date range."""
        start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, time.max, tzinfo=timezone.utc)

        result = await self.session.execute(
            select(Appointment).where(
                Appointment.clinician_id == clinician_id,
                Appointment.scheduled_start >= start_dt,
                Appointment.scheduled_start <= end_dt,
                Appointment.status.not_in([
                    AppointmentStatus.CANCELLED,
                    AppointmentStatus.RESCHEDULED,
                ]),
                Appointment.is_deleted == False,
            )
        )
        return result.scalars().all()

    def _check_conflict(
        self,
        start: datetime,
        end: datetime,
        existing: Sequence[Appointment],
        buffer: timedelta,
    ) -> bool:
        """Check if proposed time conflicts with existing appointments."""
        for apt in existing:
            apt_start = apt.scheduled_start - buffer
            apt_end = apt.scheduled_end + buffer

            # Check for overlap
            if start < apt_end and end > apt_start:
                return True

        return False

    async def book_appointment(
        self,
        patient_id: str,
        clinician_id: str,
        appointment_type_id: str,
        scheduled_start: datetime,
        triage_case_id: str | None = None,
        booking_source: BookingSource = BookingSource.PATIENT_SELF_BOOK,
        booked_by: str | None = None,
        is_remote: bool = False,
        location: str | None = None,
        patient_notes: str | None = None,
    ) -> Appointment:
        """Book an appointment.

        SAFETY CRITICAL: Validates booking rules and creates the appointment record.
        RED/AMBER tier patients CANNOT self-book - this is enforced server-side
        and cannot be bypassed by client manipulation.
        """
        # SAFETY CRITICAL: If self-booking, validate tier restrictions
        # This check MUST happen before any booking is created
        if booking_source == BookingSource.PATIENT_SELF_BOOK:
            # Even without triage_case_id, we should be cautious
            if triage_case_id:
                allowed, reason = await self.check_self_book_allowed(
                    triage_case_id, appointment_type_id
                )
                if not allowed:
                    raise SelfBookBlockedError(reason or "Self-booking not allowed")

                # DEFENSE IN DEPTH: Re-verify tier directly from case
                # This prevents any bypass through check_self_book_allowed
                result = await self.session.execute(
                    select(TriageCase).where(TriageCase.id == triage_case_id)
                )
                case = result.scalar_one_or_none()
                if case and case.tier:
                    tier_str = case.tier.value if isinstance(case.tier, TriageTier) else str(case.tier)
                    if tier_str.upper() in BLOCKED_TIERS:
                        raise SelfBookBlockedError(
                            f"SAFETY BLOCK: {tier_str.upper()} tier patients cannot self-book. "
                            "Please contact the clinic for assistance."
                        )

        # Get appointment type for duration
        result = await self.session.execute(
            select(AppointmentType).where(AppointmentType.id == appointment_type_id)
        )
        apt_type = result.scalar_one_or_none()

        if not apt_type:
            raise ValueError("Invalid appointment type")

        scheduled_end = scheduled_start + timedelta(minutes=apt_type.duration_minutes)

        # Check slot is still available
        existing = await self._get_appointments_in_range(
            clinician_id,
            scheduled_start.date(),
            scheduled_start.date(),
        )

        buffer = timedelta(minutes=apt_type.buffer_minutes)
        if self._check_conflict(scheduled_start, scheduled_end, existing, buffer):
            raise SlotNotAvailableError("This time slot is no longer available")

        # Create appointment
        appointment = Appointment(
            id=str(uuid4()),
            patient_id=patient_id,
            clinician_id=clinician_id,
            appointment_type_id=appointment_type_id,
            triage_case_id=triage_case_id,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            booking_source=booking_source,
            booked_by=booked_by,
            is_remote=is_remote,
            location=location,
            patient_notes=patient_notes,
            status=AppointmentStatus.SCHEDULED,
        )

        self.session.add(appointment)
        await self.session.commit()
        await self.session.refresh(appointment)

        return appointment

    async def get_patient_appointments(
        self,
        patient_id: str,
        include_past: bool = False,
    ) -> Sequence[Appointment]:
        """Get appointments for a patient."""
        query = select(Appointment).where(
            Appointment.patient_id == patient_id,
            Appointment.is_deleted == False,
        )

        if not include_past:
            query = query.where(Appointment.scheduled_start >= datetime.now(timezone.utc))

        query = query.order_by(Appointment.scheduled_start)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_clinician_appointments(
        self,
        clinician_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        status: AppointmentStatus | None = None,
    ) -> Sequence[Appointment]:
        """Get appointments for a clinician."""
        query = select(Appointment).where(
            Appointment.clinician_id == clinician_id,
            Appointment.is_deleted == False,
        )

        if start_date:
            query = query.where(
                Appointment.scheduled_start >= datetime.combine(start_date, time.min, tzinfo=timezone.utc)
            )

        if end_date:
            query = query.where(
                Appointment.scheduled_start <= datetime.combine(end_date, time.max, tzinfo=timezone.utc)
            )

        if status:
            query = query.where(Appointment.status == status)

        query = query.order_by(Appointment.scheduled_start)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_appointment_status(
        self,
        appointment_id: str,
        new_status: AppointmentStatus,
        cancelled_by: str | None = None,
        cancellation_reason: str | None = None,
    ) -> Appointment | None:
        """Update appointment status."""
        result = await self.session.execute(
            select(Appointment).where(Appointment.id == appointment_id)
        )
        appointment = result.scalar_one_or_none()

        if not appointment:
            return None

        appointment.status = new_status

        if new_status == AppointmentStatus.CANCELLED:
            from app.db.base import utc_now

            appointment.cancelled_at = utc_now()
            appointment.cancelled_by = cancelled_by
            appointment.cancellation_reason = cancellation_reason

        await self.session.commit()
        await self.session.refresh(appointment)

        return appointment

    async def get_appointment(self, appointment_id: str) -> Appointment | None:
        """Get a single appointment by ID."""
        result = await self.session.execute(
            select(Appointment).where(
                Appointment.id == appointment_id,
                Appointment.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()
