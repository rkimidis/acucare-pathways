"""Triage dashboard API endpoints for staff."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, get_client_ip, get_request_id, require_permissions
from app.models.audit_event import ActorType
from app.models.triage_case import TriageCase, TriageTier
from app.services.audit import write_audit_event
from app.services.disposition import DashboardService, DispositionService
from app.services.rbac import Permission
from app.services.storage import get_storage_backend
from app.services.triage_note import PDFExporter, TriageNoteGenerator

router = APIRouter()


class QueueCountsResponse(BaseModel):
    """Response for queue counts."""

    red: int
    amber: int
    green: int
    blue: int
    total: int
    breached: int


class QueueItemResponse(BaseModel):
    """Single item in the triage queue."""

    id: str
    patient_id: str
    tier: str | None
    pathway: str | None
    status: str | None
    created_at: str | None
    triaged_at: str | None
    sla_deadline: str | None
    sla_target_minutes: int | None
    sla_remaining_minutes: int | None
    sla_status: str
    sla_breached: bool
    clinician_review_required: bool
    assigned_clinician_id: str | None


class QueueResponse(BaseModel):
    """Response for triage queue."""

    items: list[QueueItemResponse]
    total_count: int


@router.get(
    "/queue/counts",
    response_model=QueueCountsResponse,
    summary="Get queue counts by tier",
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_queue_counts(
    session: DbSession,
    current_user: CurrentUser,
) -> QueueCountsResponse:
    """Get count of pending cases by tier.

    Returns counts for each tier and total breached cases.
    """
    dashboard = DashboardService(session)

    counts = await dashboard.get_queue_counts()
    breached = await dashboard.get_breached_cases_count()

    return QueueCountsResponse(
        red=counts["red"],
        amber=counts["amber"],
        green=counts["green"],
        blue=counts["blue"],
        total=counts["total"],
        breached=breached,
    )


@router.get(
    "/queue",
    response_model=QueueResponse,
    summary="Get triage queue",
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_queue(
    session: DbSession,
    current_user: CurrentUser,
    tier: Annotated[str | None, Query(description="Filter by tier (red, amber, green, blue)")] = None,
    include_reviewed: Annotated[bool, Query(description="Include already reviewed cases")] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> QueueResponse:
    """Get triage queue with optional filters.

    Queue is ordered by SLA deadline (most urgent first).
    """
    dashboard = DashboardService(session)

    tier_enum = None
    if tier:
        try:
            tier_enum = TriageTier(tier.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier: {tier}. Must be one of: red, amber, green, blue",
            )

    items = await dashboard.get_queue_by_tier(
        tier=tier_enum,
        include_reviewed=include_reviewed,
        limit=limit,
        offset=offset,
    )

    # Get total count for tier
    counts = await dashboard.get_queue_counts()
    total = counts.get(tier.lower() if tier else "total", 0)

    return QueueResponse(
        items=[QueueItemResponse(**item) for item in items],
        total_count=total,
    )


@router.get(
    "/cases/{case_id}/summary",
    summary="Get case summary for clinician review",
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_case_summary(
    case_id: str,
    session: DbSession,
    current_user: CurrentUser,
):
    """Get detailed case summary for clinician review.

    Includes scores, risk flags, draft disposition, and raw answers.
    """
    dashboard = DashboardService(session)

    summary = await dashboard.get_case_summary(case_id)

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )

    return summary


class ConfirmDispositionRequest(BaseModel):
    """Request to confirm draft disposition."""

    clinical_notes: str | None = Field(None, max_length=10000)


class OverrideDispositionRequest(BaseModel):
    """Request to override disposition."""

    tier: str = Field(..., description="New tier (RED, AMBER, GREEN, BLUE)")
    pathway: str = Field(..., max_length=100)
    rationale: str = Field(..., min_length=10, max_length=5000, description="Required explanation for override")
    clinical_notes: str | None = Field(None, max_length=10000)


class DispositionFinalResponse(BaseModel):
    """Response for finalized disposition."""

    id: str
    triage_case_id: str
    tier: str
    pathway: str
    self_book_allowed: bool
    is_override: bool
    original_tier: str | None
    original_pathway: str | None
    rationale: str | None
    clinician_id: str
    finalized_at: str


@router.post(
    "/cases/{case_id}/disposition/confirm",
    response_model=DispositionFinalResponse,
    summary="Confirm draft disposition",
    dependencies=[Depends(require_permissions(Permission.DISPOSITION_CONFIRM))],
)
async def confirm_disposition(
    case_id: str,
    request_body: ConfirmDispositionRequest,
    session: DbSession,
    current_user: CurrentUser,
    request: Request,
):
    """Confirm the draft disposition without changes.

    Creates a final disposition matching the draft.
    """
    from app.services.disposition import DispositionAlreadyFinalizedError

    disposition_service = DispositionService(session)

    try:
        final = await disposition_service.confirm_disposition(
            triage_case_id=case_id,
            clinician=current_user,
            clinical_notes=request_body.clinical_notes,
            ip_address=get_client_ip(request),
            request_id=get_request_id(request),
        )
    except DispositionAlreadyFinalizedError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    return DispositionFinalResponse(
        id=final.id,
        triage_case_id=final.triage_case_id,
        tier=final.tier,
        pathway=final.pathway,
        self_book_allowed=final.self_book_allowed,
        is_override=final.is_override,
        original_tier=final.original_tier,
        original_pathway=final.original_pathway,
        rationale=final.rationale,
        clinician_id=final.clinician_id,
        finalized_at=final.finalized_at.isoformat(),
    )


@router.post(
    "/cases/{case_id}/disposition/override",
    response_model=DispositionFinalResponse,
    summary="Override disposition",
    dependencies=[Depends(require_permissions(Permission.DISPOSITION_OVERRIDE))],
)
async def override_disposition(
    case_id: str,
    request_body: OverrideDispositionRequest,
    session: DbSession,
    current_user: CurrentUser,
    request: Request,
):
    """Override the draft disposition with a new tier/pathway.

    IMPORTANT: Rationale is REQUIRED for overrides.
    """
    from app.services.disposition import (
        DispositionAlreadyFinalizedError,
        RationaleRequiredError,
    )

    # Validate tier
    valid_tiers = ["RED", "AMBER", "GREEN", "BLUE"]
    if request_body.tier.upper() not in valid_tiers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier: {request_body.tier}. Must be one of: {valid_tiers}",
        )

    disposition_service = DispositionService(session)

    try:
        final = await disposition_service.override_disposition(
            triage_case_id=case_id,
            clinician=current_user,
            new_tier=request_body.tier,
            new_pathway=request_body.pathway,
            rationale=request_body.rationale,
            clinical_notes=request_body.clinical_notes,
            ip_address=get_client_ip(request),
            request_id=get_request_id(request),
        )
    except RationaleRequiredError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except DispositionAlreadyFinalizedError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    return DispositionFinalResponse(
        id=final.id,
        triage_case_id=final.triage_case_id,
        tier=final.tier,
        pathway=final.pathway,
        self_book_allowed=final.self_book_allowed,
        is_override=final.is_override,
        original_tier=final.original_tier,
        original_pathway=final.original_pathway,
        rationale=final.rationale,
        clinician_id=final.clinician_id,
        finalized_at=final.finalized_at.isoformat(),
    )


class TriageNoteResponse(BaseModel):
    """Response for triage note generation."""

    case_id: str
    note_url: str
    generated_at: str


@router.post(
    "/cases/{case_id}/note/generate",
    response_model=TriageNoteResponse,
    summary="Generate triage note PDF",
    dependencies=[Depends(require_permissions(Permission.DISPOSITION_EXPORT))],
)
async def generate_triage_note(
    case_id: str,
    session: DbSession,
    current_user: CurrentUser,
    request: Request,
):
    """Generate and store a PDF triage note for the case.

    The note is stored in object storage and the URL is returned.
    """
    dashboard = DashboardService(session)

    # Get case summary
    summary = await dashboard.get_case_summary(case_id)

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )

    # Generate PDF
    exporter = PDFExporter()
    pdf_bytes = exporter.generate_pdf(summary)

    # Upload to storage
    storage = get_storage_backend()
    filename = f"triage_note_{case_id[:8]}.pdf"

    try:
        note_url = await storage.upload(
            file_data=pdf_bytes,
            filename=filename,
            content_type="application/pdf",
            folder="triage-notes",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store PDF: {str(e)}",
        )

    # Update case with note URL
    now = datetime.now(timezone.utc)
    case_result = await session.execute(
        select(TriageCase).where(TriageCase.id == case_id)
    )
    case = case_result.scalar_one_or_none()
    if case:
        case.triage_note_url = note_url
        case.triage_note_generated_at = now
        await session.commit()

    # Write audit event
    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=current_user.id,
        actor_email=current_user.email,
        action="triage_note.export",
        action_category="clinical",
        entity_type="triage_case",
        entity_id=case_id,
        description=f"Triage note PDF generated for case {case_id[:8]}",
        metadata={
            "note_url": note_url,
            "generated_by": current_user.id,
        },
        ip_address=get_client_ip(request),
        request_id=get_request_id(request),
    )

    return TriageNoteResponse(
        case_id=case_id,
        note_url=note_url,
        generated_at=now.isoformat(),
    )


@router.get(
    "/cases/{case_id}/note/download",
    summary="Download triage note PDF",
    dependencies=[Depends(require_permissions(Permission.DISPOSITION_EXPORT))],
)
async def download_triage_note(
    case_id: str,
    session: DbSession,
    current_user: CurrentUser,
):
    """Download the triage note PDF for a case.

    Generates a new PDF in real-time (not stored).
    """
    dashboard = DashboardService(session)

    # Get case summary
    summary = await dashboard.get_case_summary(case_id)

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )

    # Generate PDF
    exporter = PDFExporter()
    pdf_bytes = exporter.generate_pdf(summary)

    # Return as downloadable file
    filename = f"triage_note_{case_id[:8]}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get(
    "/cases/{case_id}/note/text",
    summary="Get triage note as text",
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_triage_note_text(
    case_id: str,
    session: DbSession,
    current_user: CurrentUser,
):
    """Get the triage note as plain text (template-based narrative)."""
    dashboard = DashboardService(session)

    # Get case summary
    summary = await dashboard.get_case_summary(case_id)

    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case {case_id} not found",
        )

    # Generate narrative
    generator = TriageNoteGenerator(summary)
    narrative = generator.generate_narrative()

    return {"case_id": case_id, "narrative": narrative}
