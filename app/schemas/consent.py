"""Pydantic schemas for consent operations."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConsentCapture(BaseModel):
    """Schema for capturing patient consent."""

    consent_items: dict[str, bool] = Field(
        ...,
        description="Consent items with their acceptance status",
        examples=[{
            "data_processing": True,
            "privacy_policy": True,
            "communication_email": True,
            "communication_sms": False,
        }],
    )
    channels: dict[str, bool] = Field(
        default_factory=dict,
        description="Communication channel preferences",
        examples=[{"email": True, "sms": False, "phone": False}],
    )


class ConsentRead(BaseModel):
    """Schema for reading consent record."""

    id: str
    patient_id: str
    consent_version: str
    channels: dict[str, Any]
    agreed_at: datetime
    consent_items: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class ConsentStatus(BaseModel):
    """Schema for consent status check."""

    has_consented: bool
    consent_version: str | None = None
    agreed_at: datetime | None = None
    current_version: str
    needs_reconsent: bool = False
