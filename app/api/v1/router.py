"""API v1 router aggregating all endpoints."""

from fastapi import APIRouter

from app.api.v1 import (
    admin_friction,
    audit,
    auth_patient,
    auth_staff,
    change_control,
    consent,
    dashboard,
    evidence_export,
    health,
    incidents,
    intake,
    messaging,
    mfa,
    monitoring,
    reporting,
    scheduling,
    triage_cases,
)

api_router = APIRouter()

# Health check
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"],
)

# Authentication
api_router.include_router(
    auth_staff.router,
    prefix="/auth/staff",
    tags=["auth-staff"],
)

api_router.include_router(
    auth_patient.router,
    prefix="/auth/patient",
    tags=["auth-patient"],
)

# MFA
api_router.include_router(
    mfa.router,
    prefix="/auth/staff/mfa",
    tags=["mfa"],
)

# Triage
api_router.include_router(
    triage_cases.router,
    prefix="/triage-cases",
    tags=["triage"],
)

# Audit
api_router.include_router(
    audit.router,
    prefix="/audit",
    tags=["audit"],
)

# Patient intake
api_router.include_router(
    intake.router,
    tags=["intake"],
)

# Consent
api_router.include_router(
    consent.router,
    tags=["consent"],
)

# Staff Dashboard
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["dashboard"],
)

# Scheduling (Sprint 5)
api_router.include_router(
    scheduling.router,
    prefix="/scheduling",
    tags=["scheduling"],
)

# Messaging (Sprint 5)
api_router.include_router(
    messaging.router,
    prefix="/messaging",
    tags=["messaging"],
)

# Monitoring (Sprint 5)
api_router.include_router(
    monitoring.router,
    prefix="/monitoring",
    tags=["monitoring"],
)

# Incidents (Sprint 6)
api_router.include_router(
    incidents.router,
    tags=["incidents"],
)

# Reporting (Sprint 6)
api_router.include_router(
    reporting.router,
    tags=["reporting"],
)

# Evidence Export (Sprint 6)
api_router.include_router(
    evidence_export.router,
    tags=["evidence-export"],
)

# Change Control (Sprint 6)
api_router.include_router(
    change_control.router,
    tags=["change-control"],
)

# Admin Friction Reduction
api_router.include_router(
    admin_friction.router,
    prefix="/admin",
    tags=["admin-friction"],
)
