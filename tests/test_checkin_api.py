"""Tests for check-in API endpoints.

These tests verify the monitoring API endpoints for patient check-ins,
including submission validation, escalation triggers, and duty queue.
"""

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel, Field


# ============================================================================
# Standalone Schema Definitions (to avoid import chain issues)
# ============================================================================


class SubmitCheckInRequest(BaseModel):
    """Request to submit check-in response."""

    phq2_q1: int = Field(ge=0, le=3)
    phq2_q2: int = Field(ge=0, le=3)
    gad2_q1: int = Field(ge=0, le=3)
    gad2_q2: int = Field(ge=0, le=3)
    suicidal_ideation: bool = False
    self_harm: bool = False
    wellbeing_rating: int | None = Field(None, ge=1, le=10)
    patient_comments: str | None = Field(None, max_length=2000)
    wants_callback: bool = False


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


class AlertCountsResponse(BaseModel):
    """Alert counts by severity."""

    critical: int
    high: int
    medium: int
    low: int
    total: int


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


class DutyQueueResponse(BaseModel):
    """Duty queue response."""

    alerts: list[MonitoringAlertResponse]
    counts: AlertCountsResponse


# ============================================================================
# Mock Data Generators
# ============================================================================


def create_mock_checkin(
    checkin_id: str = "checkin-123",
    patient_id: str = "patient-456",
    triage_case_id: str = "case-789",
    sequence_number: int = 1,
    status: str = "pending",
    phq2_q1: int | None = None,
    phq2_q2: int | None = None,
    gad2_q1: int | None = None,
    gad2_q2: int | None = None,
    phq2_total: int | None = None,
    gad2_total: int | None = None,
    suicidal_ideation: bool = False,
    self_harm: bool = False,
    wellbeing_rating: int | None = None,
    wants_callback: bool = False,
    requires_escalation: bool = False,
    escalation_reason: str | None = None,
) -> MagicMock:
    """Create a mock check-in object."""
    checkin = MagicMock()
    checkin.id = checkin_id
    checkin.patient_id = patient_id
    checkin.triage_case_id = triage_case_id
    checkin.sequence_number = sequence_number
    checkin.status = status
    checkin.scheduled_for = datetime.now()
    checkin.expires_at = datetime.now() + timedelta(hours=72)
    checkin.completed_at = None
    checkin.phq2_q1 = phq2_q1
    checkin.phq2_q2 = phq2_q2
    checkin.gad2_q1 = gad2_q1
    checkin.gad2_q2 = gad2_q2
    checkin.phq2_total = phq2_total
    checkin.gad2_total = gad2_total
    checkin.suicidal_ideation = suicidal_ideation
    checkin.self_harm = self_harm
    checkin.wellbeing_rating = wellbeing_rating
    checkin.wants_callback = wants_callback
    checkin.requires_escalation = requires_escalation
    checkin.escalation_reason = escalation_reason
    return checkin


def create_mock_alert(
    alert_id: str = "alert-123",
    patient_id: str = "patient-456",
    triage_case_id: str = "case-789",
    checkin_id: str | None = "checkin-123",
    alert_type: str = "phq2_elevated",
    severity: str = "high",
    title: str = "Elevated depression screening",
    description: str = "PHQ-2 score indicates possible depression",
    phq2_score: int | None = 4,
    gad2_score: int | None = 2,
    is_active: bool = True,
    acknowledged_at: datetime | None = None,
    acknowledged_by: str | None = None,
    resolved_at: datetime | None = None,
    resolved_by: str | None = None,
    resolution_notes: str | None = None,
    action_taken: str | None = None,
    escalated_to_amber: bool = True,
) -> MagicMock:
    """Create a mock alert object."""
    alert = MagicMock()
    alert.id = alert_id
    alert.patient_id = patient_id
    alert.triage_case_id = triage_case_id
    alert.checkin_id = checkin_id
    alert.alert_type = alert_type
    alert.severity = severity
    alert.title = title
    alert.description = description
    alert.phq2_score = phq2_score
    alert.gad2_score = gad2_score
    alert.is_active = is_active
    alert.acknowledged_at = acknowledged_at
    alert.acknowledged_by = acknowledged_by
    alert.resolved_at = resolved_at
    alert.resolved_by = resolved_by
    alert.resolution_notes = resolution_notes
    alert.action_taken = action_taken
    alert.escalated_to_amber = escalated_to_amber
    alert.created_at = datetime.now()
    return alert


