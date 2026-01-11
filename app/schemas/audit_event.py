"""Audit event schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.audit_event import ActorType


class AuditEventCreate(BaseModel):
    """Schema for creating an audit event (internal use)."""

    actor_type: ActorType
    actor_id: str | None = None
    actor_email: str | None = None
    action: str = Field(max_length=100)
    action_category: str | None = Field(None, max_length=50)
    entity_type: str = Field(max_length=100)
    entity_id: str | None = None
    metadata: dict[str, Any] | None = None
    description: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None


class AuditEventRead(BaseModel):
    """Schema for reading audit event data."""

    id: str
    actor_type: ActorType
    actor_id: str | None
    actor_email: str | None
    action: str
    action_category: str | None
    entity_type: str
    entity_id: str | None
    metadata: dict[str, Any] | None
    description: str | None
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditEventFilter(BaseModel):
    """Filter parameters for querying audit events."""

    entity_id: str | None = None
    entity_type: str | None = None
    actor_id: str | None = None
    action: str | None = None
    action_category: str | None = None
    limit: int = Field(default=100, le=500)
    offset: int = Field(default=0, ge=0)
