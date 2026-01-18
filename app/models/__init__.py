"""Database models for AcuCare Pathways."""

from app.models.audit_event import ActorType, AuditEvent
from app.models.consent import Consent
from app.models.disposition import DispositionDraft, DispositionFinal, RiskFlag, RiskFlagType, RiskSeverity
from app.models.governance import (
    ApprovalStatus,
    DutyRoster,
    EvidenceExport,
    Incident,
    IncidentCategory,
    IncidentSeverity,
    IncidentStatus,
    LLMSummary,
    LLMSummaryStatus,
    PilotFeedbackResponse,
    PilotFeedbackWindow,
    QuestionnaireVersion,
    RulesetApproval,
)
from app.models.messaging import (
    DeliveryReceipt,
    Message,
    MessageChannel,
    MessageStatus,
    MessageTemplate,
    MessageTemplateType,
)
from app.models.monitoring import (
    CheckInStatus,
    EscalationReason,
    MonitoringAlert,
    MonitoringSchedule,
    WaitingListCheckIn,
)
from app.models.patient import (
    AddressType,
    AppointmentFormatPreference,
    ContactMethod,
    ContactType,
    IdentifierType,
    Patient,
    PatientAddress,
    PatientClinicalProfile,
    PatientContact,
    PatientIdentifier,
    PatientMagicLink,
    PatientPreferences,
    PatientRecordUpdate,
    PreviousTreatment,
    RecordUpdateActorType,
    RecordUpdateSource,
    SexAtBirth,
    SubstanceUseLevel,
)
from app.models.questionnaire import QuestionnaireDefinition, QuestionnaireResponse
from app.models.referral import Referral, ReferralSource, ReferralStatus
from app.models.ruleset import RulesetDefinition
from app.models.scheduling import (
    Appointment,
    AppointmentStatus,
    AppointmentType,
    AvailabilitySlot,
    BookingSource,
    ClinicalSpecialty,
    ClinicianProfile,
    DayOfWeek,
)
from app.models.score import Score, ScoreType, SeverityBand
from app.models.triage_case import TriageCase, TriageCaseStatus, TriageTier
from app.models.user import Permission, Role, User, UserRole

__all__ = [
    # User & Auth
    "User",
    "UserRole",
    "Role",
    "Permission",
    # Patient
    "Patient",
    "PatientAddress",
    "PatientClinicalProfile",
    "PatientContact",
    "PatientIdentifier",
    "PatientMagicLink",
    "PatientPreferences",
    "PatientRecordUpdate",
    # Patient enums
    "AddressType",
    "AppointmentFormatPreference",
    "ContactMethod",
    "ContactType",
    "IdentifierType",
    "PreviousTreatment",
    "RecordUpdateActorType",
    "RecordUpdateSource",
    "SexAtBirth",
    "SubstanceUseLevel",
    # Triage
    "TriageCase",
    "TriageTier",
    "TriageCaseStatus",
    # Questionnaire
    "QuestionnaireDefinition",
    "QuestionnaireResponse",
    # Audit
    "AuditEvent",
    "ActorType",
    # Referral
    "Referral",
    "ReferralSource",
    "ReferralStatus",
    # Consent
    "Consent",
    # Scoring
    "Score",
    "ScoreType",
    "SeverityBand",
    # Rules
    "RulesetDefinition",
    # Risk Flags
    "RiskFlag",
    "RiskFlagType",
    "RiskSeverity",
    # Disposition
    "DispositionDraft",
    "DispositionFinal",
    # Scheduling (Sprint 5)
    "ClinicianProfile",
    "ClinicalSpecialty",
    "AvailabilitySlot",
    "DayOfWeek",
    "AppointmentType",
    "Appointment",
    "AppointmentStatus",
    "BookingSource",
    # Messaging (Sprint 5)
    "MessageTemplate",
    "MessageTemplateType",
    "MessageChannel",
    "Message",
    "MessageStatus",
    "DeliveryReceipt",
    # Monitoring (Sprint 5)
    "WaitingListCheckIn",
    "CheckInStatus",
    "EscalationReason",
    "MonitoringSchedule",
    "MonitoringAlert",
    # Governance (Sprint 6)
    "Incident",
    "IncidentStatus",
    "IncidentSeverity",
    "IncidentCategory",
    "RulesetApproval",
    "ApprovalStatus",
    "DutyRoster",
    "QuestionnaireVersion",
    "EvidenceExport",
    "LLMSummary",
    "LLMSummaryStatus",
    "PilotFeedbackResponse",
    "PilotFeedbackWindow",
]
