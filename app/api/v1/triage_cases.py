"""Triage case endpoints."""

from datetime import datetime, timezone
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, case as sql_case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession, require_permissions
from app.models.audit_event import ActorType, AuditEvent
from app.models.disposition import DispositionDraft, DispositionFinal, RiskFlag
from app.models.governance import DutyRoster
from app.models.triage_case import TriageCase, TriageCaseStatus, TriageTier
from app.models.user import User, UserRole
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


class ReassignRequest(BaseModel):
    """Request body for reassignment."""

    user_id: str = Field(..., description="New assignee user id")
    reason: str = Field(..., min_length=3, max_length=500)


def build_patient_ref(patient_id: str) -> str:
    """Generate a stable patient reference code (e.g., PT-04291)."""
    hash_value = int(hashlib.sha1(patient_id.encode("utf-8")).hexdigest(), 16) % 100000
    return f"PT-{hash_value:05d}"


def get_assigned_user_id(case: TriageCase) -> str | None:
    """Return the current assigned user id, falling back to legacy field."""
    return case.assigned_to_user_id or case.assigned_clinician_id


def is_clinician_role(user: User) -> bool:
    """Return True if user has a clinician-capable role."""
    return user.role in (UserRole.CLINICIAN, UserRole.CLINICAL_LEAD, UserRole.ADMIN)


