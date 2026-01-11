"""Tests for triage case creation emitting audit events."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditEvent
from app.models.patient import Patient
from app.models.triage_case import TriageCase
from app.models.user import User


@pytest.mark.asyncio
async def test_creating_triage_case_emits_audit_event(
    client: TestClient,
    async_session: AsyncSession,
    admin_user: User,
    test_patient: Patient,
    admin_auth_headers: dict[str, str],
) -> None:
    """Test that creating a triage case creates an audit event."""
    # Create a triage case via API
    response = client.post(
        "/api/v1/triage-cases",
        json={"patient_id": test_patient.id},
        headers=admin_auth_headers,
    )

    assert response.status_code == 201
    case_data = response.json()

    # Verify triage case was created
    result = await async_session.execute(
        select(TriageCase).where(TriageCase.id == case_data["id"])
    )
    triage_case = result.scalar_one_or_none()
    assert triage_case is not None

    # Verify audit event was created
    result = await async_session.execute(
        select(AuditEvent).where(
            AuditEvent.entity_type == "triage_case",
            AuditEvent.entity_id == case_data["id"],
        )
    )
    audit_event = result.scalar_one_or_none()

    assert audit_event is not None
    assert audit_event.action == "triage_case_created"
    assert audit_event.actor_id == admin_user.id
    assert audit_event.event_metadata is not None
    assert audit_event.event_metadata.get("patient_id") == test_patient.id


@pytest.mark.asyncio
async def test_updating_triage_case_emits_audit_event(
    client: TestClient,
    async_session: AsyncSession,
    admin_user: User,
    test_triage_case: TriageCase,
    admin_auth_headers: dict[str, str],
) -> None:
    """Test that updating a triage case creates an audit event."""
    # Update the triage case
    response = client.patch(
        f"/api/v1/triage-cases/{test_triage_case.id}",
        json={"status": "in_review", "clinical_notes": "Initial review notes"},
        headers=admin_auth_headers,
    )

    assert response.status_code == 200

    # Verify audit event was created
    result = await async_session.execute(
        select(AuditEvent)
        .where(
            AuditEvent.entity_type == "triage_case",
            AuditEvent.entity_id == test_triage_case.id,
            AuditEvent.action == "triage_case_updated",
        )
    )
    audit_event = result.scalar_one_or_none()

    assert audit_event is not None
    assert audit_event.actor_id == admin_user.id
    assert audit_event.event_metadata is not None
    assert "changes" in audit_event.event_metadata


@pytest.mark.asyncio
async def test_audit_events_track_actor_info(
    client: TestClient,
    async_session: AsyncSession,
    admin_user: User,
    test_patient: Patient,
    admin_auth_headers: dict[str, str],
) -> None:
    """Test that audit events capture actor information."""
    response = client.post(
        "/api/v1/triage-cases",
        json={"patient_id": test_patient.id},
        headers=admin_auth_headers,
    )

    assert response.status_code == 201
    case_data = response.json()

    # Verify audit event captures actor details
    result = await async_session.execute(
        select(AuditEvent).where(
            AuditEvent.entity_id == case_data["id"],
            AuditEvent.action == "triage_case_created",
        )
    )
    audit_event = result.scalar_one_or_none()

    assert audit_event is not None
    assert audit_event.actor_type.value == "staff"
    assert audit_event.actor_id == admin_user.id
    assert audit_event.actor_email == admin_user.email
