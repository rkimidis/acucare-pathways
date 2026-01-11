"""Triage case schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.triage_case import TriageCaseStatus, TriageTier


class TriageCaseCreate(BaseModel):
    """Schema for creating a new triage case."""

    patient_id: str


class TriageCaseUpdate(BaseModel):
    """Schema for updating a triage case."""

    status: TriageCaseStatus | None = None
    assigned_clinician_id: str | None = None
    clinical_notes: str | None = Field(None, max_length=10000)


class TriageCaseRead(BaseModel):
    """Schema for reading triage case data."""

    id: str
    patient_id: str
    status: TriageCaseStatus
    tier: TriageTier | None
    questionnaire_version_id: str | None
    ruleset_version: str | None
    ruleset_hash: str | None
    tier_explanation: dict | None
    assigned_clinician_id: str | None
    clinical_notes: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class TriageTierResult(BaseModel):
    """Result of triage tier calculation."""

    tier: TriageTier
    explanation: dict
    ruleset_version: str
    ruleset_hash: str
    triggered_rules: list[str]
