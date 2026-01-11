"""Incident management service for Sprint 6.

Handles incident workflow: open/review/close.
Includes permission validation for workflow transitions.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import (
    Incident,
    IncidentCategory,
    IncidentSeverity,
    IncidentStatus,
)
from app.services.audit import write_audit_event


class IncidentPermissionError(Exception):
    """Raised when user lacks permission for incident action."""
    pass


class IncidentNotFoundError(Exception):
    """Raised when incident not found."""
    pass


class IncidentWorkflowError(Exception):
    """Raised when workflow transition is invalid."""
    pass


# Role-based permissions for incident workflow
INCIDENT_PERMISSIONS = {
    "create": ["clinician", "admin", "nurse", "receptionist"],
    "view": ["clinician", "admin", "nurse", "receptionist", "manager"],
    "start_review": ["clinician", "admin", "manager"],
    "close": ["admin", "manager", "clinical_lead"],
    "reopen": ["admin", "manager", "clinical_lead"],
    "mark_cqc_reportable": ["admin", "manager", "clinical_lead"],
}


def generate_reference_number() -> str:
    """Generate unique incident reference number."""
    timestamp = datetime.now().strftime("%Y%m%d")
    unique_id = uuid.uuid4().hex[:6].upper()
    return f"INC-{timestamp}-{unique_id}"


class IncidentService:
    """Service for managing clinical incidents."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _check_permission(
        self,
        action: str,
        user_roles: list[str],
    ) -> bool:
        """Check if user has permission for action."""
        allowed_roles = INCIDENT_PERMISSIONS.get(action, [])
        return any(role in allowed_roles for role in user_roles)

    async def create_incident(
        self,
        title: str,
        description: str,
        category: str,
        severity: str,
        reported_by: str,
        user_roles: list[str],
        triage_case_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        immediate_actions: Optional[str] = None,
    ) -> Incident:
        """Create a new incident."""
        if not self._check_permission("create", user_roles):
            raise IncidentPermissionError("User does not have permission to create incidents")

        incident = Incident(
            id=str(uuid.uuid4()),
            reference_number=generate_reference_number(),
            triage_case_id=triage_case_id,
            patient_id=patient_id,
            category=category,
            severity=severity,
            status=IncidentStatus.OPEN.value,
            title=title,
            description=description,
            immediate_actions_taken=immediate_actions,
            reported_by=reported_by,
            reported_at=datetime.now(),
        )

        self.session.add(incident)

        # Write audit event
        await write_audit_event(
            session=self.session,
            action="incident.created",
            category="governance",
            actor_type="user",
            actor_id=reported_by,
            entity_type="incident",
            entity_id=incident.id,
            metadata={
                "reference_number": incident.reference_number,
                "category": category,
                "severity": severity,
                "triage_case_id": triage_case_id,
            },
        )

        await self.session.commit()
        await self.session.refresh(incident)

        return incident

    async def get_incident(
        self,
        incident_id: str,
        user_roles: list[str],
    ) -> Incident:
        """Get incident by ID."""
        if not self._check_permission("view", user_roles):
            raise IncidentPermissionError("User does not have permission to view incidents")

        result = await self.session.execute(
            select(Incident).where(
                and_(
                    Incident.id == incident_id,
                    Incident.deleted_at.is_(None),
                )
            )
        )
        incident = result.scalar_one_or_none()

        if not incident:
            raise IncidentNotFoundError(f"Incident not found: {incident_id}")

        return incident

    async def get_incident_by_reference(
        self,
        reference_number: str,
        user_roles: list[str],
    ) -> Incident:
        """Get incident by reference number."""
        if not self._check_permission("view", user_roles):
            raise IncidentPermissionError("User does not have permission to view incidents")

        result = await self.session.execute(
            select(Incident).where(
                and_(
                    Incident.reference_number == reference_number,
                    Incident.deleted_at.is_(None),
                )
            )
        )
        incident = result.scalar_one_or_none()

        if not incident:
            raise IncidentNotFoundError(f"Incident not found: {reference_number}")

        return incident

    async def start_review(
        self,
        incident_id: str,
        reviewer_id: str,
        user_roles: list[str],
    ) -> Incident:
        """Start review of an incident."""
        if not self._check_permission("start_review", user_roles):
            raise IncidentPermissionError("User does not have permission to review incidents")

        incident = await self.get_incident(incident_id, user_roles)

        if incident.status != IncidentStatus.OPEN.value:
            raise IncidentWorkflowError("Can only start review on OPEN incidents")

        incident.start_review(reviewer_id)

        await write_audit_event(
            session=self.session,
            action="incident.review_started",
            category="governance",
            actor_type="user",
            actor_id=reviewer_id,
            entity_type="incident",
            entity_id=incident.id,
            metadata={"reference_number": incident.reference_number},
        )

        await self.session.commit()
        await self.session.refresh(incident)

        return incident

    async def add_review_notes(
        self,
        incident_id: str,
        reviewer_id: str,
        notes: str,
        user_roles: list[str],
    ) -> Incident:
        """Add review notes to incident."""
        if not self._check_permission("start_review", user_roles):
            raise IncidentPermissionError("User does not have permission to review incidents")

        incident = await self.get_incident(incident_id, user_roles)

        if incident.status != IncidentStatus.UNDER_REVIEW.value:
            raise IncidentWorkflowError("Can only add notes to incidents under review")

        existing_notes = incident.review_notes or ""
        timestamp = datetime.now().isoformat()
        incident.review_notes = f"{existing_notes}\n\n[{timestamp}] {notes}".strip()

        await self.session.commit()
        await self.session.refresh(incident)

        return incident

    async def close_incident(
        self,
        incident_id: str,
        closed_by: str,
        closure_reason: str,
        user_roles: list[str],
        lessons_learned: Optional[str] = None,
        preventive_actions: Optional[str] = None,
    ) -> Incident:
        """Close an incident."""
        if not self._check_permission("close", user_roles):
            raise IncidentPermissionError("User does not have permission to close incidents")

        incident = await self.get_incident(incident_id, user_roles)

        if incident.status == IncidentStatus.CLOSED.value:
            raise IncidentWorkflowError("Incident is already closed")

        incident.close(
            closed_by=closed_by,
            closure_reason=closure_reason,
            lessons_learned=lessons_learned,
            preventive_actions=preventive_actions,
        )

        await write_audit_event(
            session=self.session,
            action="incident.closed",
            category="governance",
            actor_type="user",
            actor_id=closed_by,
            entity_type="incident",
            entity_id=incident.id,
            metadata={
                "reference_number": incident.reference_number,
                "closure_reason": closure_reason,
            },
        )

        await self.session.commit()
        await self.session.refresh(incident)

        return incident

    async def reopen_incident(
        self,
        incident_id: str,
        reopened_by: str,
        reason: str,
        user_roles: list[str],
    ) -> Incident:
        """Reopen a closed incident."""
        if not self._check_permission("reopen", user_roles):
            raise IncidentPermissionError("User does not have permission to reopen incidents")

        incident = await self.get_incident(incident_id, user_roles)

        if incident.status != IncidentStatus.CLOSED.value:
            raise IncidentWorkflowError("Can only reopen CLOSED incidents")

        incident.reopen(reason)

        await write_audit_event(
            session=self.session,
            action="incident.reopened",
            category="governance",
            actor_type="user",
            actor_id=reopened_by,
            entity_type="incident",
            entity_id=incident.id,
            metadata={
                "reference_number": incident.reference_number,
                "reopen_reason": reason,
            },
        )

        await self.session.commit()
        await self.session.refresh(incident)

        return incident

    async def mark_cqc_reportable(
        self,
        incident_id: str,
        marked_by: str,
        user_roles: list[str],
    ) -> Incident:
        """Mark incident as reportable to CQC."""
        if not self._check_permission("mark_cqc_reportable", user_roles):
            raise IncidentPermissionError("User does not have permission to mark CQC reportable")

        incident = await self.get_incident(incident_id, user_roles)

        incident.reportable_to_cqc = True

        await write_audit_event(
            session=self.session,
            action="incident.marked_cqc_reportable",
            category="governance",
            actor_type="user",
            actor_id=marked_by,
            entity_type="incident",
            entity_id=incident.id,
            metadata={"reference_number": incident.reference_number},
        )

        await self.session.commit()
        await self.session.refresh(incident)

        return incident

    async def report_to_cqc(
        self,
        incident_id: str,
        reported_by: str,
        user_roles: list[str],
    ) -> Incident:
        """Record that incident was reported to CQC."""
        if not self._check_permission("mark_cqc_reportable", user_roles):
            raise IncidentPermissionError("User does not have permission to report to CQC")

        incident = await self.get_incident(incident_id, user_roles)

        if not incident.reportable_to_cqc:
            raise IncidentWorkflowError("Incident must be marked as CQC reportable first")

        incident.cqc_reported_at = datetime.now()

        await write_audit_event(
            session=self.session,
            action="incident.reported_to_cqc",
            category="governance",
            actor_type="user",
            actor_id=reported_by,
            entity_type="incident",
            entity_id=incident.id,
            metadata={
                "reference_number": incident.reference_number,
                "reported_at": incident.cqc_reported_at.isoformat(),
            },
        )

        await self.session.commit()
        await self.session.refresh(incident)

        return incident

    async def list_incidents(
        self,
        user_roles: list[str],
        status: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Incident], int]:
        """List incidents with optional filters."""
        if not self._check_permission("view", user_roles):
            raise IncidentPermissionError("User does not have permission to view incidents")

        query = select(Incident).where(Incident.deleted_at.is_(None))

        if status:
            query = query.where(Incident.status == status)
        if severity:
            query = query.where(Incident.severity == severity)
        if category:
            query = query.where(Incident.category == category)

        # Get total count
        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        # Get paginated results
        query = query.order_by(Incident.reported_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(query)
        incidents = list(result.scalars().all())

        return incidents, total

    async def get_incident_counts_by_status(
        self,
        user_roles: list[str],
    ) -> dict[str, int]:
        """Get count of incidents by status."""
        if not self._check_permission("view", user_roles):
            raise IncidentPermissionError("User does not have permission to view incidents")

        result = await self.session.execute(
            select(
                Incident.status,
                func.count(Incident.id).label("count"),
            )
            .where(Incident.deleted_at.is_(None))
            .group_by(Incident.status)
        )

        return {row.status: row.count for row in result.all()}
