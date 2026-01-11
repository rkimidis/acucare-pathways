"""Tests for change control service.

Sprint 6 tests covering:
- Ruleset changes require approver role
- Cannot approve own submissions
- Permission validation for all operations
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.governance import ApprovalStatus, RulesetApproval
from app.services.change_control import (
    ChangeControlPermissionError,
    ChangeControlService,
    RulesetApprovalNotFoundError,
)


class TestRulesetApprovalPermissions:
    """Tests that ruleset changes require approver role."""

    @pytest.mark.asyncio
    async def test_submit_requires_submit_permission(self) -> None:
        """User without submit permission cannot submit ruleset changes."""
        mock_session = AsyncMock()
        service = ChangeControlService(mock_session)

        # User with no relevant roles
        user_roles = ["receptionist"]

        with pytest.raises(ChangeControlPermissionError):
            await service.submit_ruleset_change(
                ruleset_type="triage_rules",
                ruleset_version="1.0.0",
                change_summary="Test change",
                change_rationale="Test rationale",
                content={"rules": []},
                submitted_by="user-123",
                user_roles=user_roles,
            )

    @pytest.mark.asyncio
    async def test_submit_allowed_for_admin(self) -> None:
        """Admin can submit ruleset changes."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("app.services.change_control.write_audit_event"):
            service = ChangeControlService(mock_session)

            user_roles = ["admin"]

            approval = await service.submit_ruleset_change(
                ruleset_type="triage_rules",
                ruleset_version="1.0.0",
                change_summary="Test change",
                change_rationale="Test rationale",
                content={"rules": []},
                submitted_by="admin-user",
                user_roles=user_roles,
            )

            assert approval is not None
            assert approval.status == ApprovalStatus.PENDING.value

    @pytest.mark.asyncio
    async def test_submit_allowed_for_clinical_lead(self) -> None:
        """Clinical lead can submit ruleset changes."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("app.services.change_control.write_audit_event"):
            service = ChangeControlService(mock_session)

            user_roles = ["clinical_lead"]

            approval = await service.submit_ruleset_change(
                ruleset_type="escalation_rules",
                ruleset_version="2.0.0",
                change_summary="Update escalation thresholds",
                change_rationale="Clinical review findings",
                content={"thresholds": {"phq9": 15}},
                submitted_by="clinical-lead-user",
                user_roles=user_roles,
            )

            assert approval is not None

    @pytest.mark.asyncio
    async def test_approve_requires_approver_role(self) -> None:
        """User without approver role cannot approve ruleset changes."""
        mock_session = AsyncMock()

        # Mock existing pending approval
        mock_approval = RulesetApproval(
            id="approval-123",
            ruleset_type="triage_rules",
            ruleset_version="1.0.0",
            change_summary="Test",
            change_rationale="Test",
            content_hash="abc123",
            submitted_by="user-A",
            submitted_at=datetime.now(timezone.utc),
            status=ApprovalStatus.PENDING.value,
        )

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_approval))
        )

        service = ChangeControlService(mock_session)

        # User without approval permission
        user_roles = ["clinician"]  # Regular clinician cannot approve

        with pytest.raises(ChangeControlPermissionError):
            await service.approve_ruleset(
                approval_id="approval-123",
                approver_id="clinician-user",
                user_roles=user_roles,
            )

    @pytest.mark.asyncio
    async def test_approve_allowed_for_admin(self) -> None:
        """Admin can approve ruleset changes."""
        mock_session = AsyncMock()

        mock_approval = MagicMock()
        mock_approval.id = "approval-123"
        mock_approval.status = ApprovalStatus.PENDING.value
        mock_approval.submitted_by = "other-user"  # Different from approver
        mock_approval.approve = MagicMock()

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_approval))
        )
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        with patch("app.services.change_control.write_audit_event"):
            service = ChangeControlService(mock_session)

            user_roles = ["admin"]

            result = await service.approve_ruleset(
                approval_id="approval-123",
                approver_id="admin-user",
                user_roles=user_roles,
            )

            mock_approval.approve.assert_called_once()

    @pytest.mark.asyncio
    async def test_cannot_approve_own_submission(self) -> None:
        """User cannot approve their own ruleset submission."""
        mock_session = AsyncMock()

        mock_approval = MagicMock()
        mock_approval.id = "approval-123"
        mock_approval.status = ApprovalStatus.PENDING.value
        mock_approval.submitted_by = "admin-user"  # Same as approver

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_approval))
        )

        service = ChangeControlService(mock_session)

        user_roles = ["admin"]  # Has permission to approve

        with pytest.raises(ChangeControlPermissionError, match="Cannot approve own submission"):
            await service.approve_ruleset(
                approval_id="approval-123",
                approver_id="admin-user",  # Same as submitted_by
                user_roles=user_roles,
            )

    @pytest.mark.asyncio
    async def test_reject_requires_approver_role(self) -> None:
        """User without approver role cannot reject ruleset changes."""
        mock_session = AsyncMock()

        mock_approval = RulesetApproval(
            id="approval-123",
            ruleset_type="triage_rules",
            ruleset_version="1.0.0",
            change_summary="Test",
            change_rationale="Test",
            content_hash="abc123",
            submitted_by="user-A",
            submitted_at=datetime.now(timezone.utc),
            status=ApprovalStatus.PENDING.value,
        )

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_approval))
        )

        service = ChangeControlService(mock_session)

        user_roles = ["developer"]  # Developer cannot reject

        with pytest.raises(ChangeControlPermissionError):
            await service.reject_ruleset(
                approval_id="approval-123",
                rejector_id="developer-user",
                rejection_reason="Not suitable",
                user_roles=user_roles,
            )

    @pytest.mark.asyncio
    async def test_activate_requires_admin_role(self) -> None:
        """Only admin can activate approved rulesets."""
        mock_session = AsyncMock()

        mock_approval = MagicMock()
        mock_approval.id = "approval-123"
        mock_approval.status = ApprovalStatus.APPROVED.value

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_approval))
        )

        service = ChangeControlService(mock_session)

        # Clinical lead can approve but not activate
        user_roles = ["clinical_lead"]

        with pytest.raises(ChangeControlPermissionError):
            await service.activate_ruleset(
                approval_id="approval-123",
                activator_id="clinical-lead-user",
                user_roles=user_roles,
            )


class TestRulesetApprovalWorkflow:
    """Tests for ruleset approval workflow states."""

    @pytest.mark.asyncio
    async def test_cannot_approve_non_pending(self) -> None:
        """Cannot approve already processed approval."""
        mock_session = AsyncMock()

        mock_approval = MagicMock()
        mock_approval.id = "approval-123"
        mock_approval.status = ApprovalStatus.APPROVED.value  # Already approved
        mock_approval.submitted_by = "other-user"

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_approval))
        )

        service = ChangeControlService(mock_session)

        user_roles = ["admin"]

        with pytest.raises(ValueError, match="Can only approve PENDING"):
            await service.approve_ruleset(
                approval_id="approval-123",
                approver_id="admin-user",
                user_roles=user_roles,
            )

    @pytest.mark.asyncio
    async def test_cannot_activate_unapproved(self) -> None:
        """Cannot activate ruleset that hasn't been approved."""
        mock_session = AsyncMock()

        mock_approval = MagicMock()
        mock_approval.id = "approval-123"
        mock_approval.status = ApprovalStatus.PENDING.value  # Not approved yet

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_approval))
        )

        service = ChangeControlService(mock_session)

        user_roles = ["admin"]

        with pytest.raises(ValueError, match="Can only activate APPROVED"):
            await service.activate_ruleset(
                approval_id="approval-123",
                activator_id="admin-user",
                user_roles=user_roles,
            )

    @pytest.mark.asyncio
    async def test_not_found_raises_error(self) -> None:
        """Nonexistent approval raises appropriate error."""
        mock_session = AsyncMock()

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        service = ChangeControlService(mock_session)

        user_roles = ["admin"]

        with pytest.raises(RulesetApprovalNotFoundError):
            await service.approve_ruleset(
                approval_id="nonexistent-id",
                approver_id="admin-user",
                user_roles=user_roles,
            )


class TestContentHashIntegrity:
    """Tests for content hash computation."""

    def test_content_hash_computed_on_submission(self) -> None:
        """Content hash is computed from ruleset content."""
        content = {"rules": [{"id": "r1", "condition": "phq9 > 15"}]}

        hash1 = RulesetApproval.compute_content_hash(content)
        hash2 = RulesetApproval.compute_content_hash(content)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256

    def test_different_content_different_hash(self) -> None:
        """Different content produces different hash."""
        content1 = {"rules": [{"id": "r1"}]}
        content2 = {"rules": [{"id": "r2"}]}

        hash1 = RulesetApproval.compute_content_hash(content1)
        hash2 = RulesetApproval.compute_content_hash(content2)

        assert hash1 != hash2