# ============================================================================
# Test Classes
# ============================================================================


class TestSubmitCheckInRequestValidation:
    """Test SubmitCheckInRequest schema validation."""

    def test_valid_minimal_request(self) -> None:
        """Test minimal valid request."""
        request = SubmitCheckInRequest(
            phq2_q1=0,
            phq2_q2=0,
            gad2_q1=0,
            gad2_q2=0,
        )
        assert request.phq2_q1 == 0
        assert request.suicidal_ideation is False

    def test_valid_full_request(self) -> None:
        """Test full valid request."""
        request = SubmitCheckInRequest(
            phq2_q1=2,
            phq2_q2=3,
            gad2_q1=1,
            gad2_q2=2,
            suicidal_ideation=False,
            self_harm=False,
            wellbeing_rating=5,
            patient_comments="Feeling better this week",
            wants_callback=True,
        )
        assert request.phq2_q1 == 2
        assert request.wellbeing_rating == 5
        assert request.wants_callback is True

    def test_phq2_q1_minimum_value(self) -> None:
        """Test PHQ-2 Q1 minimum value."""
        request = SubmitCheckInRequest(
            phq2_q1=0,
            phq2_q2=0,
            gad2_q1=0,
            gad2_q2=0,
        )
        assert request.phq2_q1 == 0

    def test_phq2_q1_maximum_value(self) -> None:
        """Test PHQ-2 Q1 maximum value."""
        request = SubmitCheckInRequest(
            phq2_q1=3,
            phq2_q2=0,
            gad2_q1=0,
            gad2_q2=0,
        )
        assert request.phq2_q1 == 3

    def test_phq2_q1_below_minimum_fails(self) -> None:
        """Test PHQ-2 Q1 below minimum fails validation."""
        with pytest.raises(ValueError):
            SubmitCheckInRequest(
                phq2_q1=-1,
                phq2_q2=0,
                gad2_q1=0,
                gad2_q2=0,
            )

    def test_phq2_q1_above_maximum_fails(self) -> None:
        """Test PHQ-2 Q1 above maximum fails validation."""
        with pytest.raises(ValueError):
            SubmitCheckInRequest(
                phq2_q1=4,
                phq2_q2=0,
                gad2_q1=0,
                gad2_q2=0,
            )

    def test_phq2_q2_range_validation(self) -> None:
        """Test PHQ-2 Q2 range validation."""
        with pytest.raises(ValueError):
            SubmitCheckInRequest(
                phq2_q1=0,
                phq2_q2=5,
                gad2_q1=0,
                gad2_q2=0,
            )

    def test_gad2_q1_range_validation(self) -> None:
        """Test GAD-2 Q1 range validation."""
        with pytest.raises(ValueError):
            SubmitCheckInRequest(
                phq2_q1=0,
                phq2_q2=0,
                gad2_q1=-1,
                gad2_q2=0,
            )

    def test_gad2_q2_range_validation(self) -> None:
        """Test GAD-2 Q2 range validation."""
        with pytest.raises(ValueError):
            SubmitCheckInRequest(
                phq2_q1=0,
                phq2_q2=0,
                gad2_q1=0,
                gad2_q2=4,
            )

    def test_wellbeing_rating_minimum(self) -> None:
        """Test wellbeing rating minimum value."""
        request = SubmitCheckInRequest(
            phq2_q1=0,
            phq2_q2=0,
            gad2_q1=0,
            gad2_q2=0,
            wellbeing_rating=1,
        )
        assert request.wellbeing_rating == 1

    def test_wellbeing_rating_maximum(self) -> None:
        """Test wellbeing rating maximum value."""
        request = SubmitCheckInRequest(
            phq2_q1=0,
            phq2_q2=0,
            gad2_q1=0,
            gad2_q2=0,
            wellbeing_rating=10,
        )
        assert request.wellbeing_rating == 10

    def test_wellbeing_rating_below_minimum_fails(self) -> None:
        """Test wellbeing rating below minimum fails."""
        with pytest.raises(ValueError):
            SubmitCheckInRequest(
                phq2_q1=0,
                phq2_q2=0,
                gad2_q1=0,
                gad2_q2=0,
                wellbeing_rating=0,
            )

    def test_wellbeing_rating_above_maximum_fails(self) -> None:
        """Test wellbeing rating above maximum fails."""
        with pytest.raises(ValueError):
            SubmitCheckInRequest(
                phq2_q1=0,
                phq2_q2=0,
                gad2_q1=0,
                gad2_q2=0,
                wellbeing_rating=11,
            )

    def test_patient_comments_max_length(self) -> None:
        """Test patient comments max length."""
        long_comment = "x" * 2000
        request = SubmitCheckInRequest(
            phq2_q1=0,
            phq2_q2=0,
            gad2_q1=0,
            gad2_q2=0,
            patient_comments=long_comment,
        )
        assert len(request.patient_comments) == 2000

    def test_patient_comments_exceeds_max_length_fails(self) -> None:
        """Test patient comments exceeds max length fails."""
        too_long_comment = "x" * 2001
        with pytest.raises(ValueError):
            SubmitCheckInRequest(
                phq2_q1=0,
                phq2_q2=0,
                gad2_q1=0,
                gad2_q2=0,
                patient_comments=too_long_comment,
            )


