"""Tests for disposition management.

Sprint 4 tests covering:
- Override requires rationale
- Audit events emitted for review/override/export
- Permission tests: receptionist cannot override clinical disposition
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.triage_case import TriageTier
from app.models.user import UserRole
from app.services.disposition import (
    DispositionService,
    RationaleRequiredError,
    DispositionAlreadyFinalizedError,
)
from app.services.rbac import Permission, RBACService


class TestOverrideRequiresRationale:
    """Tests that disposition override requires a rationale."""

    @pytest.mark.asyncio
    async def test_override_without_rationale_raises_error(self) -> None:
        """Override without rationale must raise RationaleRequiredError."""
        # Create mock session and clinician
        mock_session = AsyncMock()
        mock_clinician = MagicMock()
        mock_clinician.id = "test-clinician-id"
        mock_clinician.email = "clinician@test.com"

        service = DispositionService(mock_session)

        # Mock get_final_for_case to return None (not finalized)
        service.get_final_for_case = AsyncMock(return_value=None)

        # Test with empty rationale
        with pytest.raises(RationaleRequiredError):
            await service.override_disposition(
                triage_case_id="test-case-id",
                clinician=mock_clinician,
                new_tier="AMBER",
                new_pathway="THERAPY_ASSESSMENT",
                rationale="",  # Empty rationale
            )

    @pytest.mark.asyncio
    async def test_override_with_whitespace_rationale_raises_error(self) -> None:
        """Override with whitespace-only rationale must raise error."""
        mock_session = AsyncMock()
        mock_clinician = MagicMock()
        mock_clinician.id = "test-clinician-id"

        service = DispositionService(mock_session)
        service.get_final_for_case = AsyncMock(return_value=None)

        with pytest.raises(RationaleRequiredError):
            await service.override_disposition(
                triage_case_id="test-case-id",
                clinician=mock_clinician,
                new_tier="GREEN",
                new_pathway="THERAPY_ASSESSMENT",
                rationale="   ",  # Whitespace only
            )

    @pytest.mark.asyncio
    async def test_override_with_none_rationale_raises_error(self) -> None:
        """Override with None rationale must raise error."""
        mock_session = AsyncMock()
        mock_clinician = MagicMock()
        mock_clinician.id = "test-clinician-id"

        service = DispositionService(mock_session)
        service.get_final_for_case = AsyncMock(return_value=None)

        with pytest.raises(RationaleRequiredError):
            await service.override_disposition(
                triage_case_id="test-case-id",
                clinician=mock_clinician,
                new_tier="GREEN",
                new_pathway="THERAPY_ASSESSMENT",
                rationale=None,  # type: ignore # None rationale
            )

    def test_confirm_does_not_require_rationale(self) -> None:
        """Confirm disposition should not require rationale."""
        # Confirm endpoint schema should not have required rationale
        from app.api.v1.dashboard import ConfirmDispositionRequest

        # Should be able to create without rationale
        request = ConfirmDispositionRequest(clinical_notes=None)
        assert request.clinical_notes is None

    def test_override_schema_requires_rationale(self) -> None:
        """Override disposition schema should require rationale."""
        from app.api.v1.dashboard import OverrideDispositionRequest
        from pydantic import ValidationError

        # Should fail without rationale
        with pytest.raises(ValidationError):
            OverrideDispositionRequest(
                tier="AMBER",
                pathway="THERAPY_ASSESSMENT",
                # rationale missing
            )

    def test_override_schema_requires_minimum_rationale_length(self) -> None:
        """Override rationale must be at least 10 characters."""
        from app.api.v1.dashboard import OverrideDispositionRequest
        from pydantic import ValidationError

        # Should fail with short rationale
        with pytest.raises(ValidationError):
            OverrideDispositionRequest(
                tier="AMBER",
                pathway="THERAPY_ASSESSMENT",
                rationale="short",  # Less than 10 chars
            )


class TestAuditEventEmission:
    """Tests that audit events are emitted for disposition actions."""

    @pytest.mark.asyncio
    async def test_confirm_emits_audit_event(self) -> None:
        """Confirming disposition should emit audit event."""
        mock_session = AsyncMock()
        mock_clinician = MagicMock()
        mock_clinician.id = "clinician-123"
        mock_clinician.email = "clinician@test.com"

        # Create mock draft
        mock_draft = MagicMock()
        mock_draft.id = "draft-123"
        mock_draft.tier = "GREEN"
        mock_draft.pathway = "THERAPY_ASSESSMENT"
        mock_draft.self_book_allowed = True

        with patch("app.services.disposition.write_audit_event") as mock_audit:
            service = DispositionService(mock_session)
            service.get_final_for_case = AsyncMock(return_value=None)
            service.get_draft_for_case = AsyncMock(return_value=mock_draft)

            # Mock session execute for case update
            mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=MagicMock())))
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()
            mock_session.add = MagicMock()

            await service.confirm_disposition(
                triage_case_id="case-123",
                clinician=mock_clinician,
            )

            # Verify audit event was called
            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args.kwargs
            assert call_kwargs["action"] == "disposition.confirm"
            assert call_kwargs["entity_type"] == "triage_case"
            assert call_kwargs["entity_id"] == "case-123"

    @pytest.mark.asyncio
    async def test_override_emits_audit_event(self) -> None:
        """Overriding disposition should emit audit event."""
        mock_session = AsyncMock()
        mock_clinician = MagicMock()
        mock_clinician.id = "clinician-123"
        mock_clinician.email = "clinician@test.com"

        # Create mock draft
        mock_draft = MagicMock()
        mock_draft.id = "draft-123"
        mock_draft.tier = "GREEN"
        mock_draft.pathway = "THERAPY_ASSESSMENT"

        with patch("app.services.disposition.write_audit_event") as mock_audit:
            service = DispositionService(mock_session)
            service.get_final_for_case = AsyncMock(return_value=None)
            service.get_draft_for_case = AsyncMock(return_value=mock_draft)

            mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=MagicMock())))
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()
            mock_session.add = MagicMock()

            await service.override_disposition(
                triage_case_id="case-123",
                clinician=mock_clinician,
                new_tier="AMBER",
                new_pathway="PSYCHIATRY_ASSESSMENT",
                rationale="Patient presenting with elevated risk factors not captured in assessment.",
            )

            # Verify audit event was called
            mock_audit.assert_called_once()
            call_kwargs = mock_audit.call_args.kwargs
            assert call_kwargs["action"] == "disposition.override"
            assert call_kwargs["entity_type"] == "triage_case"
            assert "rationale" in call_kwargs["metadata"]


class TestReceptionistCannotOverride:
    """Tests that receptionist role cannot override disposition."""

    def test_receptionist_lacks_disposition_confirm_permission(self) -> None:
        """Receptionist should not have DISPOSITION_CONFIRM permission."""
        has_perm = RBACService.has_permission(
            UserRole.RECEPTIONIST,
            Permission.DISPOSITION_CONFIRM,
        )
        assert has_perm is False

    def test_receptionist_lacks_disposition_override_permission(self) -> None:
        """Receptionist should not have DISPOSITION_OVERRIDE permission."""
        has_perm = RBACService.has_permission(
            UserRole.RECEPTIONIST,
            Permission.DISPOSITION_OVERRIDE,
        )
        assert has_perm is False

    def test_receptionist_lacks_disposition_export_permission(self) -> None:
        """Receptionist should not have DISPOSITION_EXPORT permission."""
        has_perm = RBACService.has_permission(
            UserRole.RECEPTIONIST,
            Permission.DISPOSITION_EXPORT,
        )
        assert has_perm is False

    def test_clinician_has_disposition_permissions(self) -> None:
        """Clinician should have all disposition permissions."""
        assert RBACService.has_permission(
            UserRole.CLINICIAN,
            Permission.DISPOSITION_CONFIRM,
        ) is True

        assert RBACService.has_permission(
            UserRole.CLINICIAN,
            Permission.DISPOSITION_OVERRIDE,
        ) is True

        assert RBACService.has_permission(
            UserRole.CLINICIAN,
            Permission.DISPOSITION_EXPORT,
        ) is True

    def test_clinical_lead_has_disposition_permissions(self) -> None:
        """Clinical lead should have all disposition permissions."""
        assert RBACService.has_permission(
            UserRole.CLINICAL_LEAD,
            Permission.DISPOSITION_CONFIRM,
        ) is True

        assert RBACService.has_permission(
            UserRole.CLINICAL_LEAD,
            Permission.DISPOSITION_OVERRIDE,
        ) is True

    def test_admin_has_disposition_permissions(self) -> None:
        """Admin should have all disposition permissions."""
        assert RBACService.has_permission(
            UserRole.ADMIN,
            Permission.DISPOSITION_CONFIRM,
        ) is True

        assert RBACService.has_permission(
            UserRole.ADMIN,
            Permission.DISPOSITION_OVERRIDE,
        ) is True

    def test_readonly_lacks_disposition_permissions(self) -> None:
        """Readonly role should not have disposition permissions."""
        assert RBACService.has_permission(
            UserRole.READONLY,
            Permission.DISPOSITION_CONFIRM,
        ) is False

        assert RBACService.has_permission(
            UserRole.READONLY,
            Permission.DISPOSITION_OVERRIDE,
        ) is False


class TestDispositionAlreadyFinalized:
    """Tests for preventing double finalization."""

    @pytest.mark.asyncio
    async def test_confirm_on_finalized_case_raises_error(self) -> None:
        """Confirming an already finalized case should raise error."""
        mock_session = AsyncMock()
        mock_clinician = MagicMock()

        # Mock existing final disposition
        mock_final = MagicMock()

        service = DispositionService(mock_session)
        service.get_final_for_case = AsyncMock(return_value=mock_final)

        with pytest.raises(DispositionAlreadyFinalizedError):
            await service.confirm_disposition(
                triage_case_id="case-123",
                clinician=mock_clinician,
            )

    @pytest.mark.asyncio
    async def test_override_on_finalized_case_raises_error(self) -> None:
        """Overriding an already finalized case should raise error."""
        mock_session = AsyncMock()
        mock_clinician = MagicMock()

        mock_final = MagicMock()

        service = DispositionService(mock_session)
        service.get_final_for_case = AsyncMock(return_value=mock_final)

        with pytest.raises(DispositionAlreadyFinalizedError):
            await service.override_disposition(
                triage_case_id="case-123",
                clinician=mock_clinician,
                new_tier="AMBER",
                new_pathway="THERAPY_ASSESSMENT",
                rationale="This should fail because already finalized.",
            )


class TestSelfBookingOnOverride:
    """Tests that self-booking is correctly set on override."""

    @pytest.mark.asyncio
    async def test_override_to_red_disables_self_booking(self) -> None:
        """Overriding to RED tier should disable self-booking."""
        mock_session = AsyncMock()
        mock_clinician = MagicMock()
        mock_clinician.id = "clinician-123"
        mock_clinician.email = "test@test.com"

        mock_draft = MagicMock()
        mock_draft.id = "draft-123"
        mock_draft.tier = "GREEN"
        mock_draft.pathway = "THERAPY_ASSESSMENT"

        mock_case = MagicMock()

        with patch("app.services.disposition.write_audit_event"):
            service = DispositionService(mock_session)
            service.get_final_for_case = AsyncMock(return_value=None)
            service.get_draft_for_case = AsyncMock(return_value=mock_draft)

            mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_case)))
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()
            mock_session.add = MagicMock()

            result = await service.override_disposition(
                triage_case_id="case-123",
                clinician=mock_clinician,
                new_tier="RED",
                new_pathway="CRISIS_ESCALATION",
                rationale="Elevated risk identified during review.",
            )

            # Final disposition should have self_book_allowed=False
            assert result.self_book_allowed is False

            # Case should also be updated
            assert mock_case.self_book_allowed is False

    @pytest.mark.asyncio
    async def test_override_to_amber_disables_self_booking(self) -> None:
        """Overriding to AMBER tier should disable self-booking."""
        mock_session = AsyncMock()
        mock_clinician = MagicMock()
        mock_clinician.id = "clinician-123"
        mock_clinician.email = "test@test.com"

        mock_draft = MagicMock()
        mock_draft.id = "draft-123"
        mock_draft.tier = "GREEN"
        mock_draft.pathway = "THERAPY_ASSESSMENT"

        mock_case = MagicMock()

        with patch("app.services.disposition.write_audit_event"):
            service = DispositionService(mock_session)
            service.get_final_for_case = AsyncMock(return_value=None)
            service.get_draft_for_case = AsyncMock(return_value=mock_draft)

            mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_case)))
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()
            mock_session.add = MagicMock()

            result = await service.override_disposition(
                triage_case_id="case-123",
                clinician=mock_clinician,
                new_tier="AMBER",
                new_pathway="PSYCHIATRY_ASSESSMENT",
                rationale="Requires psychiatric evaluation.",
            )

            assert result.self_book_allowed is False

    @pytest.mark.asyncio
    async def test_override_to_green_allows_self_booking(self) -> None:
        """Overriding to GREEN tier should allow self-booking."""
        mock_session = AsyncMock()
        mock_clinician = MagicMock()
        mock_clinician.id = "clinician-123"
        mock_clinician.email = "test@test.com"

        mock_draft = MagicMock()
        mock_draft.id = "draft-123"
        mock_draft.tier = "AMBER"
        mock_draft.pathway = "PSYCHIATRY_ASSESSMENT"

        mock_case = MagicMock()

        with patch("app.services.disposition.write_audit_event"):
            service = DispositionService(mock_session)
            service.get_final_for_case = AsyncMock(return_value=None)
            service.get_draft_for_case = AsyncMock(return_value=mock_draft)

            mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_case)))
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()
            mock_session.add = MagicMock()

            result = await service.override_disposition(
                triage_case_id="case-123",
                clinician=mock_clinician,
                new_tier="GREEN",
                new_pathway="THERAPY_ASSESSMENT",
                rationale="Risk factors reassessed and found to be lower than indicated.",
            )

            assert result.self_book_allowed is True
