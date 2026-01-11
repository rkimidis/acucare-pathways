"""Governance models for Sprint 6.

Includes:
- Incident workflow (open/review/close)
- Ruleset approval records (change control)
- Questionnaire version history
- Evidence export records
- LLM summary drafts
"""

from datetime import datetime
from enum import Enum
from typing import Optional
import hashlib
import json

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, SoftDeleteMixin


class IncidentStatus(str, Enum):
    """Incident workflow states."""
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    CLOSED = "closed"


class IncidentSeverity(str, Enum):
    """Incident severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentCategory(str, Enum):
    """Incident categories."""
    CLINICAL = "clinical"
    SAFEGUARDING = "safeguarding"
    MEDICATION = "medication"
    COMMUNICATION = "communication"
    ACCESS = "access"
    INFORMATION_GOVERNANCE = "information_governance"
    OTHER = "other"


class Incident(Base, TimestampMixin, SoftDeleteMixin):
    """Clinical incident linked to a triage case."""

    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    reference_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )

    # Link to case
    triage_case_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("triage_cases.id"), nullable=True, index=True
    )
    patient_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("patients.id"), nullable=True, index=True
    )

    # Classification
    category: Mapped[str] = mapped_column(
        String(50), default=IncidentCategory.OTHER.value, nullable=False
    )
    severity: Mapped[str] = mapped_column(
        String(20), default=IncidentSeverity.MEDIUM.value, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=IncidentStatus.OPEN.value, nullable=False, index=True
    )

    # Details
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    immediate_actions_taken: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Workflow tracking
    reported_by: Mapped[str] = mapped_column(String(36), nullable=False)
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Review phase
    reviewer_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    review_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Closure
    closed_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lessons_learned: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preventive_actions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # CQC reporting flag
    reportable_to_cqc: Mapped[bool] = mapped_column(Boolean, default=False)
    cqc_reported_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_incidents_status_severity", "status", "severity"),
        Index("ix_incidents_reported_at", "reported_at"),
    )

    def start_review(self, reviewer_id: str) -> None:
        """Transition to under_review status."""
        if self.status != IncidentStatus.OPEN.value:
            raise ValueError("Can only start review on OPEN incidents")
        self.status = IncidentStatus.UNDER_REVIEW.value
        self.reviewer_id = reviewer_id
        self.review_started_at = datetime.now()

    def close(
        self,
        closed_by: str,
        closure_reason: str,
        lessons_learned: Optional[str] = None,
        preventive_actions: Optional[str] = None,
    ) -> None:
        """Close the incident."""
        if self.status == IncidentStatus.CLOSED.value:
            raise ValueError("Incident is already closed")
        self.status = IncidentStatus.CLOSED.value
        self.closed_by = closed_by
        self.closed_at = datetime.now()
        self.closure_reason = closure_reason
        self.lessons_learned = lessons_learned
        self.preventive_actions = preventive_actions

    def reopen(self, reason: str) -> None:
        """Reopen a closed incident."""
        if self.status != IncidentStatus.CLOSED.value:
            raise ValueError("Can only reopen CLOSED incidents")
        self.status = IncidentStatus.OPEN.value
        self.review_notes = (self.review_notes or "") + f"\n\nReopened: {reason}"


class ApprovalStatus(str, Enum):
    """Approval workflow states."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RulesetApproval(Base, TimestampMixin):
    """Change control record for ruleset modifications."""

    __tablename__ = "ruleset_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # What changed
    ruleset_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # e.g., "triage_rules", "escalation_rules"
    ruleset_version: Mapped[str] = mapped_column(String(20), nullable=False)
    previous_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Change details
    change_summary: Mapped[str] = mapped_column(Text, nullable=False)
    change_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    rules_added: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    rules_modified: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    rules_removed: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Content hash for integrity
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Submitter
    submitted_by: Mapped[str] = mapped_column(String(36), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Approval workflow
    status: Mapped[str] = mapped_column(
        String(20), default=ApprovalStatus.PENDING.value, nullable=False, index=True
    )
    approved_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approval_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Rejection details
    rejected_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Activation
    activated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("ix_ruleset_approvals_type_version", "ruleset_type", "ruleset_version"),
    )

    @staticmethod
    def compute_content_hash(content: dict) -> str:
        """Compute SHA-256 hash of ruleset content."""
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()

    def approve(self, approver_id: str, notes: Optional[str] = None) -> None:
        """Approve the ruleset change."""
        if self.status != ApprovalStatus.PENDING.value:
            raise ValueError("Can only approve PENDING changes")
        self.status = ApprovalStatus.APPROVED.value
        self.approved_by = approver_id
        self.approved_at = datetime.now()
        self.approval_notes = notes

    def reject(self, rejector_id: str, reason: str) -> None:
        """Reject the ruleset change."""
        if self.status != ApprovalStatus.PENDING.value:
            raise ValueError("Can only reject PENDING changes")
        self.status = ApprovalStatus.REJECTED.value
        self.rejected_by = rejector_id
        self.rejected_at = datetime.now()
        self.rejection_reason = reason

    def activate(self) -> None:
        """Activate an approved ruleset."""
        if self.status != ApprovalStatus.APPROVED.value:
            raise ValueError("Can only activate APPROVED rulesets")
        self.activated_at = datetime.now()
        self.is_active = True