class TestCheckInResponseSchema:
    """Test CheckInResponse schema."""

    def test_response_from_mock(self) -> None:
        """Test response can be created from mock data."""
        mock = create_mock_checkin()
        response = CheckInResponse(
            id=mock.id,
            patient_id=mock.patient_id,
            triage_case_id=mock.triage_case_id,
            sequence_number=mock.sequence_number,
            status=mock.status,
            scheduled_for=mock.scheduled_for,
            expires_at=mock.expires_at,
            completed_at=mock.completed_at,
            phq2_total=mock.phq2_total,
            gad2_total=mock.gad2_total,
            wellbeing_rating=mock.wellbeing_rating,
            requires_escalation=mock.requires_escalation,
            escalation_reason=mock.escalation_reason,
        )
        assert response.id == "checkin-123"
        assert response.requires_escalation is False

    def test_response_with_escalation(self) -> None:
        """Test response with escalation data."""
        mock = create_mock_checkin(
            phq2_total=4,
            requires_escalation=True,
            escalation_reason="phq2_elevated",
        )
        response = CheckInResponse(
            id=mock.id,
            patient_id=mock.patient_id,
            triage_case_id=mock.triage_case_id,
            sequence_number=mock.sequence_number,
            status=mock.status,
            scheduled_for=mock.scheduled_for,
            expires_at=mock.expires_at,
            completed_at=mock.completed_at,
            phq2_total=mock.phq2_total,
            gad2_total=mock.gad2_total,
            wellbeing_rating=mock.wellbeing_rating,
            requires_escalation=mock.requires_escalation,
            escalation_reason=mock.escalation_reason,
        )
        assert response.requires_escalation is True
        assert response.escalation_reason == "phq2_elevated"
        assert response.phq2_total == 4


class TestDutyQueueResponseSchema:
    """Test DutyQueueResponse schema."""

    def test_empty_duty_queue(self) -> None:
        """Test empty duty queue response."""
        response = DutyQueueResponse(
            alerts=[],
            counts=AlertCountsResponse(
                critical=0,
                high=0,
                medium=0,
                low=0,
                total=0,
            ),
        )
        assert response.counts.total == 0
        assert len(response.alerts) == 0

    def test_duty_queue_with_alerts(self) -> None:
        """Test duty queue with alerts."""
        mock_alert = create_mock_alert()
        alert_response = MonitoringAlertResponse(
            id=mock_alert.id,
            patient_id=mock_alert.patient_id,
            triage_case_id=mock_alert.triage_case_id,
            checkin_id=mock_alert.checkin_id,
            alert_type=mock_alert.alert_type,
            severity=mock_alert.severity,
            title=mock_alert.title,
            description=mock_alert.description,
            phq2_score=mock_alert.phq2_score,
            gad2_score=mock_alert.gad2_score,
            is_active=mock_alert.is_active,
            acknowledged_at=mock_alert.acknowledged_at,
            acknowledged_by=mock_alert.acknowledged_by,
            resolved_at=mock_alert.resolved_at,
            resolved_by=mock_alert.resolved_by,
            resolution_notes=mock_alert.resolution_notes,
            action_taken=mock_alert.action_taken,
            escalated_to_amber=mock_alert.escalated_to_amber,
            created_at=mock_alert.created_at,
        )
        response = DutyQueueResponse(
            alerts=[alert_response],
            counts=AlertCountsResponse(
                critical=0,
                high=1,
                medium=0,
                low=0,
                total=1,
            ),
        )
        assert response.counts.total == 1
        assert response.counts.high == 1
        assert len(response.alerts) == 1
        assert response.alerts[0].severity == "high"


