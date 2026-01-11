"""Tests for waiting list monitoring.

Sprint 5 tests covering:
- Deterioration triggers AMBER escalation + audit event
- PHQ-2/GAD-2 scoring
- Check-in escalation triggers
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.monitoring import (
    CheckInStatus,
    EscalationReason,
    WaitingListCheckIn,
)
from app.models.triage_case import TriageTier, TriageCaseStatus
from app.services.monitoring import (
    MonitoringService,
    CheckInNotFoundError,
    CheckInAlreadyCompletedError,
)


class TestDeteriorationEscalation:
    """Tests that deterioration triggers AMBER escalation and audit events."""

    @pytest.mark.asyncio
    async def test_suicidal_ideation_triggers_escalation(self) -> None:
        """Suicidal ideation in check-in triggers immediate escalation."""
        mock_session = AsyncMock()

        # Mock check-in
        mock_checkin = MagicMock()
        mock_checkin.id = "checkin-123"
        mock_checkin.patient_id = "patient-123"
        mock_checkin.triage_case_id = "case-123"
        mock_checkin.status = CheckInStatus.PENDING

        # Mock triage case with GREEN tier
        mock_case = MagicMock()
        mock_case.id = "case-123"
        mock_case.tier = TriageTier.GREEN

        mock_schedule = MagicMock()
        mock_schedule.frequency_days = 7  # Weekly check-ins

        with patch("app.services.monitoring.write_audit_event") as mock_audit:
            # Mock session.execute to return:
            # 1. TriageCase for _escalate_to_amber query
            mock_session.execute = AsyncMock(
                side_effect=[
                    MagicMock(scalar_one_or_none=MagicMock(return_value=mock_case)),  # For TriageCase query
                ]
            )
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()

            service = MonitoringService(mock_session)

            # Mock service methods that do their own queries
            service.get_checkin = AsyncMock(return_value=mock_checkin)
            service.get_monitoring_schedule = AsyncMock(return_value=mock_schedule)

            # Mock the check-in to calculate scores and trigger escalation
            mock_checkin.calculate_scores = MagicMock()
            mock_checkin.check_escalation_needed = MagicMock(
                return_value=(True, EscalationReason.SUICIDAL_IDEATION)
            )

            result = await service.submit_checkin_response(
                checkin_id="checkin-123",
                phq2_q1=2,
                phq2_q2=2,
                gad2_q1=1,
                gad2_q2=1,
                suicidal_ideation=True,  # Critical flag
                self_harm=False,
            )

            # Verify escalation was triggered
            assert mock_checkin.requires_escalation is True
            assert mock_checkin.escalation_reason == EscalationReason.SUICIDAL_IDEATION

    @pytest.mark.asyncio
    async def test_elevated_phq2_triggers_escalation(self) -> None:
        """PHQ-2 score >= 3 triggers escalation."""
        mock_session = AsyncMock()

        mock_checkin = MagicMock()
        mock_checkin.id = "checkin-456"
        mock_checkin.patient_id = "patient-456"
        mock_checkin.triage_case_id = "case-456"
        mock_checkin.status = CheckInStatus.PENDING

        mock_case = MagicMock()
        mock_case.id = "case-456"
        mock_case.tier = TriageTier.GREEN

        mock_schedule = MagicMock()
        mock_schedule.frequency_days = 7  # Weekly check-ins

        with patch("app.services.monitoring.write_audit_event"):
            # Mock session.execute for TriageCase query in _escalate_to_amber
            mock_session.execute = AsyncMock(
                side_effect=[
                    MagicMock(scalar_one_or_none=MagicMock(return_value=mock_case)),  # For TriageCase query
                ]
            )
            mock_session.add = MagicMock()
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()

            service = MonitoringService(mock_session)
            service.get_checkin = AsyncMock(return_value=mock_checkin)
            service.get_monitoring_schedule = AsyncMock(return_value=mock_schedule)

            mock_checkin.calculate_scores = MagicMock()
            mock_checkin.check_escalation_needed = MagicMock(
                return_value=(True, EscalationReason.PHQ2_ELEVATED)
            )

            result = await service.submit_checkin_response(
                checkin_id="checkin-456",
                phq2_q1=2,  # = 4 total (>= 3 threshold)
                phq2_q2=2,
                gad2_q1=1,
                gad2_q2=1,
                suicidal_ideation=False,
                self_harm=False,
            )

            assert mock_checkin.requires_escalation is True
            assert mock_checkin.escalation_reason == EscalationReason.PHQ2_ELEVATED

    @pytest.mark.asyncio
    async def test_case_escalated_to_amber_on_deterioration(self) -> None:
        """Case is escalated from GREEN to AMBER on deterioration."""
        mock_session = AsyncMock()

        mock_checkin = MagicMock()
        mock_checkin.id = "checkin-789"
        mock_checkin.patient_id = "patient-789"
        mock_checkin.triage_case_id = "case-789"
        mock_checkin.phq2_total = 4
        mock_checkin.gad2_total = 2
        mock_checkin.suicidal_ideation = False
        mock_checkin.self_harm = False

        # Mock GREEN tier case
        mock_case = MagicMock()
        mock_case.id = "case-789"
        mock_case.tier = TriageTier.GREEN
        mock_case.self_book_allowed = True

        mock_schedule = MagicMock()
        mock_schedule.frequency_days = 7  # Weekly check-ins

        # Mock session.execute to return the case
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_case))
        )

        with patch("app.services.monitoring.write_audit_event") as mock_audit:
            service = MonitoringService(mock_session)

            await service._escalate_to_amber(
                mock_checkin,
                EscalationReason.PHQ2_ELEVATED,
            )

            # Verify case was escalated
            assert mock_case.tier == TriageTier.AMBER
            assert mock_case.self_book_allowed is False

    @pytest.mark.asyncio
    async def test_already_amber_case_not_re_escalated(self) -> None:
        """AMBER cases are not re-escalated on deterioration."""
        mock_session = AsyncMock()

        mock_checkin = MagicMock()
        mock_checkin.id = "checkin-abc"
        mock_checkin.patient_id = "patient-abc"
        mock_checkin.triage_case_id = "case-abc"

        # Already AMBER tier
        mock_case = MagicMock()
        mock_case.id = "case-abc"
        mock_case.tier = TriageTier.AMBER

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_case))
        )

        with patch("app.services.monitoring.write_audit_event") as mock_audit:
            service = MonitoringService(mock_session)

            await service._escalate_to_amber(
                mock_checkin,
                EscalationReason.PHQ2_ELEVATED,
            )

            # Audit should NOT be called for already-AMBER cases
            mock_audit.assert_not_called()

    @pytest.mark.asyncio
    async def test_audit_event_emitted_on_escalation(self) -> None:
        """Audit event is emitted when case is escalated."""
        mock_session = AsyncMock()

        mock_checkin = MagicMock()
        mock_checkin.id = "checkin-def"
        mock_checkin.patient_id = "patient-def"
        mock_checkin.triage_case_id = "case-def"
        mock_checkin.phq2_total = 5
        mock_checkin.gad2_total = 4
        mock_checkin.suicidal_ideation = False
        mock_checkin.self_harm = False

        mock_case = MagicMock()
        mock_case.id = "case-def"
        mock_case.tier = TriageTier.BLUE

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_case))
        )

        with patch("app.services.monitoring.write_audit_event") as mock_audit:
            service = MonitoringService(mock_session)

            await service._escalate_to_amber(
                mock_checkin,
                EscalationReason.GAD2_ELEVATED,
            )

            # Verify audit event was written
            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args.kwargs

            assert call_kwargs["action"] == "monitoring.escalation"
            assert call_kwargs["action_category"] == "clinical"
            assert call_kwargs["entity_type"] == "triage_case"
            assert "phq2_score" in call_kwargs["metadata"]
            assert "gad2_score" in call_kwargs["metadata"]


class TestCheckInEscalationLogic:
    """Tests for check-in escalation trigger logic."""

    def test_suicidal_ideation_triggers_immediate_escalation(self) -> None:
        """Suicidal ideation triggers immediate escalation."""
        checkin = WaitingListCheckIn(
            id="test-1",
            patient_id="patient-1",
            triage_case_id="case-1",
            phq2_q1=0,
            phq2_q2=0,
            gad2_q1=0,
            gad2_q2=0,
            phq2_total=0,
            gad2_total=0,
            suicidal_ideation=True,
            self_harm=False,
        )

        needs_escalation, reason = checkin.check_escalation_needed()

        assert needs_escalation is True
        assert reason == EscalationReason.SUICIDAL_IDEATION

    def test_self_harm_triggers_escalation(self) -> None:
        """Self-harm triggers escalation."""
        checkin = WaitingListCheckIn(
            id="test-2",
            patient_id="patient-2",
            triage_case_id="case-2",
            phq2_q1=0,
            phq2_q2=0,
            gad2_q1=0,
            gad2_q2=0,
            phq2_total=0,
            gad2_total=0,
            suicidal_ideation=False,
            self_harm=True,
        )

        needs_escalation, reason = checkin.check_escalation_needed()

        assert needs_escalation is True
        assert reason == EscalationReason.SELF_HARM

    def test_phq2_score_3_triggers_escalation(self) -> None:
        """PHQ-2 total >= 3 triggers escalation."""
        checkin = WaitingListCheckIn(
            id="test-3",
            patient_id="patient-3",
            triage_case_id="case-3",
            phq2_q1=2,
            phq2_q2=1,
            gad2_q1=0,
            gad2_q2=0,
            phq2_total=3,  # Threshold
            gad2_total=0,
            suicidal_ideation=False,
            self_harm=False,
        )

        needs_escalation, reason = checkin.check_escalation_needed()

        assert needs_escalation is True
        assert reason == EscalationReason.PHQ2_ELEVATED

    def test_gad2_score_3_triggers_escalation(self) -> None:
        """GAD-2 total >= 3 triggers escalation."""
        checkin = WaitingListCheckIn(
            id="test-4",
            patient_id="patient-4",
            triage_case_id="case-4",
            phq2_q1=0,
            phq2_q2=0,
            gad2_q1=2,
            gad2_q2=1,
            phq2_total=0,
            gad2_total=3,  # Threshold
            suicidal_ideation=False,
            self_harm=False,
        )

        needs_escalation, reason = checkin.check_escalation_needed()

        assert needs_escalation is True
        assert reason == EscalationReason.GAD2_ELEVATED

    def test_low_wellbeing_with_callback_triggers_escalation(self) -> None:
        """Low wellbeing with callback request triggers escalation."""
        checkin = WaitingListCheckIn(
            id="test-5",
            patient_id="patient-5",
            triage_case_id="case-5",
            phq2_q1=0,
            phq2_q2=0,
            gad2_q1=0,
            gad2_q2=0,
            phq2_total=0,
            gad2_total=0,
            suicidal_ideation=False,
            self_harm=False,
            wellbeing_rating=2,  # Low
            wants_callback=True,
        )

        needs_escalation, reason = checkin.check_escalation_needed()

        assert needs_escalation is True
        assert reason == EscalationReason.PATIENT_REQUEST

    def test_normal_scores_no_escalation(self) -> None:
        """Normal scores do not trigger escalation."""
        checkin = WaitingListCheckIn(
            id="test-6",
            patient_id="patient-6",
            triage_case_id="case-6",
            phq2_q1=1,
            phq2_q2=0,
            gad2_q1=0,
            gad2_q2=1,
            phq2_total=1,
            gad2_total=1,
            suicidal_ideation=False,
            self_harm=False,
            wellbeing_rating=7,
            wants_callback=False,
        )

        needs_escalation, reason = checkin.check_escalation_needed()

        assert needs_escalation is False
        assert reason is None


class TestScoreCalculation:
    """Tests for PHQ-2 and GAD-2 score calculation."""

    def test_calculate_phq2_total(self) -> None:
        """PHQ-2 total is correctly calculated."""
        checkin = WaitingListCheckIn(
            id="test-score-1",
            patient_id="patient-score-1",
            triage_case_id="case-score-1",
            phq2_q1=2,
            phq2_q2=3,
            gad2_q1=1,
            gad2_q2=1,
        )

        checkin.calculate_scores()

        assert checkin.phq2_total == 5
        assert checkin.gad2_total == 2

    def test_calculate_with_zeros(self) -> None:
        """Score calculation works with zeros."""
        checkin = WaitingListCheckIn(
            id="test-score-2",
            patient_id="patient-score-2",
            triage_case_id="case-score-2",
            phq2_q1=0,
            phq2_q2=0,
            gad2_q1=0,
            gad2_q2=0,
        )

        checkin.calculate_scores()

        assert checkin.phq2_total == 0
        assert checkin.gad2_total == 0

    def test_calculate_with_none_values(self) -> None:
        """Score calculation handles None values."""
        checkin = WaitingListCheckIn(
            id="test-score-3",
            patient_id="patient-score-3",
            triage_case_id="case-score-3",
            phq2_q1=None,
            phq2_q2=None,
            gad2_q1=2,
            gad2_q2=1,
        )

        checkin.calculate_scores()

        # PHQ-2 total should remain None
        assert checkin.phq2_total is None
        # GAD-2 total should be calculated
        assert checkin.gad2_total == 3
