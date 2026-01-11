"""Incident management API endpoints for Sprint 6."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.governance import IncidentCategory, IncidentSeverity, IncidentStatus
from app.services.incident import (
    IncidentNotFoundError,
    IncidentPermissionError,
    IncidentService,
    IncidentWorkflowError,
)

router = APIRouter(prefix="/incidents", tags=["incidents"])


# Request/Response Models


class CreateIncidentRequest(BaseModel):
    """Request to create an incident."""
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10)
    category: str = Field(default=IncidentCategory.OTHER.value)
    severity: str = Field(default=IncidentSeverity.MEDIUM.value)
    triage_case_id: Optional[str] = None
    patient_id: Optional[str] = None
    immediate_actions_taken: Optional[str] = None


class StartReviewRequest(BaseModel):
    """Request to start review of an incident."""
    pass


class AddReviewNotesRequest(BaseModel):
    """Request to add review notes."""
    notes: str = Field(..., min_length=1)


class CloseIncidentRequest(BaseModel):
    """Request to close an incident."""
    closure_reason: str = Field(..., min_length=10)
    lessons_learned: Optional[str] = None
    preventive_actions: Optional[str] = None


class ReopenIncidentRequest(BaseModel):
    """Request to reopen an incident."""
    reason: str = Field(..., min_length=10)


class IncidentResponse(BaseModel):
    """Incident response model."""
    id: str
    reference_number: str
    title: str
    description: str
    category: str
    severity: str
    status: str
    triage_case_id: Optional[str]
    patient_id: Optional[str]
    immediate_actions_taken: Optional[str]
    reported_by: str
    reported_at: datetime
    reviewer_id: Optional[str]
    review_started_at: Optional[datetime]
    review_notes: Optional[str]
    closed_by: Optional[str]
    closed_at: Optional[datetime]
    closure_reason: Optional[str]
    lessons_learned: Optional[str]
    preventive_actions: Optional[str]
    reportable_to_cqc: bool
    cqc_reported_at: Optional[datetime]

    class Config:
        from_attributes = True


class IncidentListResponse(BaseModel):
    """Paginated incident list response."""
    items: list[IncidentResponse]
    total: int
    limit: int
    offset: int


class IncidentCountsResponse(BaseModel):
    """Incident counts by status."""
    open: int = 0
    under_review: int = 0
    closed: int = 0


# Endpoints


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    request: CreateIncidentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> IncidentResponse:
    """Create a new incident."""
    service = IncidentService(db)

    try:
        incident = await service.create_incident(
            title=request.title,
            description=request.description,
            category=request.category,
            severity=request.severity,
            reported_by=current_user["id"],
            user_roles=current_user.get("roles", []),
            triage_case_id=request.triage_case_id,
            patient_id=request.patient_id,
            immediate_actions=request.immediate_actions_taken,
        )
        return IncidentResponse.model_validate(incident)
    except IncidentPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    status_filter: Optional[str] = None,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> IncidentListResponse:
    """List incidents with optional filters."""
    service = IncidentService(db)

    try:
        incidents, total = await service.list_incidents(
            user_roles=current_user.get("roles", []),
            status=status_filter,
            severity=severity,
            category=category,
            limit=limit,
            offset=offset,
        )
        return IncidentListResponse(
            items=[IncidentResponse.model_validate(i) for i in incidents],
            total=total,
            limit=limit,
            offset=offset,
        )
    except IncidentPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/counts", response_model=IncidentCountsResponse)
async def get_incident_counts(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> IncidentCountsResponse:
    """Get incident counts by status."""
    service = IncidentService(db)

    try:
        counts = await service.get_incident_counts_by_status(
            user_roles=current_user.get("roles", []),
        )
        return IncidentCountsResponse(
            open=counts.get(IncidentStatus.OPEN.value, 0),
            under_review=counts.get(IncidentStatus.UNDER_REVIEW.value, 0),
            closed=counts.get(IncidentStatus.CLOSED.value, 0),
        )
    except IncidentPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> IncidentResponse:
    """Get incident by ID."""
    service = IncidentService(db)

    try:
        incident = await service.get_incident(
            incident_id=incident_id,
            user_roles=current_user.get("roles", []),
        )
        return IncidentResponse.model_validate(incident)
    except IncidentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except IncidentPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{incident_id}/start-review", response_model=IncidentResponse)
async def start_review(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> IncidentResponse:
    """Start review of an incident."""
    service = IncidentService(db)

    try:
        incident = await service.start_review(
            incident_id=incident_id,
            reviewer_id=current_user["id"],
            user_roles=current_user.get("roles", []),
        )
        return IncidentResponse.model_validate(incident)
    except IncidentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except IncidentPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except IncidentWorkflowError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{incident_id}/review-notes", response_model=IncidentResponse)
async def add_review_notes(
    incident_id: str,
    request: AddReviewNotesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> IncidentResponse:
    """Add review notes to an incident."""
    service = IncidentService(db)

    try:
        incident = await service.add_review_notes(
            incident_id=incident_id,
            reviewer_id=current_user["id"],
            notes=request.notes,
            user_roles=current_user.get("roles", []),
        )
        return IncidentResponse.model_validate(incident)
    except IncidentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except IncidentPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except IncidentWorkflowError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{incident_id}/close", response_model=IncidentResponse)
async def close_incident(
    incident_id: str,
    request: CloseIncidentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> IncidentResponse:
    """Close an incident."""
    service = IncidentService(db)

    try:
        incident = await service.close_incident(
            incident_id=incident_id,
            closed_by=current_user["id"],
            closure_reason=request.closure_reason,
            user_roles=current_user.get("roles", []),
            lessons_learned=request.lessons_learned,
            preventive_actions=request.preventive_actions,
        )
        return IncidentResponse.model_validate(incident)
    except IncidentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except IncidentPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except IncidentWorkflowError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{incident_id}/reopen", response_model=IncidentResponse)
async def reopen_incident(
    incident_id: str,
    request: ReopenIncidentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> IncidentResponse:
    """Reopen a closed incident."""
    service = IncidentService(db)

    try:
        incident = await service.reopen_incident(
            incident_id=incident_id,
            reopened_by=current_user["id"],
            reason=request.reason,
            user_roles=current_user.get("roles", []),
        )
        return IncidentResponse.model_validate(incident)
    except IncidentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except IncidentPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except IncidentWorkflowError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{incident_id}/mark-cqc-reportable", response_model=IncidentResponse)
async def mark_cqc_reportable(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> IncidentResponse:
    """Mark incident as CQC reportable."""
    service = IncidentService(db)

    try:
        incident = await service.mark_cqc_reportable(
            incident_id=incident_id,
            marked_by=current_user["id"],
            user_roles=current_user.get("roles", []),
        )
        return IncidentResponse.model_validate(incident)
    except IncidentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except IncidentPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{incident_id}/report-to-cqc", response_model=IncidentResponse)
async def report_to_cqc(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> IncidentResponse:
    """Record that incident was reported to CQC."""
    service = IncidentService(db)

    try:
        incident = await service.report_to_cqc(
            incident_id=incident_id,
            reported_by=current_user["id"],
            user_roles=current_user.get("roles", []),
        )
        return IncidentResponse.model_validate(incident)
    except IncidentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except IncidentPermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except IncidentWorkflowError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