async def get_current_duty_roster(
    session: AsyncSession,
    now: datetime,
) -> DutyRoster | None:
    """Return the current duty roster entry if active."""
    result = await session.execute(
        select(DutyRoster)
        .where(DutyRoster.starts_at <= now)
        .where(DutyRoster.ends_at >= now)
        .order_by(DutyRoster.starts_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def is_duty_user(user: User, roster: DutyRoster | None) -> bool:
    """Check if the user is on duty (primary or backup)."""
    if not roster:
        return False
    return user.id in {roster.primary_user_id, roster.backup_user_id}


async def get_user_display_name(session: AsyncSession, user_id: str) -> str | None:
    """Return a user's display name for messaging."""
    result = await session.execute(
        select(User.first_name, User.last_name).where(User.id == user_id)
    )
    row = result.first()
    if not row:
        return None
    first_name, last_name = row
    full_name = f"{first_name or ''} {last_name or ''}".strip()
    return full_name or user_id


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
    assigned: str | None = Query(None, description="Assignment filter: me, unassigned, others, any"),
    assigned_to_me: bool = Query(False, description="Deprecated: use assigned=me"),
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
        assigned: Assignment filter
        assigned_to_me: Deprecated flag for current user assignment
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
    if not case_status:
        query = query.where(TriageCase.reviewed_at.is_(None))
        query = query.where(
            TriageCase.status.in_([
                TriageCaseStatus.TRIAGED,
                TriageCaseStatus.IN_REVIEW,
            ])
        )
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

    assignment_filter = assigned
    if not assignment_filter and assigned_to_me:
        assignment_filter = "me"

    assigned_col = func.coalesce(
        TriageCase.assigned_to_user_id,
        TriageCase.assigned_clinician_id,
    )

    if assignment_filter == "me":
        query = query.where(assigned_col == user.id)
    elif assignment_filter == "unassigned":
        query = query.where(assigned_col.is_(None))
    elif assignment_filter == "others":
        query = query.where(assigned_col.isnot(None)).where(assigned_col != user.id)
    elif assignment_filter == "any":
        pass

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
    tier_priority = sql_case(
        (TriageCase.tier == "red", 1),
        (TriageCase.tier == "amber", 2),
        (TriageCase.tier == "green", 3),
        (TriageCase.tier == "blue", 4),
        else_=5,
    )

    age_sort = func.coalesce(TriageCase.triaged_at, TriageCase.created_at)

    query = query.order_by(
        tier_priority,
        TriageCase.sla_breached.desc(),
        TriageCase.sla_deadline.asc().nulls_last(),
        age_sort.asc(),
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

    case_ids = [case.id for case in cases]
    draft_map: dict[str, DispositionDraft] = {}
    last_action_map: dict[str, datetime] = {}
    clinician_map: dict[str, dict[str, str]] = {}

    if case_ids:
        drafts_result = await session.execute(
            select(DispositionDraft)
            .where(DispositionDraft.triage_case_id.in_(case_ids))
            .order_by(DispositionDraft.created_at.desc())
        )
        for draft in drafts_result.scalars().all():
            if draft.triage_case_id not in draft_map:
                draft_map[draft.triage_case_id] = draft

        events_result = await session.execute(
            select(
                AuditEvent.entity_id,
                func.max(AuditEvent.created_at).label("last_action"),
            )
            .where(AuditEvent.entity_type == "triage_case")
            .where(AuditEvent.actor_type == ActorType.STAFF)
            .where(AuditEvent.entity_id.in_(case_ids))
            .group_by(AuditEvent.entity_id)
        )
        last_action_map = {
            row.entity_id: row.last_action
            for row in events_result.all()
            if row.entity_id and row.last_action
        }

        assigned_ids = {
            get_assigned_user_id(case)
            for case in cases
            if get_assigned_user_id(case)
        }
        if assigned_ids:
            clinicians_result = await session.execute(
                select(User.id, User.first_name, User.last_name)
                .where(User.id.in_(assigned_ids))
            )
            for row in clinicians_result.all():
                initials = ""
                if row.first_name:
                    initials += row.first_name[:1].upper()
                if row.last_name:
                    initials += row.last_name[:1].upper()
                clinician_map[row.id] = {
                    "initials": initials or "--",
                    "name": f"{row.first_name} {row.last_name}".strip(),
                }

    # Build queue items with SLA calculations
    items = []
    for case in cases:
        minutes_remaining = None
        if case.sla_deadline and not case.sla_breached:
            delta = case.sla_deadline - now
            minutes_remaining = max(0, int(delta.total_seconds() / 60))

        draft = draft_map.get(case.id)
        rules_fired = draft.rules_fired if draft else []
        ruleset_version = draft.ruleset_version if draft else case.ruleset_version

        last_action_at = last_action_map.get(case.id) or case.updated_at or case.created_at

        age_base = case.triaged_at or case.created_at
        age_minutes = None
        if age_base:
            age_minutes = int((now - age_base).total_seconds() / 60)

        assigned_user_id = get_assigned_user_id(case)
        assigned_display = clinician_map.get(assigned_user_id or "")

        items.append(
            QueueItem(
                id=case.id,
                patient_id=case.patient_id,
                patient_ref=build_patient_ref(case.patient_id),
                tier=case.tier.value if hasattr(case.tier, "value") else case.tier,
                pathway=case.pathway,
                status=case.status.value if hasattr(case.status, "value") else case.status,
                sla_deadline=case.sla_deadline,
                sla_breached=case.sla_breached,
                sla_minutes_remaining=minutes_remaining,
                clinician_review_required=case.clinician_review_required,
                assigned_to_user_id=assigned_user_id,
                assigned_to_user_initials=assigned_display["initials"] if assigned_display else None,
                assigned_to_user_name=assigned_display["name"] if assigned_display else None,
                assigned_to_me=assigned_user_id == user.id if assigned_user_id else False,
                assigned_at=case.assigned_at,
                rules_fired=rules_fired,
                ruleset_version=ruleset_version,
                last_staff_action_at=last_action_at,
                age_minutes=age_minutes,
                created_at=case.created_at,
                triaged_at=case.triaged_at,
            )
        )

    # Get counts by tier (only cases in the queue - TRIAGED/IN_REVIEW and not reviewed)
    counts_query = (
        select(TriageCase.tier, func.count().label("count"))
        .where(TriageCase.deleted_at.is_(None))
        .where(TriageCase.reviewed_at.is_(None))
        .where(
            TriageCase.status.in_([
                TriageCaseStatus.TRIAGED,
                TriageCaseStatus.IN_REVIEW,
            ])
        )
        .group_by(TriageCase.tier)
    )
    counts_result = await session.execute(counts_query)
    tier_counts = {row.tier: row.count for row in counts_result}

    # Get breach count (only for cases in the queue)
    breach_query = select(func.count()).where(
        and_(
            TriageCase.deleted_at.is_(None),
            TriageCase.reviewed_at.is_(None),
            TriageCase.status.in_([
                TriageCaseStatus.TRIAGED,
                TriageCaseStatus.IN_REVIEW,
            ]),
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

    if body.assigned_to_user_id is not None:
        changes["assigned_to_user_id"] = {
            "from": case.assigned_to_user_id,
            "to": body.assigned_to_user_id,
        }
        case.assigned_to_user_id = body.assigned_to_user_id
        case.assigned_clinician_id = body.assigned_to_user_id
        if body.assigned_to_user_id:
            case.assigned_at = body.assigned_at or datetime.now(timezone.utc)
        else:
            case.assigned_at = None
    elif body.assigned_at is not None:
        case.assigned_at = body.assigned_at

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


@router.post(
    "/{case_id}/claim",
    response_model=TriageCaseRead,
    status_code=status.HTTP_200_OK,
    summary="Claim triage case",
    description="Assign the triage case to the current clinician",
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def claim_triage_case(
    case_id: str,
    session: DbSession,
    user: CurrentUser,
) -> TriageCaseRead:
    """Claim a triage case for the current clinician."""
    if not is_clinician_role(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinicians can claim cases",
        )

    result = await session.execute(
        select(TriageCase).where(TriageCase.id == case_id)
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Triage case not found",
        )

    now = datetime.now(timezone.utc)
    assigned_user_id = get_assigned_user_id(case)
    roster = await get_current_duty_roster(session, now)
    override_allowed = is_duty_user(user, roster) or user.role in (
        UserRole.ADMIN,
        UserRole.CLINICAL_LEAD,
    )

    if assigned_user_id == user.id:
        return TriageCaseRead.model_validate(case)

    if assigned_user_id and assigned_user_id != user.id and not override_allowed:
        assigned_name = await get_user_display_name(session, assigned_user_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Case already assigned to {assigned_name or 'another clinician'}",
        )

    if assigned_user_id is None:
        claim_stmt = (
            update(TriageCase)
            .where(TriageCase.id == case_id)
            .where(TriageCase.assigned_to_user_id.is_(None))
            .values(
                assigned_to_user_id=user.id,
                assigned_clinician_id=user.id,
                assigned_at=now,
            )
        )
        claim_result = await session.execute(claim_stmt)
        if claim_result.rowcount == 0:
            await session.rollback()
            latest = await session.execute(
                select(TriageCase).where(TriageCase.id == case_id)
            )
            case = latest.scalar_one_or_none()
            assigned_user_id = get_assigned_user_id(case) if case else None
            assigned_name = (
                await get_user_display_name(session, assigned_user_id)
                if assigned_user_id
                else None
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Case already assigned to {assigned_name or 'another clinician'}",
            )
        await session.commit()
    else:
        case.assigned_to_user_id = user.id
        case.assigned_clinician_id = user.id
        case.assigned_at = now
        await session.commit()

    refreshed = await session.execute(select(TriageCase).where(TriageCase.id == case_id))
    case = refreshed.scalar_one()

    audit_action = "case_reassigned" if assigned_user_id else "case_claimed"
    audit_metadata = {
        "assigned_to_user_id": user.id,
        "previous_assignee_id": assigned_user_id,
    }
    if assigned_user_id:
        audit_metadata["reason"] = "Duty override claim"

    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action=audit_action,
        action_category="triage",
        entity_type="triage_case",
        entity_id=case.id,
        metadata=audit_metadata,
    )

    return TriageCaseRead.model_validate(case)


@router.post(
    "/{case_id}/unassign",
    response_model=TriageCaseRead,
    status_code=status.HTTP_200_OK,
    summary="Unassign triage case",
    description="Remove assignment from a triage case",
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def unassign_triage_case(
    case_id: str,
    session: DbSession,
    user: CurrentUser,
) -> TriageCaseRead:
    """Unassign a triage case."""
    result = await session.execute(
        select(TriageCase).where(TriageCase.id == case_id)
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Triage case not found",
        )

    assigned_user_id = get_assigned_user_id(case)
    if not assigned_user_id:
        return TriageCaseRead.model_validate(case)

    now = datetime.now(timezone.utc)
    roster = await get_current_duty_roster(session, now)
    override_allowed = is_duty_user(user, roster) or user.role in (
        UserRole.ADMIN,
        UserRole.CLINICAL_LEAD,
    )

    if assigned_user_id != user.id and not override_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assignee or duty clinician can unassign this case",
        )

    case.assigned_to_user_id = None
    case.assigned_clinician_id = None
    case.assigned_at = None
    await session.commit()
    await session.refresh(case)

    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="case_unassigned",
        action_category="triage",
        entity_type="triage_case",
        entity_id=case.id,
        metadata={
            "previous_assignee_id": assigned_user_id,
            "reason": "Self-unassigned" if assigned_user_id == user.id else "Duty unassigned",
        },
    )

    return TriageCaseRead.model_validate(case)


@router.post(
    "/{case_id}/reassign",
    response_model=TriageCaseRead,
    status_code=status.HTTP_200_OK,
    summary="Reassign triage case",
    description="Reassign the triage case to another clinician",
    dependencies=[Depends(require_permissions(Permission.TRIAGE_WRITE))],
)
async def reassign_triage_case(
    case_id: str,
    body: ReassignRequest,
    session: DbSession,
    user: CurrentUser,
) -> TriageCaseRead:
    """Reassign a triage case to another clinician."""
    result = await session.execute(
        select(TriageCase).where(TriageCase.id == case_id)
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Triage case not found",
        )

    now = datetime.now(timezone.utc)
    roster = await get_current_duty_roster(session, now)
    override_allowed = is_duty_user(user, roster) or user.role in (
        UserRole.ADMIN,
        UserRole.CLINICAL_LEAD,
    )

    if not override_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only duty clinicians or admins can reassign cases",
        )

    target_result = await session.execute(
        select(User).where(User.id == body.user_id)
    )
    target_user = target_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found",
        )

    previous_assignee = get_assigned_user_id(case)
    case.assigned_to_user_id = body.user_id
    case.assigned_clinician_id = body.user_id
    case.assigned_at = now
    await session.commit()
    await session.refresh(case)

    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="case_reassigned",
        action_category="triage",
        entity_type="triage_case",
        entity_id=case.id,
        metadata={
            "previous_assignee_id": previous_assignee,
            "new_assignee_id": body.user_id,
            "reason": body.reason,
        },
    )

    return TriageCaseRead.model_validate(case)


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
        metadata={"tier": case.tier.value if hasattr(case.tier, "value") else case.tier},
    )

    return CaseSummary(
        id=case.id,
        patient_id=case.patient_id,
        status=case.status.value if hasattr(case.status, "value") else case.status,
        tier=case.tier.value if hasattr(case.tier, "value") else case.tier,
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
        assigned_to_user_id=get_assigned_user_id(case),
        assigned_at=case.assigned_at,
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
