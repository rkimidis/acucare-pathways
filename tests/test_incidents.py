"""Tests for incident management service.

Sprint 6 tests covering:
- Incident workflow permissions validated
- Workflow state transitions
- Role-based access control
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.governance import Incident, IncidentStatus, IncidentSeverity
from app.services.incident import (
    IncidentNotFoundError,
    IncidentPermissionError,
    IncidentService,
    IncidentWorkflowError,
)


class TestIncidentWorkflowPermissions:
    """Tests that incident workflow permissions are validated."""

    @pytest.mark.asyncio
    async def test_create_requires_permission(self) -> None:
        """User without create permission cannot create incidents."""
        mock_session = AsyncMock()
        service = IncidentService(mock_session)

        # User with no relevant roles
        user_roles = ["viewer"]

        with pytest.raises(IncidentPermissionError):
            await service.create_incident(
                title="Test incident",
                description="Test description for incident",
                category="clinical",
                severity="medium",
                reported_by="user-123",
                user_roles=user_roles,
            )

    @pytest.mark.asyncio
    async def test_create_allowed_for_clinician(self) -> None:
        """Clinician can create incidents."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("app.services.incident.write_audit_event"):
            service = IncidentService(mock_session)

            user_roles = ["clinician"]

            incident = await service.create_incident(
                title="Patient safety concern",
                description="Description of the safety concern observed",
                category="clinical",
                severity="high",
                reported_by="clinician-user",
                user_roles=user_roles,
            )

            assert incident is not None
            assert incident.status == IncidentStatus.OPEN.value
            assert incident.title == "Patient safety concern"

    @pytest.mark.asyncio
    async def test_create_allowed_for_nurse(self) -> None:
        """Nurse can create incidents."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("app.services.incident.write_audit_event"):
            service = IncidentService(mock_session)

            user_roles = ["nurse"]

            incident = await service.create_incident(
                title="Medication incident",
                description="Description of medication issue",
                category="medication",
                severity="medium",
                reported_by="nurse-user",
                user_roles=user_roles,
            )

            assert incident is not None

    @pytest.mark.asyncio
    async def test_view_requires_permission(self) -> None:
        """User without view permission cannot view incidents."""
        mock_session = AsyncMock()
        service = IncidentService(mock_session)

        user_roles = ["external"]  # No view permission

        with pytest.raises(IncidentPermissionError):
            await service.get_incident(
                incident_id="incident-123",
                user_roles=user_roles,
            )

    @pytest.mark.asyncio
    async def test_start_review_requires_permission(self) -> None:
        """Only authorized roles can start incident review."""
        mock_session = AsyncMock()

        # Mock existing incident
        mock_incident = MagicMock()
        mock_incident.id = "incident-123"
        mock_incident.status = IncidentStatus.OPEN.value
        mock_incident.deleted_at = None

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_incident))
        )

        service = IncidentService(mock_session)

        # Receptionist cannot start review
        user_roles = ["receptionist"]

        with pytest.raises(IncidentPermissionError):
            await service.start_review(
                incident_id="incident-123",
                reviewer_id="receptionist-user",
                user_roles=user_roles,
            )

    @pytest.mark.asyncio
    async def test_start_review_allowed_for_clinician(self) -> None:
        """Clinician can start incident review."""
        mock_session = AsyncMock()

        mock_incident = MagicMock()
        mock_incident.id = "incident-123"
        mock_incident.status = IncidentStatus.OPEN.value
        mock_incident.deleted_at = None
        mock_incident.start_review = MagicMock()

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_incident))
        )
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("app.services.incident.write_audit_event"):
            service = IncidentService(mock_session)

            user_roles = ["clinician"]

            await service.start_review(
                incident_id="incident-123",
                reviewer_id="clinician-user",
                user_roles=user_roles,
            )

            mock_incident.start_review.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_requires_senior_permission(self) -> None:
        """Only senior roles can close incidents."""
        mock_session = AsyncMock()

        mock_incident = MagicMock()
        mock_incident.id = "incident-123"
        mock_incident.status = IncidentStatus.UNDER_REVIEW.value
        mock_incident.deleted_at = None

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_incident))
        )

        service = IncidentService(mock_session)

        # Regular clinician cannot close
        user_roles = ["clinician"]

        with pytest.raises(IncidentPermissionError):
            await service.close_incident(
                incident_id="incident-123",
                closed_by="clinician-user",
                closure_reason="Issue resolved with appropriate actions",
                user_roles=user_roles,
            )

    @pytest.mark.asyncio
    async def test_close_allowed_for_manager(self) -> None:
        """Manager can close incidents."""
        mock_session = AsyncMock()

        mock_incident = MagicMock()
        mock_incident.id = "incident-123"
        mock_incident.status = IncidentStatus.UNDER_REVIEW.value
        mock_incident.deleted_at = None
        mock_incident.close = MagicMock()

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_incident))
        )
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("app.services.incident.write_audit_event"):
            service = IncidentService(mock_session)

            user_roles = ["manager"]

            await service.close_incident(
                incident_id="incident-123",
                closed_by="manager-user",
                closure_reason="Issue resolved with corrective measures",
                user_roles=user_roles,
                lessons_learned="Improved process documentation",
                preventive_actions="Staff training scheduled",
            )

            mock_incident.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_reopen_requires_senior_permission(self) -> None:
        """Only senior roles can reopen incidents."""
        mock_session = AsyncMock()

        mock_incident = MagicMock()
        mock_incident.id = "incident-123"
        mock_incident.status = IncidentStatus.CLOSED.value
        mock_incident.deleted_at = None

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_incident))
        )

        service = IncidentService(mock_session)

        user_roles = ["clinician"]

        with pytest.raises(IncidentPermissionError):
            await service.reopen_incident(
                incident_id="incident-123",
                reopened_by="clinician-user",
                reason="Additional issues discovered",
                user_roles=user_roles,
            )

    @pytest.mark.asyncio
    async def test_mark_cqc_reportable_requires_permission(self) -> None:
        """Only senior roles can mark incidents as CQC reportable."""
        mock_session = AsyncMock()

        mock_incident = MagicMock()
        mock_incident.id = "incident-123"
        mock_incident.deleted_at = None

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_incident))
        )

        service = IncidentService(mock_session)

        user_roles = ["nurse"]

        with pytest.raises(IncidentPermissionError):
            await service.mark_cqc_reportable(
                incident_id="incident-123",
                marked_by="nurse-user",
                user_roles=user_roles,
            )


class TestIncidentWorkflowStates:
    """Tests for incident workflow state transitions."""

    def test_start_review_only_from_open(self) -> None:
        """Can only start review on OPEN incidents."""
        incident = Incident(
            id="test-id",
            reference_number="INC-20240101-ABC123",
            title="Test",
            description="Test description",
            reported_by="user-1",
            reported_at=datetime.now(timezone.utc),
            status=IncidentStatus.UNDER_REVIEW.value,  # Not OPEN
        )

        with pytest.raises(ValueError, match="Can only start review on OPEN"):
            incident.start_review("reviewer-id")

    def test_start_review_updates_status(self) -> None:
        """Starting review transitions to UNDER_REVIEW."""
        incident = Incident(
            id="test-id",
            reference_number="INC-20240101-ABC123",
            title="Test",
            description="Test description",
            reported_by="user-1",
            reported_at=datetime.now(timezone.utc),
            status=IncidentStatus.OPEN.value,
        )

        incident.start_review("reviewer-id")

        assert incident.status == IncidentStatus.UNDER_REVIEW.value
        assert incident.reviewer_id == "reviewer-id"
        assert incident.review_started_at is not None

    def test_close_already_closed_raises_error(self) -> None:
        """Cannot close already closed incident."""
        incident = Incident(
            id="test-id",
            reference_number="INC-20240101-ABC123",
            title="Test",
            description="Test description",
            reported_by="user-1",
            reported_at=datetime.now(timezone.utc),
            status=IncidentStatus.CLOSED.value,
        )

        with pytest.raises(ValueError, match="already closed"):
            incident.close("closer-id", "Already resolved")

    def test_close_records_details(self) -> None:
        """Closing records all closure details."""
        incident = Incident(
            id="test-id",
            reference_number="INC-20240101-ABC123",
            title="Test",
            description="Test description",
            reported_by="user-1",
            reported_at=datetime.now(timezone.utc),
            status=IncidentStatus.UNDER_REVIEW.value,
        )

        incident.close(
            closed_by="closer-id",
            closure_reason="Issue fully resolved",
            lessons_learned="Need better monitoring",
            preventive_actions="Implement alerts",
        )

        assert incident.status == IncidentStatus.CLOSED.value
        assert incident.closed_by == "closer-id"
        assert incident.closed_at is not None
        assert incident.closure_reason == "Issue fully resolved"
        assert incident.lessons_learned == "Need better monitoring"
        assert incident.preventive_actions == "Implement alerts"

    def test_reopen_only_from_closed(self) -> None:
        """Can only reopen CLOSED incidents."""
        incident = Incident(
            id="test-id",
            reference_number="INC-20240101-ABC123",
            title="Test",
            description="Test description",
            reported_by="user-1",
            reported_at=datetime.now(timezone.utc),
            status=IncidentStatus.OPEN.value,  # Not CLOSED
        )

        with pytest.raises(ValueError, match="Can only reopen CLOSED"):
            incident.reopen("New issues found")

    def test_reopen_transitions_to_open(self) -> None:
        """Reopening transitions back to OPEN."""
        incident = Incident(
            id="test-id",
            reference_number="INC-20240101-ABC123",
            title="Test",
            description="Test description",
            reported_by="user-1",
            reported_at=datetime.now(timezone.utc),
            status=IncidentStatus.CLOSED.value,
        )

        incident.reopen("Additional concerns raised")

        assert incident.status == IncidentStatus.OPEN.value
        assert "Reopened" in (incident.review_notes or "")


class TestIncidentNotFound:
    """Tests for incident not found scenarios."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_raises_error(self) -> None:
        """Getting nonexistent incident raises appropriate error."""
        mock_session = AsyncMock()

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        service = IncidentService(mock_session)

        user_roles = ["admin"]

        with pytest.raises(IncidentNotFoundError):
            await service.get_incident(
                incident_id="nonexistent-id",
                user_roles=user_roles,
            )
