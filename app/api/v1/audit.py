"""Audit event endpoints.

IMPORTANT: This module intentionally provides READ-ONLY access to audit events.
No endpoints exist for creating, updating, or deleting audit events through the API.
Audit events are created internally via the write_audit_event() service function.
"""

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, DbSession, require_permissions
from app.schemas.audit_event import AuditEventFilter, AuditEventRead
from app.services.audit import AuditService
from app.services.rbac import Permission

router = APIRouter()


@router.get(
    "/events",
    response_model=list[AuditEventRead],
    status_code=status.HTTP_200_OK,
    summary="List audit events",
    description="Query audit events with optional filters (append-only, no modification endpoints)",
    dependencies=[Depends(require_permissions(Permission.AUDIT_READ))],
)
async def list_audit_events(
    session: DbSession,
    user: CurrentUser,
    entity_id: str | None = None,
    entity_type: str | None = None,
    actor_id: str | None = None,
    action: str | None = None,
    action_category: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditEventRead]:
    """Query audit events with optional filters.

    This is a read-only endpoint. Audit events cannot be created,
    modified, or deleted through the API - they are append-only
    records created by internal service calls.

    Args:
        session: Database session
        user: Current authenticated user
        entity_id: Filter by entity ID
        entity_type: Filter by entity type
        actor_id: Filter by actor ID
        action: Filter by action
        action_category: Filter by action category
        limit: Maximum results (default 100, max 500)
        offset: Results to skip

    Returns:
        List of audit events matching filters
    """
    filters = AuditEventFilter(
        entity_id=entity_id,
        entity_type=entity_type,
        actor_id=actor_id,
        action=action,
        action_category=action_category,
        limit=min(limit, 500),  # Cap at 500
        offset=offset,
    )

    audit_service = AuditService(session)
    events = await audit_service.get_events(filters)

    return [AuditEventRead.model_validate(e) for e in events]


@router.get(
    "/events/{entity_type}/{entity_id}",
    response_model=list[AuditEventRead],
    status_code=status.HTTP_200_OK,
    summary="Get entity audit history",
    description="Get complete audit history for a specific entity",
    dependencies=[Depends(require_permissions(Permission.AUDIT_READ))],
)
async def get_entity_history(
    entity_type: str,
    entity_id: str,
    session: DbSession,
    user: CurrentUser,
    limit: int = 100,
) -> list[AuditEventRead]:
    """Get audit history for a specific entity.

    Args:
        entity_type: Type of entity (e.g., "triage_case", "patient")
        entity_id: UUID of the entity
        session: Database session
        user: Current authenticated user
        limit: Maximum events to return

    Returns:
        List of audit events for the entity
    """
    audit_service = AuditService(session)
    events = await audit_service.get_entity_history(
        entity_type=entity_type,
        entity_id=entity_id,
        limit=min(limit, 500),
    )

    return [AuditEventRead.model_validate(e) for e in events]


# NOTE: No POST, PUT, PATCH, or DELETE endpoints are provided.
# This is intentional - audit events are append-only and created
# only through internal service calls, never through the API.
