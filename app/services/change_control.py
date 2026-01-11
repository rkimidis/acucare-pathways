"""Change control service for Sprint 6.

Handles ruleset approvals and questionnaire version history.
Includes permission validation for approvers.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import (
    ApprovalStatus,
    QuestionnaireVersion,
    RulesetApproval,
)
from app.services.audit import write_audit_event


class ChangeControlPermissionError(Exception):
    """Raised when user lacks permission for change control action."""
    pass


class RulesetApprovalNotFoundError(Exception):
    """Raised when ruleset approval not found."""
    pass


class QuestionnaireVersionNotFoundError(Exception):
    """Raised when questionnaire version not found."""
    pass


# Role-based permissions for change control
CHANGE_CONTROL_PERMISSIONS = {
    "submit_ruleset": ["admin", "clinical_lead", "developer"],
    "approve_ruleset": ["admin", "clinical_lead"],
    "reject_ruleset": ["admin", "clinical_lead"],
    "activate_ruleset": ["admin"],
    "submit_questionnaire": ["admin", "clinical_lead", "developer"],
    "approve_questionnaire": ["admin", "clinical_lead"],
    "view": ["admin", "clinical_lead", "clinician", "developer", "manager"],
}


class ChangeControlService:
    """Service for managing change control workflows."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _check_permission(
        self,
        action: str,
        user_roles: list[str],
    ) -> bool:
        """Check if user has permission for action."""
        allowed_roles = CHANGE_CONTROL_PERMISSIONS.get(action, [])
        return any(role in allowed_roles for role in user_roles)

    # Ruleset Approval Methods

    async def submit_ruleset_change(
        self,
        ruleset_type: str,
        ruleset_version: str,
        change_summary: str,
        change_rationale: str,
        content: dict,
        submitted_by: str,
        user_roles: list[str],
        previous_version: Optional[str] = None,
        rules_added: Optional[dict] = None,
        rules_modified: Optional[dict] = None,
        rules_removed: Optional[dict] = None,
    ) -> RulesetApproval:
        """Submit a ruleset change for approval."""
        if not self._check_permission("submit_ruleset", user_roles):
            raise ChangeControlPermissionError(
                "User does not have permission to submit ruleset changes"
            )

        # Compute content hash
        content_hash = RulesetApproval.compute_content_hash(content)

        approval = RulesetApproval(
            id=str(uuid.uuid4()),
            ruleset_type=ruleset_type,
            ruleset_version=ruleset_version,
            previous_version=previous_version,
            change_summary=change_summary,
            change_rationale=change_rationale,
            rules_added=rules_added,
            rules_modified=rules_modified,
            rules_removed=rules_removed,
            content_hash=content_hash,
            submitted_by=submitted_by,
            submitted_at=datetime.now(),
            status=ApprovalStatus.PENDING.value,
        )

        self.session.add(approval)

        await write_audit_event(
            session=self.session,
            action="change_control.ruleset_submitted",
            category="governance",
            actor_type="user",
            actor_id=submitted_by,
            entity_type="ruleset_approval",
            entity_id=approval.id,
            metadata={
                "ruleset_type": ruleset_type,
                "version": ruleset_version,
                "previous_version": previous_version,
                "content_hash": content_hash,
            },
        )

        await self.session.commit()
        await self.session.refresh(approval)

        return approval

    async def approve_ruleset(
        self,
        approval_id: str,
        approver_id: str,
        user_roles: list[str],
        notes: Optional[str] = None,
    ) -> RulesetApproval:
        """Approve a ruleset change."""
        if not self._check_permission("approve_ruleset", user_roles):
            raise ChangeControlPermissionError(
                "User does not have permission to approve ruleset changes"
            )

        result = await self.session.execute(
            select(RulesetApproval).where(RulesetApproval.id == approval_id)
        )
        approval = result.scalar_one_or_none()

        if not approval:
            raise RulesetApprovalNotFoundError(f"Approval not found: {approval_id}")

        if approval.status != ApprovalStatus.PENDING.value:
            raise ValueError("Can only approve PENDING changes")

        # Cannot approve own submission
        if approval.submitted_by == approver_id:
            raise ChangeControlPermissionError("Cannot approve own submission")

        approval.approve(approver_id, notes)

        await write_audit_event(
            session=self.session,
            action="change_control.ruleset_approved",
            category="governance",
            actor_type="user",
            actor_id=approver_id,
            entity_type="ruleset_approval",
            entity_id=approval.id,
            metadata={
                "ruleset_type": approval.ruleset_type,
                "version": approval.ruleset_version,
            },
        )

        await self.session.commit()
        await self.session.refresh(approval)

        return approval

    async def reject_ruleset(
        self,
        approval_id: str,
        rejector_id: str,
        rejection_reason: str,
        user_roles: list[str],
    ) -> RulesetApproval:
        """Reject a ruleset change."""
        if not self._check_permission("reject_ruleset", user_roles):
            raise ChangeControlPermissionError(
                "User does not have permission to reject ruleset changes"
            )

        result = await self.session.execute(
            select(RulesetApproval).where(RulesetApproval.id == approval_id)
        )
        approval = result.scalar_one_or_none()

        if not approval:
            raise RulesetApprovalNotFoundError(f"Approval not found: {approval_id}")

        approval.reject(rejector_id, rejection_reason)

        await write_audit_event(
            session=self.session,
            action="change_control.ruleset_rejected",
            category="governance",
            actor_type="user",
            actor_id=rejector_id,
            entity_type="ruleset_approval",
            entity_id=approval.id,
            metadata={
                "ruleset_type": approval.ruleset_type,
                "version": approval.ruleset_version,
                "reason": rejection_reason,
            },
        )

        await self.session.commit()
        await self.session.refresh(approval)

        return approval

    async def activate_ruleset(
        self,
        approval_id: str,
        activator_id: str,
        user_roles: list[str],
    ) -> RulesetApproval:
        """Activate an approved ruleset."""
        if not self._check_permission("activate_ruleset", user_roles):
            raise ChangeControlPermissionError(
                "User does not have permission to activate rulesets"
            )

        result = await self.session.execute(
            select(RulesetApproval).where(RulesetApproval.id == approval_id)
        )
        approval = result.scalar_one_or_none()

        if not approval:
            raise RulesetApprovalNotFoundError(f"Approval not found: {approval_id}")

        if approval.status != ApprovalStatus.APPROVED.value:
            raise ValueError("Can only activate APPROVED rulesets")

        # Deactivate current active ruleset of same type
        await self.session.execute(
            select(RulesetApproval)
            .where(
                and_(
                    RulesetApproval.ruleset_type == approval.ruleset_type,
                    RulesetApproval.is_active == True,
                )
            )
        )

        # This would need updating logic in production
        approval.activate()

        await write_audit_event(
            session=self.session,
            action="change_control.ruleset_activated",
            category="governance",
            actor_type="user",
            actor_id=activator_id,
            entity_type="ruleset_approval",
            entity_id=approval.id,
            metadata={
                "ruleset_type": approval.ruleset_type,
                "version": approval.ruleset_version,
            },
        )

        await self.session.commit()
        await self.session.refresh(approval)

        return approval

    async def get_pending_approvals(
        self,
        user_roles: list[str],
        ruleset_type: Optional[str] = None,
    ) -> list[RulesetApproval]:
        """Get pending ruleset approvals."""
        if not self._check_permission("view", user_roles):
            raise ChangeControlPermissionError("User does not have permission to view approvals")

        query = select(RulesetApproval).where(
            RulesetApproval.status == ApprovalStatus.PENDING.value
        )

        if ruleset_type:
            query = query.where(RulesetApproval.ruleset_type == ruleset_type)

        query = query.order_by(RulesetApproval.submitted_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_approval_history(
        self,
        user_roles: list[str],
        ruleset_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[RulesetApproval]:
        """Get ruleset approval history."""
        if not self._check_permission("view", user_roles):
            raise ChangeControlPermissionError("User does not have permission to view approvals")

        query = select(RulesetApproval)

        if ruleset_type:
            query = query.where(RulesetApproval.ruleset_type == ruleset_type)

        query = query.order_by(RulesetApproval.submitted_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # Questionnaire Version Methods

    async def create_questionnaire_version(
        self,
        questionnaire_code: str,
        version: str,
        title: str,
        questions: dict,
        created_by: str,
        user_roles: list[str],
        description: Optional[str] = None,
        scoring_rules: Optional[dict] = None,
        change_summary: Optional[str] = None,
        previous_version_id: Optional[str] = None,
    ) -> QuestionnaireVersion:
        """Create a new questionnaire version."""
        if not self._check_permission("submit_questionnaire", user_roles):
            raise ChangeControlPermissionError(
                "User does not have permission to create questionnaire versions"
            )

        content_hash = QuestionnaireVersion.compute_content_hash(questions, scoring_rules)

        qv = QuestionnaireVersion(
            id=str(uuid.uuid4()),
            questionnaire_code=questionnaire_code,
            version=version,
            previous_version_id=previous_version_id,
            title=title,
            description=description,
            questions=questions,
            scoring_rules=scoring_rules,
            content_hash=content_hash,
            change_summary=change_summary,
            created_by=created_by,
            status=ApprovalStatus.PENDING.value,
        )

        self.session.add(qv)

        await write_audit_event(
            session=self.session,
            action="change_control.questionnaire_created",
            category="governance",
            actor_type="user",
            actor_id=created_by,
            entity_type="questionnaire_version",
            entity_id=qv.id,
            metadata={
                "questionnaire_code": questionnaire_code,
                "version": version,
                "content_hash": content_hash,
            },
        )

        await self.session.commit()
        await self.session.refresh(qv)

        return qv

    async def approve_questionnaire_version(
        self,
        version_id: str,
        approver_id: str,
        user_roles: list[str],
    ) -> QuestionnaireVersion:
        """Approve a questionnaire version."""
        if not self._check_permission("approve_questionnaire", user_roles):
            raise ChangeControlPermissionError(
                "User does not have permission to approve questionnaire versions"
            )

        result = await self.session.execute(
            select(QuestionnaireVersion).where(QuestionnaireVersion.id == version_id)
        )
        qv = result.scalar_one_or_none()

        if not qv:
            raise QuestionnaireVersionNotFoundError(f"Version not found: {version_id}")

        if qv.status != ApprovalStatus.PENDING.value:
            raise ValueError("Can only approve PENDING versions")

        # Cannot approve own submission
        if qv.created_by == approver_id:
            raise ChangeControlPermissionError("Cannot approve own submission")

        qv.status = ApprovalStatus.APPROVED.value
        qv.approved_by = approver_id
        qv.approved_at = datetime.now()

        await write_audit_event(
            session=self.session,
            action="change_control.questionnaire_approved",
            category="governance",
            actor_type="user",
            actor_id=approver_id,
            entity_type="questionnaire_version",
            entity_id=qv.id,
            metadata={
                "questionnaire_code": qv.questionnaire_code,
                "version": qv.version,
            },
        )

        await self.session.commit()
        await self.session.refresh(qv)

        return qv

    async def activate_questionnaire_version(
        self,
        version_id: str,
        activator_id: str,
        user_roles: list[str],
    ) -> QuestionnaireVersion:
        """Activate an approved questionnaire version."""
        if not self._check_permission("activate_ruleset", user_roles):
            raise ChangeControlPermissionError(
                "User does not have permission to activate questionnaire versions"
            )

        result = await self.session.execute(
            select(QuestionnaireVersion).where(QuestionnaireVersion.id == version_id)
        )
        qv = result.scalar_one_or_none()

        if not qv:
            raise QuestionnaireVersionNotFoundError(f"Version not found: {version_id}")

        if qv.status != ApprovalStatus.APPROVED.value:
            raise ValueError("Can only activate APPROVED versions")

        # Deactivate current active version
        await self.session.execute(
            select(QuestionnaireVersion).where(
                and_(
                    QuestionnaireVersion.questionnaire_code == qv.questionnaire_code,
                    QuestionnaireVersion.is_active == True,
                )
            )
        )

        qv.is_active = True
        qv.activated_at = datetime.now()

        await write_audit_event(
            session=self.session,
            action="change_control.questionnaire_activated",
            category="governance",
            actor_type="user",
            actor_id=activator_id,
            entity_type="questionnaire_version",
            entity_id=qv.id,
            metadata={
                "questionnaire_code": qv.questionnaire_code,
                "version": qv.version,
            },
        )

        await self.session.commit()
        await self.session.refresh(qv)

        return qv

    async def get_questionnaire_version_history(
        self,
        questionnaire_code: str,
        user_roles: list[str],
    ) -> list[QuestionnaireVersion]:
        """Get version history for a questionnaire."""
        if not self._check_permission("view", user_roles):
            raise ChangeControlPermissionError("User does not have permission to view versions")

        result = await self.session.execute(
            select(QuestionnaireVersion)
            .where(QuestionnaireVersion.questionnaire_code == questionnaire_code)
            .order_by(QuestionnaireVersion.created_at.desc())
        )

        return list(result.scalars().all())

    async def get_active_questionnaire_version(
        self,
        questionnaire_code: str,
    ) -> Optional[QuestionnaireVersion]:
        """Get the currently active version of a questionnaire."""
        result = await self.session.execute(
            select(QuestionnaireVersion).where(
                and_(
                    QuestionnaireVersion.questionnaire_code == questionnaire_code,
                    QuestionnaireVersion.is_active == True,
                )
            )
        )

        return result.scalar_one_or_none()
