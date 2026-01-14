"""Pydantic schemas for questionnaire operations."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class QuestionnaireDefinitionRead(BaseModel):
    """Schema for reading questionnaire definition."""

    id: str
    name: str
    version: str
    description: str | None = None
    schema_json: dict = Field(..., alias="schema")
    schema_hash: str
    is_active: bool
    display_order: int
    previous_version_id: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class QuestionnaireResponseCreate(BaseModel):
    """Schema for creating/updating a questionnaire response."""

    triage_case_id: str
    questionnaire_definition_id: str
    answers: dict[str, Any]
    is_complete: bool = False


class QuestionnaireResponseRead(BaseModel):
    """Schema for reading questionnaire response."""

    id: str
    triage_case_id: str
    questionnaire_definition_id: str
    answers: dict[str, Any]
    computed_scores: dict[str, Any] | None = None
    is_complete: bool
    submitted_at: datetime | None = None
    completion_time_seconds: int | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class IntakeResponseSubmit(BaseModel):
    """Schema for submitting intake questionnaire response."""

    answers: dict[str, Any] = Field(..., description="Questionnaire answers as JSON")


class IntakeDraftSave(BaseModel):
    """Schema for saving draft intake response."""

    answers: dict[str, Any] = Field(..., description="Partial answers to save")


class SafetyBannerResponse(BaseModel):
    """Schema for safety banner configuration."""

    enabled: bool
    text: str
    consent_version: str
