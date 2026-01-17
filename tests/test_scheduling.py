"""Tests for scheduling and booking.

Sprint 5 tests covering:
- Self-book blocked for RED/AMBER tiers
- Booking rules enforcement
- Appointment lifecycle
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.models.scheduling import (
    AppointmentType,
    BookingSource,
)
from app.models.triage_case import TriageTier
from app.services.scheduling import (
    SchedulingService,
    SelfBookBlockedError,
    SELF_BOOK_ALLOWED_TIERS,
)


class TestSelfBookBlocking:
    """Tests that self-booking is blocked for RED/AMBER tiers."""

    @pytest.mark.asyncio
    async def test_red_tier_cannot_self_book(self) -> None:
        """RED tier patients cannot self-book appointments."""
        mock_session = AsyncMock()

        # Mock triage case with RED tier
        mock_case = MagicMock()
        mock_case.tier = "red"
        mock_case.self_book_allowed = True

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_case))
        )

        service = SchedulingService(mock_session)
        allowed, reason = await service.check_self_book_allowed(
            triage_case_id="test-case-id",
            appointment_type_id="test-type-id",
        )

        assert allowed is False
        assert "RED" in reason.upper()

    @pytest.mark.asyncio
    async def test_amber_tier_cannot_self_book(self) -> None:
        """AMBER tier patients cannot self-book appointments."""
        mock_session = AsyncMock()

        # Mock triage case with AMBER tier
        mock_case = MagicMock()
        mock_case.tier = "amber"
        mock_case.self_book_allowed = True

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_case))
        )

        service = SchedulingService(mock_session)
        allowed, reason = await service.check_self_book_allowed(
            triage_case_id="test-case-id",
            appointment_type_id="test-type-id",
        )

        assert allowed is False
        assert "AMBER" in reason.upper()

    @pytest.mark.asyncio
    async def test_green_tier_can_self_book(self) -> None:
        """GREEN tier patients can self-book appointments."""
        mock_session = AsyncMock()

        # Mock triage case with GREEN tier
        mock_case = MagicMock()
        mock_case.tier = "green"
        mock_case.self_book_allowed = True

        # Mock appointment type that allows GREEN
        mock_type = MagicMock()
        mock_type.self_book_tiers = ["green", "blue"]
        mock_type.can_self_book = MagicMock(return_value=True)

        # Set up execute to return case first, then type
        mock_session.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=mock_case)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=mock_type)),
            ]
        )

        service = SchedulingService(mock_session)
        allowed, reason = await service.check_self_book_allowed(
            triage_case_id="test-case-id",
            appointment_type_id="test-type-id",
        )

        assert allowed is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_blue_tier_can_self_book(self) -> None:
        """BLUE tier patients can self-book appointments."""
        mock_session = AsyncMock()

        # Mock triage case with BLUE tier
        mock_case = MagicMock()
        mock_case.tier = "blue"
        mock_case.self_book_allowed = True

        # Mock appointment type that allows BLUE
        mock_type = MagicMock()
        mock_type.self_book_tiers = ["green", "blue"]
        mock_type.can_self_book = MagicMock(return_value=True)

        mock_session.execute = AsyncMock(
            side_effect=[
                MagicMock(scalar_one_or_none=MagicMock(return_value=mock_case)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=mock_type)),
            ]
        )

        service = SchedulingService(mock_session)
        allowed, reason = await service.check_self_book_allowed(
            triage_case_id="test-case-id",
            appointment_type_id="test-type-id",
        )

        assert allowed is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_case_level_self_book_disabled(self) -> None:
        """Self-booking blocked if case-level flag is disabled."""
        mock_session = AsyncMock()

        # Mock triage case with self_book_allowed=False
        mock_case = MagicMock()
        mock_case.tier = "green"  # Would normally allow
        mock_case.self_book_allowed = False

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_case))
        )

        service = SchedulingService(mock_session)
        allowed, reason = await service.check_self_book_allowed(
            triage_case_id="test-case-id",
            appointment_type_id="test-type-id",
        )

        assert allowed is False
        assert "disabled" in reason.lower()

    @pytest.mark.asyncio
    async def test_booking_raises_error_for_blocked_tier(self) -> None:
        """Booking attempt raises SelfBookBlockedError for blocked tiers."""
        mock_session = AsyncMock()

        service = SchedulingService(mock_session)

        # Mock check_self_book_allowed to return False
        service.check_self_book_allowed = AsyncMock(
            return_value=(False, "Self-booking not allowed for RED tier")
        )

        with pytest.raises(SelfBookBlockedError):
            await service.book_appointment(
                patient_id="test-patient",
                clinician_id="test-clinician",
                appointment_type_id="test-type",
                scheduled_start=datetime.now() + timedelta(days=1),
                triage_case_id="test-case",
                booking_source=BookingSource.PATIENT_SELF_BOOK,
            )

    def test_self_book_allowed_tiers_constant(self) -> None:
        """Verify SELF_BOOK_ALLOWED_TIERS only includes GREEN and BLUE."""
        assert TriageTier.GREEN in SELF_BOOK_ALLOWED_TIERS
        assert TriageTier.BLUE in SELF_BOOK_ALLOWED_TIERS
        assert TriageTier.RED not in SELF_BOOK_ALLOWED_TIERS
        assert TriageTier.AMBER not in SELF_BOOK_ALLOWED_TIERS


class TestAppointmentTypeBookingRules:
    """Tests for appointment type booking rules."""

    def test_can_self_book_checks_tier(self) -> None:
        """AppointmentType.can_self_book correctly checks tier."""
        # Create mock appointment type
        apt_type = AppointmentType(
            id="test-id",
            code="INITIAL_ASSESSMENT",
            name="Initial Assessment",
            duration_minutes=50,
            buffer_minutes=10,
            self_book_tiers=["green", "blue"],
            required_specialties=[],
            is_bookable=True,
        )

        assert apt_type.can_self_book("green") is True
        assert apt_type.can_self_book("GREEN") is True
        assert apt_type.can_self_book("blue") is True
        assert apt_type.can_self_book("BLUE") is True
        assert apt_type.can_self_book("red") is False
        assert apt_type.can_self_book("amber") is False

    def test_restricted_appointment_type(self) -> None:
        """Appointment types can be restricted to staff-only booking."""
        # Create appointment type with no self-book tiers
        apt_type = AppointmentType(
            id="test-id",
            code="CRISIS_ASSESSMENT",
            name="Crisis Assessment",
            duration_minutes=60,
            buffer_minutes=15,
            self_book_tiers=[],  # Staff only
            required_specialties=["crisis_intervention"],
            is_bookable=True,
        )

        assert apt_type.can_self_book("green") is False
        assert apt_type.can_self_book("blue") is False
        assert apt_type.can_self_book("red") is False
        assert apt_type.can_self_book("amber") is False


class TestStaffBooking:
    """Tests for staff-initiated bookings."""

    @pytest.mark.asyncio
    async def test_staff_can_book_for_red_tier(self) -> None:
        """Staff can book appointments for RED tier patients."""
        mock_session = AsyncMock()

        # Mock appointment type
        mock_type = MagicMock()
        mock_type.duration_minutes = 50
        mock_type.buffer_minutes = 10

        # Set up mocks
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_type))
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        service = SchedulingService(mock_session)

        # Mock _get_appointments_in_range to return empty list (no conflicts)
        service._get_appointments_in_range = AsyncMock(return_value=[])

        # Staff booking should not check self-book restrictions
        appointment = await service.book_appointment(
            patient_id="test-patient",
            clinician_id="test-clinician",
            appointment_type_id="test-type",
            scheduled_start=datetime.now() + timedelta(days=1),
            triage_case_id="test-case",
            booking_source=BookingSource.STAFF_BOOKED,
            booked_by="staff-user-id",
        )

        # Should succeed without checking tier restrictions
        assert mock_session.add.called


class TestCancellationPolicy:
    """Tests for cancellation and rescheduling policy enforcement."""

    def test_red_tier_cannot_self_cancel(self) -> None:
        """RED tier patients cannot immediately cancel - requires request."""
        from app.booking.policy import can_patient_self_cancel

        allowed, message, requires_request = can_patient_self_cancel(
            tier="RED",
            hours_until_appointment=48,  # Even far in advance
        )

        assert allowed is False
        assert requires_request is True
        assert "999" in message or "A&E" in message  # Safety messaging

    def test_amber_tier_cannot_self_cancel(self) -> None:
        """AMBER tier patients cannot immediately cancel - requires request."""
        from app.booking.policy import can_patient_self_cancel

        allowed, message, requires_request = can_patient_self_cancel(
            tier="AMBER",
            hours_until_appointment=48,
        )

        assert allowed is False
        assert requires_request is True
        assert "contact" in message.lower()

    def test_green_tier_can_self_cancel_over_24h(self) -> None:
        """GREEN tier can immediately cancel if >24h before appointment."""
        from app.booking.policy import can_patient_self_cancel

        allowed, message, requires_request = can_patient_self_cancel(
            tier="GREEN",
            hours_until_appointment=48,
        )

        assert allowed is True
        assert requires_request is False
        assert "cancelled" in message.lower()

    def test_green_tier_cannot_self_cancel_under_24h(self) -> None:
        """GREEN tier cannot immediately cancel if <24h - requires request."""
        from app.booking.policy import can_patient_self_cancel

        allowed, message, requires_request = can_patient_self_cancel(
            tier="GREEN",
            hours_until_appointment=12,
        )

        assert allowed is False
        assert requires_request is True
        assert "24" in message  # References 24h window

    def test_blue_tier_can_self_cancel_over_24h(self) -> None:
        """BLUE tier can immediately cancel if >24h before appointment."""
        from app.booking.policy import can_patient_self_cancel

        allowed, message, requires_request = can_patient_self_cancel(
            tier="BLUE",
            hours_until_appointment=48,
        )

        assert allowed is True
        assert requires_request is False

    def test_blue_tier_cannot_self_cancel_under_24h(self) -> None:
        """BLUE tier cannot immediately cancel if <24h - requires request."""
        from app.booking.policy import can_patient_self_cancel

        allowed, message, requires_request = can_patient_self_cancel(
            tier="BLUE",
            hours_until_appointment=12,
        )

        assert allowed is False
        assert requires_request is True


class TestReschedulePolicy:
    """Tests for rescheduling policy enforcement."""

    def test_max_reschedule_limit_enforced(self) -> None:
        """Max reschedule count blocks further reschedules."""
        from app.booking.policy import can_patient_self_reschedule

        allowed, message, requires_request = can_patient_self_reschedule(
            tier="GREEN",
            hours_until_appointment=48,
            current_reschedule_count=2,  # At limit
        )

        assert allowed is False
        assert requires_request is True
        assert "maximum" in message.lower()

    def test_red_tier_cannot_self_reschedule(self) -> None:
        """RED tier patients cannot self-reschedule."""
        from app.booking.policy import can_patient_self_reschedule

        allowed, message, requires_request = can_patient_self_reschedule(
            tier="RED",
            hours_until_appointment=48,
            current_reschedule_count=0,
        )

        assert allowed is False
        assert requires_request is True

    def test_amber_tier_cannot_self_reschedule(self) -> None:
        """AMBER tier patients cannot self-reschedule."""
        from app.booking.policy import can_patient_self_reschedule

        allowed, message, requires_request = can_patient_self_reschedule(
            tier="AMBER",
            hours_until_appointment=48,
            current_reschedule_count=0,
        )

        assert allowed is False
        assert requires_request is True

    def test_green_tier_can_self_reschedule_over_24h(self) -> None:
        """GREEN tier can self-reschedule if >24h and under limit."""
        from app.booking.policy import can_patient_self_reschedule

        allowed, message, requires_request = can_patient_self_reschedule(
            tier="GREEN",
            hours_until_appointment=48,
            current_reschedule_count=1,  # Under limit
        )

        assert allowed is True
        assert requires_request is False

    def test_green_tier_cannot_self_reschedule_under_24h(self) -> None:
        """GREEN tier cannot self-reschedule if <24h."""
        from app.booking.policy import can_patient_self_reschedule

        allowed, message, requires_request = can_patient_self_reschedule(
            tier="GREEN",
            hours_until_appointment=12,
            current_reschedule_count=0,
        )

        assert allowed is False
        assert requires_request is True


class TestSafetyPhraseDetection:
    """Tests for safety concern detection in cancellation reasons."""

    def test_detects_direct_safety_phrases(self) -> None:
        """Detects direct safety concern phrases."""
        from app.booking.policy import check_safety_concern_in_reason

        assert check_safety_concern_in_reason("I feel unsafe") is True
        assert check_safety_concern_in_reason("I might harm myself") is True
        assert check_safety_concern_in_reason("having suicidal thoughts") is True
        assert check_safety_concern_in_reason("I don't want to live anymore") is True

    def test_case_insensitive_detection(self) -> None:
        """Detection is case insensitive."""
        from app.booking.policy import check_safety_concern_in_reason

        assert check_safety_concern_in_reason("I FEEL UNSAFE") is True
        assert check_safety_concern_in_reason("Suicidal") is True

    def test_no_false_positives_on_normal_reasons(self) -> None:
        """Normal cancellation reasons don't trigger safety flag."""
        from app.booking.policy import check_safety_concern_in_reason

        assert check_safety_concern_in_reason("Work conflict") is False
        assert check_safety_concern_in_reason("Feeling better") is False
        assert check_safety_concern_in_reason("Scheduling issue") is False
        assert check_safety_concern_in_reason(None) is False
        assert check_safety_concern_in_reason("") is False
