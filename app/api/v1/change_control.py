"""Change control API endpoints for Sprint 6."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.services.change_control import (
    ChangeControlPermissionError,
    ChangeControlService,
    QuestionnaireVersionNotFoundError,
    RulesetApprovalNotFoundError,
)

router = APIRouter(prefix="/change-control", tags=["change-control"])


# Request/Response Models


class SubmitRulesetRequest(BaseModel):
    """Request to submit a ruleset change."""
    ruleset_type: str = Field(..., min_length=1)
    ruleset_version: str = Field(..., min_length=1)
    change_summary: str = Field(..., min_length=10)
    change_rationale: str = Field(..., min_length=10)
    content: dict
    previous_version: Optional[str] = None
    rules_added: Optional[dict] = None
    rules_modified: Optional[dict] = None
    rules_removed: Optional[dict] = None


class ApproveRulesetRequest(BaseModel):
    """Request to approve a ruleset change."""
    notes: Optional[str] = None


class RejectRulesetRequest(BaseModel):
    """Request to reject a ruleset change."""
    rejection_reason: str = Field(..., min_length=10)


class RulesetApprovalResponse(BaseModel):
    """Ruleset approval response."""
    id: str
    ruleset_type: str
    ruleset_version: str
    previous_version: Optional[str]
    change_summary: str
    change_rationale: str
    content_hash: str
    submitted_by: str
    submitted_at: datetime
    status: str
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    approval_notes: Optional[str]
    rejected_by: Optional[str]
    rejected_at: Optional[datetime]
    rejection_reason: Optional[str]
    is_active: bool
    activated_at: Optional[datetime]

    class Config:
        from_attributes = True


class CreateQuestionnaireVersionRequest(BaseModel):
    """Request to create a questionnaire version."""
    questionnaire_code: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    questions: dict
    description: Optional[str] = None
    scoring_rules: Optional[dict] = None
    change_summary: Optional[str] = None
    previous_version_id: Optional[str] = None


class QuestionnaireVersionResponse(BaseModel):
    """Questionnaire version response."""
    id: str
    questionnaire_code: str
    version: str
    previous_version_id: Optional[str]
    title: str
    description: Optional[str]
    content_hash: str
    change_summary: Optional[str]
    created_by: str
    status: str
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    is_active: bool
    activated_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# Ruleset Endpoints


@router.post("/rulesets", response_model=RulesetApprovalResponse, status_code=status.HTTP_201_CREATED)
async def submit_ruleset_change(
    request: SubmitRulesetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> RulesetApprovalResponse:
    """Submit a ruleset change for approval."""
    service = ChangeControlService(db)

    try:
        approval = await service.submit_ruleset_change(
            ruleset_type=request.ruleset_type,
            ruleset_version=request.ruleset_version,
            change_summary=request.change_summary,
            change_rationale=request.change_rationale,
            content=request.content,
            submitted_by=current_user["id"],
            user_roles=current_user.get("roles", []),
            previous_version=request.previous_version,
            rules_added=request.rules_added,
            rules_modified=request.rules_modified,
            rules_removed=request.rules_removed,
        )
        return RulesetApprovalResponse.model_validate(approval)
    except ChangeControlPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/rulesets/pending", response_model=list[RulesetApprovalResponse])
async def get_pending_ruleset_approvals(
    ruleset_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[RulesetApprovalResponse]:
    """Get pending ruleset approvals."""
    service = ChangeControlService(db)

    try:
        approvals = await service.get_pending_approvals(
            user_roles=current_user.get("roles", []),
            ruleset_type=ruleset_type,
        )
        return [RulesetApprovalResponse.model_validate(a) for a in approvals]
    except ChangeControlPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/rulesets/history", response_model=list[RulesetApprovalResponse])
async def get_ruleset_approval_history(
    ruleset_type: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[RulesetApprovalResponse]:
    """Get ruleset approval history."""
    service = ChangeControlService(db)

    try:
        approvals = await service.get_approval_history(
            user_roles=current_user.get("roles", []),
            ruleset_type=ruleset_type,
            limit=limit,
        )
        return [RulesetApprovalResponse.model_validate(a) for a in approvals]
    except ChangeControlPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/rulesets/{approval_id}/approve", response_model=RulesetApprovalResponse)
async def approve_ruleset(
    approval_id: str,
    request: ApproveRulesetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> RulesetApprovalResponse:
    """Approve a ruleset change."""
    service = ChangeControlService(db)

    try:
        approval = await service.approve_ruleset(
            approval_id=approval_id,
            approver_id=current_user["id"],
            user_roles=current_user.get("roles", []),
            notes=request.notes,
        )
        return RulesetApprovalResponse.model_validate(approval)
    except RulesetApprovalNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ChangeControlPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/rulesets/{approval_id}/reject", response_model=RulesetApprovalResponse)
async def reject_ruleset(
    approval_id: str,
    request: RejectRulesetRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> RulesetApprovalResponse:
    """Reject a ruleset change."""
    service = ChangeControlService(db)

    try:
        approval = await service.reject_ruleset(
            approval_id=approval_id,
            rejector_id=current_user["id"],
            rejection_reason=request.rejection_reason,
            user_roles=current_user.get("roles", []),
        )
        return RulesetApprovalResponse.model_validate(approval)
    except RulesetApprovalNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ChangeControlPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/rulesets/{approval_id}/activate", response_model=RulesetApprovalResponse)
async def activate_ruleset(
    approval_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> RulesetApprovalResponse:
    """Activate an approved ruleset."""
    service = ChangeControlService(db)

    try:
        approval = await service.activate_ruleset(
            approval_id=approval_id,
            activator_id=current_user["id"],
            user_roles=current_user.get("roles", []),
        )
        return RulesetApprovalResponse.model_validate(approval)
    except RulesetApprovalNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ChangeControlPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Questionnaire Version Endpoints


@router.post("/questionnaires", response_model=QuestionnaireVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_questionnaire_version(
    request: CreateQuestionnaireVersionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> QuestionnaireVersionResponse:
    """Create a new questionnaire version."""
    service = ChangeControlService(db)

    try:
        version = await service.create_questionnaire_version(
            questionnaire_code=request.questionnaire_code,
            version=request.version,
            title=request.title,
            questions=request.questions,
            created_by=current_user["id"],
            user_roles=current_user.get("roles", []),
            description=request.description,
            scoring_rules=request.scoring_rules,
            change_summary=request.change_summary,
            previous_version_id=request.previous_version_id,
        )
        return QuestionnaireVersionResponse.model_validate(version)
    except ChangeControlPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/questionnaires/{questionnaire_code}/history", response_model=list[QuestionnaireVersionResponse])
async def get_questionnaire_version_history(
    questionnaire_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[QuestionnaireVersionResponse]:
    """Get version history for a questionnaire."""
    service = ChangeControlService(db)

    try:
        versions = await service.get_questionnaire_version_history(
            questionnaire_code=questionnaire_code,
            user_roles=current_user.get("roles", []),
        )
        return [QuestionnaireVersionResponse.model_validate(v) for v in versions]
    except ChangeControlPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/questionnaires/{questionnaire_code}/active", response_model=QuestionnaireVersionResponse)
async def get_active_questionnaire_version(
    questionnaire_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> QuestionnaireVersionResponse:
    """Get the currently active version of a questionnaire."""
    service = ChangeControlService(db)

    version = await service.get_active_questionnaire_version(questionnaire_code)

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active version found for questionnaire: {questionnaire_code}",
        )

    return QuestionnaireVersionResponse.model_validate(version)


@router.post("/questionnaires/{version_id}/approve", response_model=QuestionnaireVersionResponse)
async def approve_questionnaire_version(
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> QuestionnaireVersionResponse:
    """Approve a questionnaire version."""
    service = ChangeControlService(db)

    try:
        version = await service.approve_questionnaire_version(
            version_id=version_id,
            approver_id=current_user["id"],
            user_roles=current_user.get("roles", []),
        )
        return QuestionnaireVersionResponse.model_validate(version)
    except QuestionnaireVersionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ChangeControlPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/questionnaires/{version_id}/activate", response_model=QuestionnaireVersionResponse)
async def activate_questionnaire_version(
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> QuestionnaireVersionResponse:
    """Activate an approved questionnaire version."""
    service = ChangeControlService(db)

    try:
        version = await service.activate_questionnaire_version(
            version_id=version_id,
            activator_id=current_user["id"],
            user_roles=current_user.get("roles", []),
        )
        return QuestionnaireVersionResponse.model_validate(version)
    except QuestionnaireVersionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ChangeControlPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
