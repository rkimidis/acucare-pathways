"""Pydantic schemas for request/response validation."""

from app.schemas.audit_event import AuditEventCreate, AuditEventRead
from app.schemas.auth import (
    MagicLinkRequest,
    MagicLinkResponse,
    PatientLoginRequest,
    StaffLoginRequest,
    TokenResponse,
)
from app.schemas.consent import ConsentCapture, ConsentRead, ConsentStatus
from app.schemas.questionnaire import (
    IntakeDraftSave,
    IntakeResponseSubmit,
    QuestionnaireDefinitionRead,
    QuestionnaireResponseCreate,
    QuestionnaireResponseRead,
    SafetyBannerResponse,
)
from app.schemas.triage_case import (
    TriageCaseCreate,
    TriageCaseRead,
    TriageCaseUpdate,
)

__all__ = [
    "StaffLoginRequest",
    "PatientLoginRequest",
    "MagicLinkRequest",
    "MagicLinkResponse",
    "TokenResponse",
    "TriageCaseCreate",
    "TriageCaseRead",
    "TriageCaseUpdate",
    "AuditEventCreate",
    "AuditEventRead",
    "QuestionnaireDefinitionRead",
    "QuestionnaireResponseCreate",
    "QuestionnaireResponseRead",
    "IntakeResponseSubmit",
    "IntakeDraftSave",
    "SafetyBannerResponse",
    "ConsentCapture",
    "ConsentRead",
    "ConsentStatus",
]