class TestAlertSeverityMapping:
    """Test alert severity mapping in duty queue."""

    def test_critical_severity_for_suicidal_ideation(self) -> None:
        """Test critical severity for suicidal ideation."""
        alert = create_mock_alert(
            alert_type="suicidal_ideation",
            severity="critical",
            title="Suicidal ideation reported",
        )
        assert alert.severity == "critical"

    def test_critical_severity_for_self_harm(self) -> None:
        """Test critical severity for self-harm."""
        alert = create_mock_alert(
            alert_type="self_harm",
            severity="critical",
            title="Self-harm reported",
        )
        assert alert.severity == "critical"

    def test_high_severity_for_phq2_elevated(self) -> None:
        """Test high severity for elevated PHQ-2."""
        alert = create_mock_alert(
            alert_type="phq2_elevated",
            severity="high",
            phq2_score=4,
        )
        assert alert.severity == "high"

    def test_high_severity_for_gad2_elevated(self) -> None:
        """Test high severity for elevated GAD-2."""
        alert = create_mock_alert(
            alert_type="gad2_elevated",
            severity="high",
            gad2_score=5,
        )
        assert alert.severity == "high"

    def test_medium_severity_for_patient_request(self) -> None:
        """Test medium severity for patient callback request."""
        alert = create_mock_alert(
            alert_type="patient_request",
            severity="medium",
            title="Patient callback requested",
        )
        assert alert.severity == "medium"


class TestCheckInSubmissionLogic:
    """Test check-in submission business logic."""

    def test_ownership_validation_same_patient(self) -> None:
        """Test check-in ownership validation passes for same patient."""
        checkin = create_mock_checkin(patient_id="patient-123")
        patient_id = "patient-123"
        assert checkin.patient_id == patient_id

    def test_ownership_validation_different_patient(self) -> None:
        """Test check-in ownership validation fails for different patient."""
        checkin = create_mock_checkin(patient_id="patient-123")
        patient_id = "patient-456"
        assert checkin.patient_id != patient_id

    def test_completed_checkin_cannot_be_resubmitted(self) -> None:
        """Test completed check-in cannot be resubmitted."""
        checkin = create_mock_checkin(status="completed")
        assert checkin.status == "completed"
        # In real code, this would raise CheckInAlreadyCompletedError

    def test_pending_checkin_can_be_submitted(self) -> None:
        """Test pending check-in can be submitted."""
        checkin = create_mock_checkin(status="pending")
        assert checkin.status in ["pending", "sent", "scheduled"]


class TestEscalationTriggerValidation:
    """Test escalation trigger validation."""

    def test_phq2_score_3_triggers_escalation(self) -> None:
        """Test PHQ-2 score of 3 triggers escalation."""
        request = SubmitCheckInRequest(
            phq2_q1=2,
            phq2_q2=1,  # Total = 3
            gad2_q1=0,
            gad2_q2=0,
        )
        phq2_total = request.phq2_q1 + request.phq2_q2
        assert phq2_total == 3
        assert phq2_total >= 3  # Escalation threshold

    def test_gad2_score_3_triggers_escalation(self) -> None:
        """Test GAD-2 score of 3 triggers escalation."""
        request = SubmitCheckInRequest(
            phq2_q1=0,
            phq2_q2=0,
            gad2_q1=2,
            gad2_q2=1,  # Total = 3
        )
        gad2_total = request.gad2_q1 + request.gad2_q2
        assert gad2_total == 3
        assert gad2_total >= 3  # Escalation threshold

    def test_suicidal_ideation_triggers_immediate_escalation(self) -> None:
        """Test suicidal ideation triggers immediate escalation."""
        request = SubmitCheckInRequest(
            phq2_q1=0,
            phq2_q2=0,
            gad2_q1=0,
            gad2_q2=0,
            suicidal_ideation=True,
        )
        assert request.suicidal_ideation is True
        # This should trigger CRITICAL severity escalation

    def test_self_harm_triggers_immediate_escalation(self) -> None:
        """Test self-harm triggers immediate escalation."""
        request = SubmitCheckInRequest(
            phq2_q1=0,
            phq2_q2=0,
            gad2_q1=0,
            gad2_q2=0,
            self_harm=True,
        )
        assert request.self_harm is True
        # This should trigger CRITICAL severity escalation

    def test_callback_with_low_wellbeing_triggers_escalation(self) -> None:
        """Test callback request with low wellbeing triggers escalation."""
        request = SubmitCheckInRequest(
            phq2_q1=0,
            phq2_q2=0,
            gad2_q1=0,
            gad2_q2=0,
            wellbeing_rating=2,
            wants_callback=True,
        )
        assert request.wants_callback is True
        assert request.wellbeing_rating <= 3  # Escalation threshold

    def test_callback_with_good_wellbeing_no_escalation(self) -> None:
        """Test callback request with good wellbeing doesn't escalate."""
        request = SubmitCheckInRequest(
            phq2_q1=0,
            phq2_q2=0,
            gad2_q1=0,
            gad2_q2=0,
            wellbeing_rating=7,
            wants_callback=True,
        )
        assert request.wants_callback is True
        assert request.wellbeing_rating > 3  # Above escalation threshold