class QuestionnaireVersion(Base, TimestampMixin):
    """Version history for questionnaire definitions."""

    __tablename__ = "questionnaire_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Questionnaire identification
    questionnaire_code: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    previous_version_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("questionnaire_versions.id"), nullable=True
    )

    # Content
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    questions: Mapped[dict] = mapped_column(JSON, nullable=False)
    scoring_rules: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Content hash for integrity
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Change tracking
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default=ApprovalStatus.PENDING.value, nullable=False
    )
    approved_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Activation
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    activated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index(
            "ix_questionnaire_versions_code_version",
            "questionnaire_code",
            "version",
            unique=True,
        ),
    )

    @staticmethod
    def compute_content_hash(questions: dict, scoring_rules: Optional[dict]) -> str:
        """Compute SHA-256 hash of questionnaire content."""
        content = {"questions": questions, "scoring_rules": scoring_rules}
        content_str = json.dumps(content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()


class EvidenceExport(Base, TimestampMixin):
    """Record of evidence exports for audit purposes."""

    __tablename__ = "evidence_exports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Export type
    export_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # "audit_log", "case_pathway", "incident_report"

    # Scope
    date_range_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    date_range_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    triage_case_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("triage_cases.id"), nullable=True
    )
    filters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Export details
    exported_by: Mapped[str] = mapped_column(String(36), nullable=False)
    exported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    export_reason: Mapped[str] = mapped_column(Text, nullable=False)

    # File details
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_format: Mapped[str] = mapped_column(String(20), nullable=False)  # "json", "csv", "pdf"

    # Tamper evidence
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Chain of custody
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    last_downloaded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_downloaded_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    @staticmethod
    def compute_content_hash(content: str) -> str:
        """Compute SHA-256 hash of export content."""
        return hashlib.sha256(content.encode()).hexdigest()


class LLMSummaryStatus(str, Enum):
    """LLM summary approval states."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class LLMSummary(Base, TimestampMixin):
    """LLM-generated clinical summary requiring approval."""

    __tablename__ = "llm_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Source data
    triage_case_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("triage_cases.id"), nullable=False, index=True
    )
    source_data_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "triage_assessment", "check_in", "appointment_notes"
    source_data_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # LLM details (for audit)
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_template_version: Mapped[str] = mapped_column(String(20), nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Generated content
    generated_summary: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Approval workflow
    status: Mapped[str] = mapped_column(
        String(20), default=LLMSummaryStatus.DRAFT.value, nullable=False, index=True
    )

    # Clinician review
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    clinician_edits: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Approval
    approved_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Rejection
    rejected_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    @staticmethod
    def compute_source_hash(source_data: dict) -> str:
        """Compute hash of source data."""
        content_str = json.dumps(source_data, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()

    @staticmethod
    def compute_prompt_hash(prompt: str) -> str:
        """Compute hash of prompt template."""
        return hashlib.sha256(prompt.encode()).hexdigest()

    def submit_for_approval(self) -> None:
        """Submit draft for clinician approval."""
        if self.status != LLMSummaryStatus.DRAFT.value:
            raise ValueError("Can only submit DRAFT summaries")
        self.status = LLMSummaryStatus.PENDING_APPROVAL.value

    def approve(
        self,
        approver_id: str,
        final_summary: Optional[str] = None,
        edits: Optional[str] = None,
    ) -> None:
        """Approve the summary."""
        if self.status != LLMSummaryStatus.PENDING_APPROVAL.value:
            raise ValueError("Can only approve PENDING_APPROVAL summaries")
        self.status = LLMSummaryStatus.APPROVED.value
        self.approved_by = approver_id
        self.approved_at = datetime.now()
        self.clinician_edits = edits
        self.final_summary = final_summary or self.generated_summary

    def reject(self, rejector_id: str, reason: str) -> None:
        """Reject the summary."""
        if self.status != LLMSummaryStatus.PENDING_APPROVAL.value:
            raise ValueError("Can only reject PENDING_APPROVAL summaries")
        self.status = LLMSummaryStatus.REJECTED.value
        self.rejected_by = rejector_id
        self.rejected_at = datetime.now()
        self.rejection_reason = reason
