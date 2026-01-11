"""Triage case endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession, require_permissions
from app.models.audit_event import ActorType
from app.models.disposition import DispositionDraft, DispositionFinal, RiskFlag
from app.models.triage_case import TriageCase, TriageCaseStatus, TriageTier
from app.schemas.disposition import (
    CaseSummary,
    DispositionDraftRead,
    DispositionFinalize,
    DispositionFinalRead,
    QueueItem,
    QueueResponse,
)
from app.schemas.triage_case import TriageCaseCreate, TriageCaseRead, TriageCaseUpdate
from app.services.audit import write_audit_event
from app.services.rbac import Permission

router = APIRouter()


@router.get(
    "",
    response_model=list[TriageCaseRead],
    status_code=status.HTTP_200_OK,
    summary="List triage cases",
    description="Get all triage cases (staff only)",
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def list_triage_cases(
    session: DbSession,
    user: CurrentUser,
    limit: int = 100,
    offset: int = 0,
) -> list[TriageCaseRead]:
    """List all triage cases.

    Args:
        session: Database session
        user: Current authenticated user
        limit: Maximum results to return
        offset: Number of results to skip

    Returns:
        List of triage cases
    """
    result = await session.execute(
        select(TriageCase)
        .order_by(TriageCase.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    cases = result.scalars().all()
    return [TriageCaseRead.model_validate(c) for c in cases]


@router.get(
    "/{case_id}",
    response_model=TriageCaseRead,
    status_code=status.HTTP_200_OK,
    summary="Get triage case",
    description="Get a specific triage case by ID",
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_triage_case(
    case_id: str,
    session: DbSession,
    user: CurrentUser,
) -> TriageCaseRead:
    """Get a specific triage case.

    Args:
        case_id: UUID of the triage case
        session: Database session
        user: Current authenticated user

    Returns:
        Triage case details

    Raises:
        HTTPException: If case not found
    """
    result = await session.execute(
        select(TriageCase).where(TriageCase.id == case_id)
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Triage case not found",
        )

    return TriageCaseRead.model_validate(case)


@router.post(
    "",
    response_model=TriageCaseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create triage case",
    description="Create a new triage case for a patient",
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def create_triage_case(
    body: TriageCaseCreate,
    session: DbSession,
    user: CurrentUser,
) -> TriageCaseRead:
    """Create a new triage case.

    Args:
        body: Triage case creation data
        session: Database session
        user: Current authenticated user

    Returns:
        Created triage case
    """
    case = TriageCase(
        patient_id=body.patient_id,
    )

    session.add(case)
    await session.commit()
    await session.refresh(case)

    # Audit the creation
    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="triage_case_created",
        action_category="triage",
        entity_type="triage_case",
        entity_id=case.id,
        metadata={"patient_id": body.patient_id},
    )

    return TriageCaseRead.model_validate(case)


@router.patch(
    "/{case_id}",
    response_model=TriageCaseRead,
    status_code=status.HTTP_200_OK,
    summary="Update triage case",
    description="Update a triage case (status, assignment, notes)",
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def update_triage_case(
    case_id: str,
    body: TriageCaseUpdate,
    session: DbSession,
    user: CurrentUser,
) -> TriageCaseRead:
    """Update a triage case.

    Args:
        case_id: UUID of the triage case
        body: Update data
        session: Database session
        user: Current authenticated user

    Returns:
        Updated triage case

    Raises:
        HTTPException: If case not found
    """
    result = await session.execute(
        select(TriageCase).where(TriageCase.id == case_id)
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Triage case not found",
        )

    # Track changes for audit
    changes = {}

    if body.status is not None:
        changes["status"] = {"from": case.status.value, "to": body.status.value}
        case.status = body.status

    if body.assigned_clinician_id is not None:
        changes["assigned_clinician_id"] = {
            "from": case.assigned_clinician_id,
            "to": body.assigned_clinician_id,
        }
        case.assigned_clinician_id = body.assigned_clinician_id

    if body.clinical_notes is not None:
        changes["clinical_notes"] = "updated"
        case.clinical_notes = body.clinical_notes

    await session.commit()
    await session.refresh(case)

    # Audit the update
    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="triage_case_updated",
        action_category="triage",
        entity_type="triage_case",
        entity_id=case.id,
        metadata={"changes": changes},
    )

    return TriageCaseRead.model_validate(case)


@router.get(
    "/queue",
    response_model=QueueResponse,
    status_code=status.HTTP_200_OK,
    summary="Get triage queue",
    description="Get triage queue filtered by tier, SLA status, and assignment",
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_triage_queue(
    session: DbSession,
    user: CurrentUser,
    tier: str | None = Query(None, description="Filter by tier (RED, AMBER, GREEN, BLUE)"),
    sla_status: str | None = Query(None, description="Filter: breached, at_risk, ok"),
    case_status: str | None = Query(None, description="Filter by case status"),
    assigned_to_me: bool = Query(False, description="Only my assigned cases"),
    needs_review: bool = Query(False, description="Only cases needing clinician review"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
) -> QueueResponse:
    """Get the triage queue with filtering and SLA tracking.

    The queue is ordered by:
    1. SLA breaches first
    2. Then by tier priority (RED > AMBER > GREEN > BLUE)
    3. Then by time remaining to SLA deadline

    Args:
        session: Database session
        user: Current authenticated user
        tier: Optional tier filter
        sla_status: Optional SLA status filter
        case_status: Optional case status filter
        assigned_to_me: Only show cases assigned to current user
        needs_review: Only show cases requiring clinician review
        limit: Maximum results
        offset: Pagination offset

    Returns:
        Queue response with items and counts
    """
    now = datetime.now(timezone.utc)

    # Build base query
    query = select(TriageCase).where(TriageCase.deleted_at.is_(None))

    # Apply filters
    if tier:
        tier_upper = tier.upper()
        if tier_upper in ("RED", "AMBER", "GREEN", "BLUE"):
            query = query.where(TriageCase.tier == tier_upper.lower())

    if case_status:
        try:
            status_enum = TriageCaseStatus(case_status.lower())
            query = query.where(TriageCase.status == status_enum)
        except ValueError:
            pass

    if assigned_to_me:
        query = query.where(TriageCase.assigned_clinician_id == user.id)

    if needs_review:
        query = query.where(TriageCase.clinician_review_required == True)

    if sla_status:
        if sla_status == "breached":
            query = query.where(TriageCase.sla_breached == True)
        elif sla_status == "at_risk":
            # Within 15 minutes of deadline
            from datetime import timedelta
            at_risk_threshold = now + timedelta(minutes=15)
            query = query.where(
                and_(
                    TriageCase.sla_breached == False,
                    TriageCase.sla_deadline.isnot(None),
                    TriageCase.sla_deadline <= at_risk_threshold,
                )
            )
        elif sla_status == "ok":
            from datetime import timedelta
            at_risk_threshold = now + timedelta(minutes=15)
            query = query.where(
                or_(
                    TriageCase.sla_deadline.is_(None),
                    and_(
                        TriageCase.sla_breached == False,
                        TriageCase.sla_deadline > at_risk_threshold,
                    ),
                )
            )

    # Order by priority: breaches first, then tier, then SLA deadline
    tier_priority = func.case(
        (TriageCase.tier == "red", 1),
        (TriageCase.tier == "amber", 2),
        (TriageCase.tier == "green", 3),
        (TriageCase.tier == "blue", 4),
        else_=5,
    )

    query = query.order_by(
        TriageCase.sla_breached.desc(),
        tier_priority,
        TriageCase.sla_deadline.asc().nulls_last(),
        TriageCase.created_at.asc(),
    )

    # Get total count before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    query = query.offset(offset).limit(limit)

    # Execute main query
    result = await session.execute(query)
    cases = result.scalars().all()

    # Build queue items with SLA calculations
    items = []
    for case in cases:
        minutes_remaining = None
        if case.sla_deadline and not case.sla_breached:
            delta = case.sla_deadline - now
            minutes_remaining = max(0, int(delta.total_seconds() / 60))

        items.append(
            QueueItem(
                id=case.id,
                patient_id=case.patient_id,
                tier=case.tier.value if case.tier else None,
                pathway=case.pathway,
                status=case.status.value,
                sla_deadline=case.sla_deadline,
                sla_breached=case.sla_breached,
                sla_minutes_remaining=minutes_remaining,
                clinician_review_required=case.clinician_review_required,
                assigned_clinician_id=case.assigned_clinician_id,
                created_at=case.created_at,
                triaged_at=case.triaged_at,
            )
        )

    # Get counts by tier (unfiltered)
    counts_query = (
        select(TriageCase.tier, func.count().label("count"))
        .where(TriageCase.deleted_at.is_(None))
        .group_by(TriageCase.tier)
    )
    counts_result = await session.execute(counts_query)
    tier_counts = {row.tier: row.count for row in counts_result}

    # Get breach count
    breach_query = select(func.count()).where(
        and_(
            TriageCase.deleted_at.is_(None),
            TriageCase.sla_breached == True,
        )
    )
    breach_result = await session.execute(breach_query)
    breached_count = breach_result.scalar() or 0

    return QueueResponse(
        items=items,
        total=total,
        red_count=tier_counts.get(TriageTier.RED, 0),
        amber_count=tier_counts.get(TriageTier.AMBER, 0),
        green_count=tier_counts.get(TriageTier.GREEN, 0),
        blue_count=tier_counts.get(TriageTier.BLUE, 0),
        breached_count=breached_count,
    )


@router.get(
    "/{case_id}/summary",
    response_model=CaseSummary,
    status_code=status.HTTP_200_OK,
    summary="Get case summary",
    description="Get full case summary for clinician review",
    dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))],
)
async def get_case_summary(
    case_id: str,
    session: DbSession,
    user: CurrentUser,
) -> CaseSummary:
    """Get comprehensive case summary for clinician review.

    Includes:
    - Triage case details
    - SLA tracking with time remaining
    - Disposition draft (if exists)
    - Disposition final (if exists)
    - Risk flags

    Args:
        case_id: UUID of the triage case
        session: Database session
        user: Current authenticated user

    Returns:
        Full case summary

    Raises:
        HTTPException: If case not found
    """
    # Get the triage case
    result = await session.execute(
        select(TriageCase).where(TriageCase.id == case_id)
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Triage case not found",
        )

    # Get disposition draft (latest)
    draft_result = await session.execute(
        select(DispositionDraft)
        .where(DispositionDraft.triage_case_id == case_id)
        .order_by(DispositionDraft.created_at.desc())
        .limit(1)
    )
    draft = draft_result.scalar_one_or_none()

    # Get disposition final
    final_result = await session.execute(
        select(DispositionFinal).where(DispositionFinal.triage_case_id == case_id)
    )
    final = final_result.scalar_one_or_none()

    # Get risk flags
    flags_result = await session.execute(
        select(RiskFlag)
        .where(RiskFlag.triage_case_id == case_id)
        .order_by(RiskFlag.created_at.desc())
    )
    risk_flags = [
        {
            "id": f.id,
            "flag_type": f.flag_type.value,
            "severity": f.severity.value,
            "explanation": f.explanation,
            "reviewed": f.reviewed,
            "rule_id": f.rule_id,
        }
        for f in flags_result.scalars().all()
    ]

    # Calculate SLA minutes remaining
    now = datetime.now(timezone.utc)
    minutes_remaining = None
    if case.sla_deadline and not case.sla_breached:
        delta = case.sla_deadline - now
        minutes_remaining = max(0, int(delta.total_seconds() / 60))

    # Audit the summary view
    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="triage_case_summary_viewed",
        action_category="triage",
        entity_type="triage_case",
        entity_id=case.id,
        metadata={"tier": case.tier.value if case.tier else None},
    )

    return CaseSummary(
        id=case.id,
        patient_id=case.patient_id,
        status=case.status.value,
        tier=case.tier.value if case.tier else None,
        pathway=case.pathway,
        clinician_review_required=case.clinician_review_required,
        self_book_allowed=case.self_book_allowed,
        ruleset_version=case.ruleset_version,
        ruleset_hash=case.ruleset_hash,
        tier_explanation=case.tier_explanation,
        triaged_at=case.triaged_at,
        sla_deadline=case.sla_deadline,
        sla_target_minutes=case.sla_target_minutes,
        sla_breached=case.sla_breached,
        sla_minutes_remaining=minutes_remaining,
        assigned_clinician_id=case.assigned_clinician_id,
        clinical_notes=case.clinical_notes,
        reviewed_at=case.reviewed_at,
        reviewed_by=case.reviewed_by,
        disposition_draft=DispositionDraftRead.model_validate(draft) if draft else None,
        disposition_final=DispositionFinalRead.model_validate(final) if final else None,
        risk_flags=risk_flags,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.post(
    "/{case_id}/disposition",
    response_model=DispositionFinalRead,
    status_code=status.HTTP_201_CREATED,
    summary="Finalize disposition",
    description="Confirm or override the triage disposition. Override requires rationale.",
    dependencies=[Depends(require_permissions(Permission.DISPOSITION_CONFIRM))],
)
async def finalize_disposition(
    case_id: str,
    body: DispositionFinalize,
    session: DbSession,
    user: CurrentUser,
) -> DispositionFinalRead:
    """Finalize the triage disposition.

    A clinician can either:
    - CONFIRM: Accept the rules engine draft as-is
    - OVERRIDE: Change tier/pathway with MANDATORY rationale (min 20 chars)

    Override requires DISPOSITION_OVERRIDE permission.

    Args:
        case_id: UUID of the triage case
        body: Finalization request (confirm or override)
        session: Database session
        user: Current authenticated user

    Returns:
        The final disposition record

    Raises:
        HTTPException: If case not found, already finalized, or permission denied
    """
    # Get the triage case
    result = await session.execute(
        select(TriageCase).where(TriageCase.id == case_id)
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Triage case not found",
        )

    # Check if already finalized
    existing_final = await session.execute(
        select(DispositionFinal).where(DispositionFinal.triage_case_id == case_id)
    )
    if existing_final.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Disposition already finalized. Create new triage case to re-evaluate.",
        )

    # Get the latest draft
    draft_result = await session.execute(
        select(DispositionDraft)
        .where(DispositionDraft.triage_case_id == case_id)
        .order_by(DispositionDraft.created_at.desc())
        .limit(1)
    )
    draft = draft_result.scalar_one_or_none()

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No disposition draft found. Run triage evaluation first.",
        )

    now = datetime.now(timezone.utc)
    is_override = body.action == "override"

    # For override, check permission
    if is_override:
        from app.services.rbac import RBACService
        if not RBACService.has_permission(user.role, Permission.DISPOSITION_OVERRIDE):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: disposition:override required for tier/pathway changes",
            )

    # Determine final values
    if is_override:
        final_tier = body.override.tier
        final_pathway = body.override.pathway
        rationale = body.override.rationale
        clinical_notes = body.override.clinical_notes or body.clinical_notes
        original_tier = draft.tier
        original_pathway = draft.pathway
    else:
        final_tier = draft.tier
        final_pathway = draft.pathway
        rationale = None
        clinical_notes = body.clinical_notes
        original_tier = None
        original_pathway = None

    # Determine self_book_allowed based on final tier
    self_book_allowed = final_tier.upper() not in ("RED", "AMBER")

    # Create final disposition
    final = DispositionFinal(
        triage_case_id=case_id,
        draft_id=draft.id,
        tier=final_tier,
        pathway=final_pathway,
        self_book_allowed=self_book_allowed,
        is_override=is_override,
        original_tier=original_tier,
        original_pathway=original_pathway,
        rationale=rationale,
        clinician_id=user.id,
        finalized_at=now,
        clinical_notes=clinical_notes,
    )

    session.add(final)

    # Mark draft as applied
    draft.is_applied = True
    draft.approved_by = user.id

    # Update triage case
    case.status = TriageCaseStatus.TRIAGED
    case.tier = TriageTier(final_tier.lower())
    case.pathway = final_pathway
    case.self_book_allowed = self_book_allowed
    case.reviewed_at = now
    case.reviewed_by = user.id
    if clinical_notes:
        case.clinical_notes = clinical_notes

    await session.commit()
    await session.refresh(final)

    # Audit the finalization
    audit_action = "disposition_overridden" if is_override else "disposition_confirmed"
    audit_metadata = {
        "final_tier": final_tier,
        "final_pathway": final_pathway,
        "is_override": is_override,
    }

    if is_override:
        audit_metadata.update({
            "original_tier": original_tier,
            "original_pathway": original_pathway,
            "rationale": rationale,
            "rationale_length": len(rationale) if rationale else 0,
        })

    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action=audit_action,
        action_category="disposition",
        entity_type="disposition_final",
        entity_id=final.id,
        description=f"Clinician {user.email} {'overrode' if is_override else 'confirmed'} "
                    f"disposition for case {case_id[:8]}... to tier={final_tier}",
        metadata=audit_metadata,
    )

    # Also audit on the triage case for complete history
    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="triage_case_disposition_finalized",
        action_category="triage",
        entity_type="triage_case",
        entity_id=case_id,
        metadata={
            "disposition_id": final.id,
            "is_override": is_override,
            "tier": final_tier,
        },
    )

    return DispositionFinalRead.model_validate(final)
