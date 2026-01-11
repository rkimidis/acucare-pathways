"""Tests for append-only audit event functionality."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import ActorType, AuditEvent
from app.models.user import User
from app.services.audit import AuditService, write_audit_event


@pytest.mark.asyncio
async def test_write_audit_event(async_session: AsyncSession) -> None:
    """Test writing an audit event."""
    event = await write_audit_event(
        session=async_session,
        actor_type=ActorType.SYSTEM,
        actor_id=None,
        action="test_action",
        entity_type="test_entity",
        entity_id="123",
        metadata={"key": "value"},
        description="Test audit event",
    )

    assert event.id is not None
    assert event.actor_type == ActorType.SYSTEM
    assert event.action == "test_action"
    assert event.entity_type == "test_entity"
    assert event.entity_id == "123"
    assert event.event_metadata == {"key": "value"}
    assert event.created_at is not None


@pytest.mark.asyncio
async def test_audit_events_are_persisted(async_session: AsyncSession) -> None:
    """Test that audit events are properly persisted to database."""
    # Write an event
    await write_audit_event(
        session=async_session,
        actor_type=ActorType.STAFF,
        actor_id="user-123",
        action="login_success",
        entity_type="user",
        entity_id="user-123",
    )

    # Query it back
    service = AuditService(async_session)
    from app.schemas.audit_event import AuditEventFilter

    events = await service.get_events(AuditEventFilter(action="login_success"))

    assert len(events) == 1
    assert events[0].action == "login_success"


@pytest.mark.asyncio
async def test_audit_service_filters(async_session: AsyncSession) -> None:
    """Test audit service filtering capabilities."""
    # Create multiple events
    await write_audit_event(
        session=async_session,
        actor_type=ActorType.STAFF,
        actor_id="user-1",
        action="create",
        entity_type="triage_case",
        entity_id="case-1",
    )
    await write_audit_event(
        session=async_session,
        actor_type=ActorType.PATIENT,
        actor_id="patient-1",
        action="view",
        entity_type="triage_case",
        entity_id="case-1",
    )
    await write_audit_event(
        session=async_session,
        actor_type=ActorType.SYSTEM,
        actor_id=None,
        action="process",
        entity_type="queue_job",
        entity_id="job-1",
    )

    service = AuditService(async_session)
    from app.schemas.audit_event import AuditEventFilter

    # Filter by entity_id
    events = await service.get_events(AuditEventFilter(entity_id="case-1"))
    assert len(events) == 2

    # Filter by entity_type
    events = await service.get_events(AuditEventFilter(entity_type="queue_job"))
    assert len(events) == 1

    # Filter by action
    events = await service.get_events(AuditEventFilter(action="create"))
    assert len(events) == 1


def test_audit_endpoint_no_post_method(client: TestClient) -> None:
    """Test that audit endpoint does not allow POST (append-only enforcement)."""
    # Attempt to POST to audit events endpoint
    response = client.post(
        "/api/v1/audit/events",
        json={
            "actor_type": "system",
            "action": "test",
            "entity_type": "test",
        },
    )

    # Should return 405 Method Not Allowed (endpoint doesn't exist for POST)
    assert response.status_code == 405


def test_audit_endpoint_no_put_method(client: TestClient) -> None:
    """Test that audit endpoint does not allow PUT (append-only enforcement)."""
    response = client.put(
        "/api/v1/audit/events/123",
        json={"action": "modified"},
    )

    # Should return 405 Method Not Allowed
    assert response.status_code == 405


def test_audit_endpoint_no_delete_method(client: TestClient) -> None:
    """Test that audit endpoint does not allow DELETE (append-only enforcement)."""
    response = client.delete("/api/v1/audit/events/123")

    # Should return 405 Method Not Allowed
    assert response.status_code == 405


def test_audit_endpoint_no_patch_method(client: TestClient) -> None:
    """Test that audit endpoint does not allow PATCH (append-only enforcement)."""
    response = client.patch(
        "/api/v1/audit/events/123",
        json={"action": "modified"},
    )

    # Should return 405 Method Not Allowed
    assert response.status_code == 405
