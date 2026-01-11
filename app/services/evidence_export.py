"""Evidence export service for Sprint 6.

Provides tamper-evident exports for:
- Audit log exports for date ranges
- Case pathway exports (decisions + rules fired + timestamps)
- Incident reports
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditEvent
from app.models.governance import EvidenceExport
from app.models.questionnaire import QuestionnaireResponse
from app.models.score import Score
from app.models.triage_case import TriageCase


@dataclass
class AuditEventExport:
    """Exported audit event record."""
    id: str
    timestamp: str
    action: str
    category: str
    actor_type: str
    actor_id: Optional[str]
    entity_type: str
    entity_id: str
    metadata: Optional[dict]


@dataclass
class PathwayStep:
    """A step in the case pathway."""
    timestamp: str
    step_type: str
    description: str
    actor: Optional[str]
    data: Optional[dict]


@dataclass
class CasePathwayExport:
    """Complete pathway export for a case."""
    case_id: str
    patient_id: str
    export_timestamp: str
    pathway_steps: list[PathwayStep]
    audit_events: list[AuditEventExport]
    questionnaire_responses: list[dict]
    scores: list[dict]
    risk_flags: list[dict]
    disposition: Optional[dict]


@dataclass
class ExportManifest:
    """Manifest for export with integrity verification."""
    export_id: str
    export_type: str
    exported_by: str
    exported_at: str
    export_reason: str
    record_count: int
    date_range_start: Optional[str]
    date_range_end: Optional[str]
    content_hash: str
    hash_algorithm: str


class EvidenceExportService:
    """Service for generating tamper-evident evidence exports."""

    HASH_ALGORITHM = "sha256"

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_chain_hash(records: list[dict]) -> str:
        """Compute chained hash for ordered records (tamper-evident)."""
        chain_hash = ""
        for record in records:
            record_str = json.dumps(record, sort_keys=True, default=str)
            combined = chain_hash + record_str
            chain_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
        return chain_hash

    async def export_audit_log(
        self,
        start_date: datetime,
        end_date: datetime,
        exported_by: str,
        export_reason: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        category: Optional[str] = None,
    ) -> tuple[dict, EvidenceExport]:
        """Export audit events for a date range with tamper-evident hash."""
        # Build query
        query = select(AuditEvent).where(
            and_(
                AuditEvent.created_at >= start_date,
                AuditEvent.created_at <= end_date,
            )
        )

        if entity_type:
            query = query.where(AuditEvent.entity_type == entity_type)
        if entity_id:
            query = query.where(AuditEvent.entity_id == entity_id)
        if category:
            query = query.where(AuditEvent.category == category)

        query = query.order_by(AuditEvent.created_at)

        result = await self.session.execute(query)
        events = result.scalars().all()

        # Convert to export format
        exported_events = []
        for event in events:
            exported_events.append({
                "id": event.id,
                "timestamp": event.timestamp.isoformat(),
                "action": event.action,
                "category": event.category,
                "actor_type": event.actor_type,
                "actor_id": event.actor_id,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "metadata": event.event_metadata,
            })

        # Compute tamper-evident hash
        content_hash = self.compute_chain_hash(exported_events)

        # Create manifest
        export_id = str(uuid.uuid4())
        manifest = ExportManifest(
            export_id=export_id,
            export_type="audit_log",
            exported_by=exported_by,
            exported_at=datetime.now().isoformat(),
            export_reason=export_reason,
            record_count=len(exported_events),
            date_range_start=start_date.isoformat(),
            date_range_end=end_date.isoformat(),
            content_hash=content_hash,
            hash_algorithm=self.HASH_ALGORITHM,
        )

        # Build complete export
        export_data = {
            "manifest": asdict(manifest),
            "events": exported_events,
        }

        # Serialize for storage
        export_json = json.dumps(export_data, default=str)

        # Create export record
        export_record = EvidenceExport(
            id=export_id,
            export_type="audit_log",
            date_range_start=start_date,
            date_range_end=end_date,
            exported_by=exported_by,
            exported_at=datetime.now(),
            export_reason=export_reason,
            file_name=f"audit_export_{export_id}.json",
            file_size_bytes=len(export_json.encode("utf-8")),
            file_format="json",
            content_hash=content_hash,
            record_count=len(exported_events),
            filters={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "category": category,
            },
        )

        self.session.add(export_record)
        await self.session.commit()
        await self.session.refresh(export_record)

        return export_data, export_record

    async def export_case_pathway(
        self,
        triage_case_id: str,
        exported_by: str,
        export_reason: str,
    ) -> tuple[dict, EvidenceExport]:
        """Export complete pathway for a case."""
        # Get triage case
        case_result = await self.session.execute(
            select(TriageCase).where(TriageCase.id == triage_case_id)
        )
        case = case_result.scalar_one_or_none()

        if not case:
            raise ValueError(f"Case not found: {triage_case_id}")

        # Get audit events for this case
        events_result = await self.session.execute(
            select(AuditEvent).where(
                and_(
                    AuditEvent.entity_id == triage_case_id,
                    AuditEvent.entity_type == "triage_case",
                )
            ).order_by(AuditEvent.created_at)
        )
        audit_events = events_result.scalars().all()

        # Get questionnaire responses
        responses_result = await self.session.execute(
            select(QuestionnaireResponse).where(
                QuestionnaireResponse.triage_case_id == triage_case_id
            ).order_by(QuestionnaireResponse.submitted_at)
        )
        responses = responses_result.scalars().all()

        # Get scores
        scores_result = await self.session.execute(
            select(Score).where(
                Score.triage_case_id == triage_case_id
            ).order_by(Score.created_at)
        )
        scores = scores_result.scalars().all()

        # Build pathway steps from audit events
        pathway_steps = []
        for event in audit_events:
            step = PathwayStep(
                timestamp=event.timestamp.isoformat(),
                step_type=event.action,
                description=self._get_step_description(event),
                actor=event.actor_id,
                data=event.event_metadata,
            )
            pathway_steps.append(asdict(step))

        # Build export data
        export_events = []
        for event in audit_events:
            export_events.append({
                "id": event.id,
                "timestamp": event.timestamp.isoformat(),
                "action": event.action,
                "category": event.category,
                "actor_type": event.actor_type,
                "actor_id": event.actor_id,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "metadata": event.event_metadata,
            })

        export_responses = []
        for response in responses:
            export_responses.append({
                "id": response.id,
                "questionnaire_id": response.questionnaire_id,
                "submitted_at": response.submitted_at.isoformat() if response.submitted_at else None,
                "answers": response.answers,
            })

        export_scores = []
        for score in scores:
            export_scores.append({
                "id": score.id,
                "score_type": score.score_type,
                "value": score.value,
                "severity_band": score.severity_band,
                "created_at": score.created_at.isoformat() if score.created_at else None,
            })

        # Compute content hash
        all_records = export_events + export_responses + export_scores
        content_hash = self.compute_chain_hash(all_records)

        # Create manifest
        export_id = str(uuid.uuid4())
        manifest = ExportManifest(
            export_id=export_id,
            export_type="case_pathway",
            exported_by=exported_by,
            exported_at=datetime.now().isoformat(),
            export_reason=export_reason,
            record_count=len(all_records),
            date_range_start=None,
            date_range_end=None,
            content_hash=content_hash,
            hash_algorithm=self.HASH_ALGORITHM,
        )

        # Build complete export
        export_data = {
            "manifest": asdict(manifest),
            "case": {
                "id": case.id,
                "patient_id": case.patient_id,
                "tier": case.tier,
                "status": case.status,
                "pathway": case.pathway,
                "created_at": case.created_at.isoformat() if case.created_at else None,
            },
            "pathway_steps": pathway_steps,
            "audit_events": export_events,
            "questionnaire_responses": export_responses,
            "scores": export_scores,
        }

        # Serialize for storage
        export_json = json.dumps(export_data, default=str)

        # Create export record
        export_record = EvidenceExport(
            id=export_id,
            export_type="case_pathway",
            triage_case_id=triage_case_id,
            exported_by=exported_by,
            exported_at=datetime.now(),
            export_reason=export_reason,
            file_name=f"case_pathway_{triage_case_id}_{export_id}.json",
            file_size_bytes=len(export_json.encode("utf-8")),
            file_format="json",
            content_hash=content_hash,
            record_count=len(all_records),
        )

        self.session.add(export_record)
        await self.session.commit()
        await self.session.refresh(export_record)

        return export_data, export_record

    def _get_step_description(self, event: AuditEvent) -> str:
        """Generate human-readable description for pathway step."""
        descriptions = {
            "triage.case_created": "Case created",
            "triage.questionnaire_started": "Questionnaire started",
            "triage.questionnaire_completed": "Questionnaire completed",
            "triage.score_calculated": "Assessment scores calculated",
            "triage.tier_assigned": "Triage tier assigned",
            "triage.risk_flag_added": "Risk flag identified",
            "triage.disposition_drafted": "Disposition drafted",
            "triage.disposition_approved": "Disposition approved",
            "triage.case_escalated": "Case escalated",
            "monitoring.checkin_sent": "Check-in sent",
            "monitoring.checkin_completed": "Check-in completed",
            "monitoring.escalation": "Escalation triggered",
            "scheduling.appointment_booked": "Appointment booked",
            "scheduling.appointment_completed": "Appointment completed",
        }

        return descriptions.get(event.action, event.action.replace("_", " ").replace(".", ": ").title())

    @staticmethod
    def verify_export_integrity(export_data: dict) -> bool:
        """Verify the integrity of an export by recalculating the hash."""
        manifest = export_data.get("manifest", {})
        stored_hash = manifest.get("content_hash")

        if not stored_hash:
            return False

        # Determine what to hash based on export type
        export_type = manifest.get("export_type")

        if export_type == "audit_log":
            records = export_data.get("events", [])
        elif export_type == "case_pathway":
            records = (
                export_data.get("audit_events", []) +
                export_data.get("questionnaire_responses", []) +
                export_data.get("scores", [])
            )
        else:
            return False

        # Recompute hash
        computed_hash = EvidenceExportService.compute_chain_hash(records)

        return computed_hash == stored_hash

    async def record_download(
        self,
        export_id: str,
        downloaded_by: str,
    ) -> None:
        """Record that an export was downloaded."""
        result = await self.session.execute(
            select(EvidenceExport).where(EvidenceExport.id == export_id)
        )
        export = result.scalar_one_or_none()

        if export:
            export.download_count += 1
            export.last_downloaded_at = datetime.now()
            export.last_downloaded_by = downloaded_by
            await self.session.commit()

    async def get_export_history(
        self,
        export_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[EvidenceExport]:
        """Get export history."""
        query = select(EvidenceExport).order_by(EvidenceExport.exported_at.desc())

        if export_type:
            query = query.where(EvidenceExport.export_type == export_type)

        query = query.limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def export_evidence_bundle(
        self,
        start_date: datetime,
        end_date: datetime,
        exported_by: str,
        export_reason: str,
        include_audit_log: bool = True,
        include_incidents: bool = True,
        include_ruleset_approvals: bool = True,
        include_reporting_summary: bool = True,
    ) -> tuple[dict, EvidenceExport]:
        """Export comprehensive evidence bundle for CQC inspection.

        Combines:
        - Audit log for date range
        - Incident reports
        - Ruleset approval history
        - Reporting dashboard summary
        """
        from app.models.governance import Incident, RulesetApproval

        bundle = {
            "bundle_type": "cqc_evidence",
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "generated_at": datetime.now().isoformat(),
            "generated_by": exported_by,
            "export_reason": export_reason,
            "sections": {},
        }

        all_records = []

        # 1. Audit log
        if include_audit_log:
            query = select(AuditEvent).where(
                and_(
                    AuditEvent.created_at >= start_date,
                    AuditEvent.created_at <= end_date,
                )
            ).order_by(AuditEvent.created_at)
            result = await self.session.execute(query)
            events = result.scalars().all()

            audit_records = []
            for event in events:
                record = {
                    "id": event.id,
                    "timestamp": event.timestamp.isoformat(),
                    "action": event.action,
                    "category": event.category,
                    "actor_type": event.actor_type,
                    "actor_id": event.actor_id,
                    "entity_type": event.entity_type,
                    "entity_id": event.entity_id,
                    "metadata": event.event_metadata,
                }
                audit_records.append(record)
                all_records.append(record)

            bundle["sections"]["audit_log"] = {
                "record_count": len(audit_records),
                "events": audit_records,
            }

        # 2. Incidents
        if include_incidents:
            query = select(Incident).where(
                and_(
                    Incident.reported_at >= start_date,
                    Incident.reported_at <= end_date,
                )
            ).order_by(Incident.reported_at)
            result = await self.session.execute(query)
            incidents = result.scalars().all()

            incident_records = []
            for incident in incidents:
                record = {
                    "id": incident.id,
                    "reference_number": incident.reference_number,
                    "title": incident.title,
                    "description": incident.description,
                    "category": incident.category,
                    "severity": incident.severity,
                    "status": incident.status,
                    "reported_by": incident.reported_by,
                    "reported_at": incident.reported_at.isoformat() if incident.reported_at else None,
                    "reviewer_id": incident.reviewer_id,
                    "review_started_at": incident.review_started_at.isoformat() if incident.review_started_at else None,
                    "review_notes": incident.review_notes,
                    "closed_by": incident.closed_by,
                    "closed_at": incident.closed_at.isoformat() if incident.closed_at else None,
                    "closure_reason": incident.closure_reason,
                    "lessons_learned": incident.lessons_learned,
                    "preventive_actions": incident.preventive_actions,
                    "reportable_to_cqc": incident.reportable_to_cqc,
                    "cqc_reported_at": incident.cqc_reported_at.isoformat() if incident.cqc_reported_at else None,
                }
                incident_records.append(record)
                all_records.append(record)

            bundle["sections"]["incidents"] = {
                "record_count": len(incident_records),
                "summary": {
                    "total": len(incident_records),
                    "by_status": self._count_by_field(incident_records, "status"),
                    "by_severity": self._count_by_field(incident_records, "severity"),
                    "by_category": self._count_by_field(incident_records, "category"),
                    "cqc_reportable": sum(1 for i in incident_records if i.get("reportable_to_cqc")),
                },
                "incidents": incident_records,
            }

        # 3. Ruleset approvals
        if include_ruleset_approvals:
            query = select(RulesetApproval).where(
                and_(
                    RulesetApproval.submitted_at >= start_date,
                    RulesetApproval.submitted_at <= end_date,
                )
            ).order_by(RulesetApproval.submitted_at)
            result = await self.session.execute(query)
            approvals = result.scalars().all()

            approval_records = []
            for approval in approvals:
                record = {
                    "id": approval.id,
                    "ruleset_type": approval.ruleset_type,
                    "ruleset_version": approval.ruleset_version,
                    "previous_version": approval.previous_version,
                    "change_summary": approval.change_summary,
                    "change_rationale": approval.change_rationale,
                    "content_hash": approval.content_hash,
                    "submitted_by": approval.submitted_by,
                    "submitted_at": approval.submitted_at.isoformat() if approval.submitted_at else None,
                    "status": approval.status,
                    "approved_by": approval.approved_by,
                    "approved_at": approval.approved_at.isoformat() if approval.approved_at else None,
                    "approval_notes": approval.approval_notes,
                    "rejected_by": approval.rejected_by,
                    "rejected_at": approval.rejected_at.isoformat() if approval.rejected_at else None,
                    "rejection_reason": approval.rejection_reason,
                    "is_active": approval.is_active,
                    "activated_at": approval.activated_at.isoformat() if approval.activated_at else None,
                }
                approval_records.append(record)
                all_records.append(record)

            bundle["sections"]["ruleset_approvals"] = {
                "record_count": len(approval_records),
                "summary": {
                    "total": len(approval_records),
                    "by_status": self._count_by_field(approval_records, "status"),
                    "by_type": self._count_by_field(approval_records, "ruleset_type"),
                    "currently_active": sum(1 for a in approval_records if a.get("is_active")),
                },
                "approvals": approval_records,
            }

        # 4. Reporting summary (computed metrics)
        if include_reporting_summary:
            bundle["sections"]["reporting_summary"] = {
                "note": "Dashboard metrics are computed at runtime via /api/v1/reporting/dashboard",
                "available_reports": [
                    "volumes/tier",
                    "volumes/pathway",
                    "wait-times",
                    "no-shows",
                    "outcome-trends",
                    "sla-breaches",
                    "alerts-summary",
                ],
            }

        # Compute tamper-evident hash
        content_hash = self.compute_chain_hash(all_records)

        # Create manifest
        export_id = str(uuid.uuid4())
        bundle["manifest"] = {
            "export_id": export_id,
            "export_type": "evidence_bundle",
            "exported_by": exported_by,
            "exported_at": datetime.now().isoformat(),
            "export_reason": export_reason,
            "record_count": len(all_records),
            "date_range_start": start_date.isoformat(),
            "date_range_end": end_date.isoformat(),
            "content_hash": content_hash,
            "hash_algorithm": self.HASH_ALGORITHM,
            "sections_included": list(bundle["sections"].keys()),
        }

        # Serialize for storage
        export_json = json.dumps(bundle, default=str)

        # Create export record
        export_record = EvidenceExport(
            id=export_id,
            export_type="evidence_bundle",
            date_range_start=start_date,
            date_range_end=end_date,
            exported_by=exported_by,
            exported_at=datetime.now(),
            export_reason=export_reason,
            file_name=f"cqc_evidence_bundle_{export_id}.json",
            file_size_bytes=len(export_json.encode("utf-8")),
            file_format="json",
            content_hash=content_hash,
            record_count=len(all_records),
            filters={
                "include_audit_log": include_audit_log,
                "include_incidents": include_incidents,
                "include_ruleset_approvals": include_ruleset_approvals,
                "include_reporting_summary": include_reporting_summary,
            },
        )

        self.session.add(export_record)
        await self.session.commit()
        await self.session.refresh(export_record)

        return bundle, export_record

    @staticmethod
    def _count_by_field(records: list[dict], field: str) -> dict[str, int]:
        """Count records by field value."""
        counts: dict[str, int] = {}
        for record in records:
            value = record.get(field, "unknown")
            counts[value] = counts.get(value, 0) + 1
        return counts
