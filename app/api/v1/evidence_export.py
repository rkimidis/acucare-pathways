"""Evidence export API endpoints for Sprint 6."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.services.evidence_export import EvidenceExportService

router = APIRouter(prefix="/evidence", tags=["evidence-export"])


# Request/Response Models


class AuditExportRequest(BaseModel):
    """Request to export audit log."""
    start_date: datetime
    end_date: datetime
    export_reason: str = Field(..., min_length=10)
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    category: Optional[str] = None


class CasePathwayExportRequest(BaseModel):
    """Request to export case pathway."""
    triage_case_id: str
    export_reason: str = Field(..., min_length=10)


class EvidenceBundleRequest(BaseModel):
    """Request to export comprehensive evidence bundle."""
    start_date: datetime
    end_date: datetime
    export_reason: str = Field(..., min_length=10)
    include_audit_log: bool = True
    include_incidents: bool = True
    include_ruleset_approvals: bool = True
    include_reporting_summary: bool = True


class VerifyExportRequest(BaseModel):
    """Request to verify export integrity."""
    export_data: dict


class ExportRecordResponse(BaseModel):
    """Export record response."""
    id: str
    export_type: str
    date_range_start: Optional[datetime]
    date_range_end: Optional[datetime]
    triage_case_id: Optional[str]
    exported_by: str
    exported_at: datetime
    export_reason: str
    file_name: str
    file_size_bytes: int
    file_format: str
    content_hash: str
    record_count: int
    download_count: int
    last_downloaded_at: Optional[datetime]

    class Config:
        from_attributes = True


class ExportHistoryResponse(BaseModel):
    """Export history response."""
    exports: list[ExportRecordResponse]


class IntegrityVerificationResponse(BaseModel):
    """Export integrity verification response."""
    is_valid: bool
    content_hash: str
    message: str


# Endpoints


@router.post("/audit-log")
async def export_audit_log(
    request: AuditExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    """Export audit events for a date range.

    Returns tamper-evident export with chained hash.
    """
    service = EvidenceExportService(db)

    export_data, export_record = await service.export_audit_log(
        start_date=request.start_date,
        end_date=request.end_date,
        exported_by=current_user["id"],
        export_reason=request.export_reason,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        category=request.category,
    )

    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f'attachment; filename="{export_record.file_name}"',
            "X-Content-Hash": export_record.content_hash,
            "X-Record-Count": str(export_record.record_count),
        },
    )


@router.post("/case-pathway")
async def export_case_pathway(
    request: CasePathwayExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    """Export complete pathway for a case.

    Shows decisions, rules fired, and timestamps.
    Returns tamper-evident export with chained hash.
    """
    service = EvidenceExportService(db)

    try:
        export_data, export_record = await service.export_case_pathway(
            triage_case_id=request.triage_case_id,
            exported_by=current_user["id"],
            export_reason=request.export_reason,
        )

        return JSONResponse(
            content=export_data,
            headers={
                "Content-Disposition": f'attachment; filename="{export_record.file_name}"',
                "X-Content-Hash": export_record.content_hash,
                "X-Record-Count": str(export_record.record_count),
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/bundle")
async def export_evidence_bundle(
    request: EvidenceBundleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> JSONResponse:
    """Export comprehensive evidence bundle for CQC inspection.

    Combines audit logs, incidents, ruleset approvals, and reporting summary
    into a single tamper-evident export file.
    """
    service = EvidenceExportService(db)

    export_data, export_record = await service.export_evidence_bundle(
        start_date=request.start_date,
        end_date=request.end_date,
        exported_by=current_user["id"],
        export_reason=request.export_reason,
        include_audit_log=request.include_audit_log,
        include_incidents=request.include_incidents,
        include_ruleset_approvals=request.include_ruleset_approvals,
        include_reporting_summary=request.include_reporting_summary,
    )

    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f'attachment; filename="{export_record.file_name}"',
            "X-Content-Hash": export_record.content_hash,
            "X-Record-Count": str(export_record.record_count),
            "X-Export-Type": "evidence_bundle",
        },
    )


@router.post("/verify", response_model=IntegrityVerificationResponse)
async def verify_export_integrity(
    request: VerifyExportRequest,
    current_user: dict = Depends(get_current_user),
) -> IntegrityVerificationResponse:
    """Verify the integrity of an export by recalculating the hash."""
    is_valid = EvidenceExportService.verify_export_integrity(request.export_data)

    manifest = request.export_data.get("manifest", {})
    content_hash = manifest.get("content_hash", "")

    if is_valid:
        return IntegrityVerificationResponse(
            is_valid=True,
            content_hash=content_hash,
            message="Export integrity verified. Hash matches.",
        )
    else:
        return IntegrityVerificationResponse(
            is_valid=False,
            content_hash=content_hash,
            message="Export integrity check FAILED. Data may have been tampered with.",
        )


@router.get("/history", response_model=ExportHistoryResponse)
async def get_export_history(
    export_type: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> ExportHistoryResponse:
    """Get history of evidence exports."""
    service = EvidenceExportService(db)

    exports = await service.get_export_history(
        export_type=export_type,
        limit=limit,
    )

    return ExportHistoryResponse(
        exports=[ExportRecordResponse.model_validate(e) for e in exports]
    )


@router.post("/{export_id}/record-download")
async def record_download(
    export_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Record that an export was downloaded."""
    service = EvidenceExportService(db)

    await service.record_download(
        export_id=export_id,
        downloaded_by=current_user["id"],
    )

    return {"message": "Download recorded"}