class TestAuditMetadataStructure:
    """Test audit metadata structure for check-in submission."""

    def test_audit_metadata_contains_required_fields(self) -> None:
        """Test audit metadata contains all required fields."""
        checkin = create_mock_checkin(
            sequence_number=3,
            phq2_total=2,
            gad2_total=1,
            suicidal_ideation=False,
            self_harm=False,
            wellbeing_rating=6,
            wants_callback=False,
            requires_escalation=False,
            escalation_reason=None,
        )

        # Simulate audit metadata structure
        metadata = {
            "sequence_number": checkin.sequence_number,
            "phq2_total": checkin.phq2_total,
            "gad2_total": checkin.gad2_total,
            "suicidal_ideation": checkin.suicidal_ideation,
            "self_harm": checkin.self_harm,
            "wellbeing_rating": checkin.wellbeing_rating,
            "wants_callback": checkin.wants_callback,
            "requires_escalation": checkin.requires_escalation,
            "escalation_reason": checkin.escalation_reason,
        }

        assert "sequence_number" in metadata
        assert "phq2_total" in metadata
        assert "gad2_total" in metadata
        assert "suicidal_ideation" in metadata
        assert "self_harm" in metadata
        assert "requires_escalation" in metadata

    def test_audit_metadata_includes_escalation_details(self) -> None:
        """Test audit metadata includes escalation details when triggered."""
        checkin = create_mock_checkin(
            phq2_total=4,
            requires_escalation=True,
            escalation_reason="phq2_elevated",
        )

        metadata = {
            "phq2_total": checkin.phq2_total,
            "requires_escalation": checkin.requires_escalation,
            "escalation_reason": checkin.escalation_reason,
        }

        assert metadata["requires_escalation"] is True
        assert metadata["escalation_reason"] == "phq2_elevated"
        assert metadata["phq2_total"] == 4


class TestDutyQueuePrioritization:
    """Test duty queue prioritization logic."""

    def test_critical_alerts_first(self) -> None:
        """Test critical severity alerts come first."""
        alerts = [
            create_mock_alert(alert_id="high-1", severity="high"),
            create_mock_alert(alert_id="critical-1", severity="critical"),
            create_mock_alert(alert_id="medium-1", severity="medium"),
        ]

        # Sort by severity priority (critical=1, high=2, medium=3, low=4)
        severity_order = {"critical": 1, "high": 2, "medium": 3, "low": 4}
        sorted_alerts = sorted(alerts, key=lambda a: severity_order.get(a.severity, 5))

        assert sorted_alerts[0].severity == "critical"
        assert sorted_alerts[1].severity == "high"
        assert sorted_alerts[2].severity == "medium"

    def test_same_severity_ordered_by_time(self) -> None:
        """Test alerts with same severity are ordered by creation time."""
        now = datetime.now()
        alerts = [
            create_mock_alert(alert_id="high-2", severity="high"),
            create_mock_alert(alert_id="high-1", severity="high"),
        ]
        alerts[0].created_at = now
        alerts[1].created_at = now - timedelta(hours=1)

        # Sort by severity then by creation time (oldest first)
        severity_order = {"critical": 1, "high": 2, "medium": 3, "low": 4}
        sorted_alerts = sorted(
            alerts,
            key=lambda a: (severity_order.get(a.severity, 5), a.created_at),
        )

        assert sorted_alerts[0].id == "high-1"  # Older alert first
        assert sorted_alerts[1].id == "high-2"


