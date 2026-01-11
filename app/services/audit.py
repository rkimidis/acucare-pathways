"""Audit event service for append-only audit logging."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import audit_logger
from app.models.audit_event import ActorType, AuditEvent
from app.schemas.audit_event import AuditEventCreate, AuditEventFilter


async def write_audit_event(
    session: AsyncSession,
    actor_type: ActorType,
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None,
    metadata: dict[str, Any] | None = None,
    actor_email: str | None = None,
    action_category: str | None = None,
    description: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> AuditEvent:
    """Write an audit event to the database.

    This is the primary function for recording audit events.
    Events are append-only and cannot be modified or deleted.

    Args:
        session: Database session
        actor_type: Type of actor (system, staff, patient)
        actor_id: ID of the actor (user ID or patient ID)
        action: Action performed (e.g., "login", "create_case", "update_tier")
        entity_type: Type of entity affected (e.g., "user", "triage_case")
        entity_id: ID of the affected entity
        metadata: Additional context as JSON
        actor_email: Email of the actor (for easier querying)
        action_category: Category of action (auth, triage, clinical, admin)
        description: Human-readable description
        ip_address: Client IP address
        user_agent: Client user agent string
        request_id: Request correlation ID

    Returns:
        Created AuditEvent instance
    """
    event = AuditEvent(
        actor_type=actor_type,
        actor_id=actor_id,
        actor_email=actor_email,
        action=action,
        action_category=action_category,
        entity_type=entity_type,
        entity_id=entity_id,
        event_metadata=metadata,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )

    session.add(event)
    await session.commit()
    await session.refresh(event)

    # Also log to structured logger
    audit_logger.log(
        action=action,
        actor_type=actor_type.value,
        actor_id=actor_id or "system",
        entity_type=entity_type,
        entity_id=entity_id or "none",
        metadata=metadata,
    )

    return event


class AuditService:
    """Service for querying audit events.

    Note: This service only provides read operations.
    Audit events are created via write_audit_event() function.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_events(
        self,
        filters: AuditEventFilter,
    ) -> list[AuditEvent]:
        """Query audit events with optional filters.

        Args:
            filters: Filter parameters

        Returns:
            List of matching audit events
        """
        query = select(AuditEvent).order_by(AuditEvent.created_at.desc())

        if filters.entity_id:
            query = query.where(AuditEvent.entity_id == filters.entity_id)
        if filters.entity_type:
            query = query.where(AuditEvent.entity_type == filters.entity_type)
        if filters.actor_id:
            query = query.where(AuditEvent.actor_id == filters.actor_id)
        if filters.action:
            query = query.where(AuditEvent.action == filters.action)
        if filters.action_category:
            query = query.where(AuditEvent.action_category == filters.action_category)

        query = query.offset(filters.offset).limit(filters.limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_event_by_id(self, event_id: str) -> AuditEvent | None:
        """Get a single audit event by ID.

        Args:
            event_id: UUID of the event

        Returns:
            AuditEvent or None if not found
        """
        result = await self.session.execute(
            select(AuditEvent).where(AuditEvent.id == event_id)
        )
        return result.scalar_one_or_none()

    async def get_entity_history(
        self,
        entity_type: str,
        entity_id: str,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Get audit history for a specific entity.

        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            limit: Maximum events to return

        Returns:
            List of audit events for the entity
        """
        result = await self.session.execute(
            select(AuditEvent)
            .where(AuditEvent.entity_type == entity_type)
            .where(AuditEvent.entity_id == entity_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
