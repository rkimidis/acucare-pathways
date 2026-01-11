"""Disposition schemas for triage finalization."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class DispositionConfirm(BaseModel):
    """Schema for confirming a disposition (no changes)."""

    clinical_notes: Optional[str] = Field(None, max_length=10000)


class DispositionOverride(BaseModel):
    """Schema for overriding a disposition.

    Rationale is REQUIRED when overriding tier or pathway.
    """

    tier: str = Field(..., description="New tier (RED, AMBER, GREEN, BLUE)")
    pathway: str = Field(..., description="New pathway")
    rationale: str = Field(
        ...,
        min_length=20,
        max_length=5000,
        description="Clinical rationale for override (min 20 chars required)",
    )
    clinical_notes: Optional[str] = Field(None, max_length=10000)

    @model_validator(mode="after")
    def validate_tier(self) -> "DispositionOverride":
        """Validate tier is a valid value."""
        valid_tiers = {"RED", "AMBER", "GREEN", "BLUE"}
        if self.tier.upper() not in valid_tiers:
            raise ValueError(f"tier must be one of: {', '.join(valid_tiers)}")
        self.tier = self.tier.upper()
        return self


class DispositionFinalize(BaseModel):
    """Schema for finalizing a disposition.

    Either confirm the draft or override with new values.
    If override is provided, rationale is required.
    """

    action: str = Field(
        ...,
        description="Action to take: 'confirm' or 'override'",
    )
    override: Optional[DispositionOverride] = Field(
        None,
        description="Override details (required if action='override')",
    )
    clinical_notes: Optional[str] = Field(None, max_length=10000)

    @model_validator(mode="after")
    def validate_action_and_override(self) -> "DispositionFinalize":
        """Validate action matches override presence."""
        if self.action not in ("confirm", "override"):
            raise ValueError("action must be 'confirm' or 'override'")
        if self.action == "override" and self.override is None:
            raise ValueError("override details required when action='override'")
        if self.action == "confirm" and self.override is not None:
            raise ValueError("override must be None when action='confirm'")
        return self


class DispositionDraftRead(BaseModel):
    """Schema for reading disposition draft data."""

    id: str
    triage_case_id: str
    tier: str
    pathway: str
    self_book_allowed: bool
    clinician_review_required: bool
    rules_fired: list[str]
    explanations: list[str]
    ruleset_version: str
    ruleset_hash: str
    is_applied: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DispositionFinalRead(BaseModel):
    """Schema for reading final disposition data."""

    id: str
    triage_case_id: str
    draft_id: Optional[str]
    tier: str
    pathway: str
    self_book_allowed: bool
    is_override: bool
    original_tier: Optional[str]
    original_pathway: Optional[str]
    rationale: Optional[str]
    clinician_id: str
    finalized_at: datetime
    clinical_notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class QueueFilter(BaseModel):
    """Filter parameters for triage queue."""

    tier: Optional[str] = Field(None, description="Filter by tier (RED, AMBER, GREEN, BLUE)")
    sla_status: Optional[str] = Field(
        None,
        description="Filter by SLA status: 'breached', 'at_risk' (within 15 min), 'ok'",
    )
    status: Optional[str] = Field(None, description="Filter by case status")
    assigned_to_me: bool = Field(False, description="Only show cases assigned to current user")
    needs_review: bool = Field(False, description="Only show cases requiring clinician review")


class QueueItem(BaseModel):
    """Single item in the triage queue."""

    id: str
    patient_id: str
    tier: Optional[str]
    pathway: Optional[str]
    status: str
    sla_deadline: Optional[datetime]
    sla_breached: bool
    sla_minutes_remaining: Optional[int]
    clinician_review_required: bool
    assigned_clinician_id: Optional[str]
    created_at: datetime
    triaged_at: Optional[datetime]

    model_config = {"from_attributes": True}


class QueueResponse(BaseModel):
    """Response for triage queue endpoint."""

    items: list[QueueItem]
    total: int
    red_count: int
    amber_count: int
    green_count: int
    blue_count: int
    breached_count: int


class CaseSummary(BaseModel):
    """Full case summary for clinician review."""

    id: str
    patient_id: str
    status: str
    tier: Optional[str]
    pathway: Optional[str]
    clinician_review_required: bool
    self_book_allowed: bool

    # Triage details
    ruleset_version: Optional[str]
    ruleset_hash: Optional[str]
    tier_explanation: Optional[dict]

    # SLA tracking
    triaged_at: Optional[datetime]
    sla_deadline: Optional[datetime]
    sla_target_minutes: Optional[int]
    sla_breached: bool
    sla_minutes_remaining: Optional[int]

    # Assignment
    assigned_clinician_id: Optional[str]
    clinical_notes: Optional[str]

    # Review status
    reviewed_at: Optional[datetime]
    reviewed_by: Optional[str]

    # Disposition draft (if exists)
    disposition_draft: Optional[DispositionDraftRead]

    # Disposition final (if exists)
    disposition_final: Optional[DispositionFinalRead]

    # Risk flags
    risk_flags: list[dict]

    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}