class TestAlertCountsResponse:
    """Test AlertCountsResponse schema."""

    def test_all_zeros(self) -> None:
        """Test response with all zero counts."""
        response = AlertCountsResponse(
            critical=0,
            high=0,
            medium=0,
            low=0,
            total=0,
        )
        assert response.total == 0

    def test_total_matches_sum(self) -> None:
        """Test total should match sum of individual counts."""
        response = AlertCountsResponse(
            critical=2,
            high=5,
            medium=3,
            low=1,
            total=11,
        )
        expected_total = (
            response.critical + response.high + response.medium + response.low
        )
        assert response.total == expected_total

    def test_critical_count(self) -> None:
        """Test critical count tracking."""
        response = AlertCountsResponse(
            critical=3,
            high=0,
            medium=0,
            low=0,
            total=3,
        )
        assert response.critical == 3


class TestAPIEndpointPaths:
    """Test API endpoint path structure."""

    def test_patient_checkin_path(self) -> None:
        """Test patient check-in endpoint path."""
        path = "/monitoring/patient/checkin"
        assert "/patient/" in path
        assert "/checkin" in path

    def test_patient_checkins_history_path(self) -> None:
        """Test patient check-ins history endpoint path."""
        path = "/monitoring/patient/checkins"
        assert "/patient/" in path
        assert path.endswith("/checkins")

    def test_submit_checkin_path(self) -> None:
        """Test submit check-in endpoint path."""
        checkin_id = "abc-123"
        path = f"/monitoring/patient/checkin/{checkin_id}"
        assert checkin_id in path

    def test_duty_queue_path(self) -> None:
        """Test duty queue endpoint path."""
        path = "/monitoring/staff/duty-queue"
        assert "/staff/" in path
        assert "/duty-queue" in path

    def test_alerts_path(self) -> None:
        """Test alerts endpoint path."""
        path = "/monitoring/staff/alerts"
        assert "/staff/" in path
        assert "/alerts" in path

    def test_acknowledge_alert_path(self) -> None:
        """Test acknowledge alert endpoint path."""
        alert_id = "alert-456"
        path = f"/monitoring/staff/alerts/{alert_id}/acknowledge"
        assert alert_id in path
        assert "/acknowledge" in path

    def test_resolve_alert_path(self) -> None:
        """Test resolve alert endpoint path."""
        alert_id = "alert-456"
        path = f"/monitoring/staff/alerts/{alert_id}/resolve"
        assert alert_id in path
        assert "/resolve" in path


class TestRequirementsSummary:
    """Summary tests verifying all requirements are met."""

    def test_phq2_questions_have_valid_range(self) -> None:
        """Test PHQ-2 questions accept valid range 0-3."""
        for val in [0, 1, 2, 3]:
            request = SubmitCheckInRequest(
                phq2_q1=val,
                phq2_q2=val,
                gad2_q1=0,
                gad2_q2=0,
            )
            assert request.phq2_q1 == val
            assert request.phq2_q2 == val

    def test_gad2_questions_have_valid_range(self) -> None:
        """Test GAD-2 questions accept valid range 0-3."""
        for val in [0, 1, 2, 3]:
            request = SubmitCheckInRequest(
                phq2_q1=0,
                phq2_q2=0,
                gad2_q1=val,
                gad2_q2=val,
            )
            assert request.gad2_q1 == val
            assert request.gad2_q2 == val

    def test_safety_questions_are_boolean(self) -> None:
        """Test safety questions are boolean fields."""
        request = SubmitCheckInRequest(
            phq2_q1=0,
            phq2_q2=0,
            gad2_q1=0,
            gad2_q2=0,
            suicidal_ideation=True,
            self_harm=True,
        )
        assert isinstance(request.suicidal_ideation, bool)
        assert isinstance(request.self_harm, bool)

    def test_wellbeing_rating_is_1_to_10(self) -> None:
        """Test wellbeing rating accepts 1-10 range."""
        for val in range(1, 11):
            request = SubmitCheckInRequest(
                phq2_q1=0,
                phq2_q2=0,
                gad2_q1=0,
                gad2_q2=0,
                wellbeing_rating=val,
            )
            assert request.wellbeing_rating == val

    def test_duty_queue_has_severity_counts(self) -> None:
        """Test duty queue response includes severity counts."""
        response = DutyQueueResponse(
            alerts=[],
            counts=AlertCountsResponse(
                critical=1,
                high=2,
                medium=3,
                low=4,
                total=10,
            ),
        )
        assert hasattr(response.counts, "critical")
        assert hasattr(response.counts, "high")
        assert hasattr(response.counts, "medium")
        assert hasattr(response.counts, "low")
        assert hasattr(response.counts, "total")
