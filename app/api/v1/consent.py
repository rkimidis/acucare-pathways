"""Consent capture endpoints for patient portal."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import CurrentPatient, DbSession, get_client_ip
from app.core.config import settings
from app.models.consent import Consent
from app.schemas.consent import ConsentCapture, ConsentRead, ConsentStatus
from app.services.audit import AuditService

router = APIRouter(prefix="/consent", tags=["consent"])


@router.get("/status", response_model=ConsentStatus)
async def get_consent_status(
    patient: CurrentPatient,
    session: DbSession,
) -> ConsentStatus:
    """Get the patient's current consent status.

    Checks if patient has valid consent for current version.
    """
    result = await session.execute(
        select(Consent)
        .where(Consent.patient_id == patient.id)
        .order_by(Consent.agreed_at.desc())
        .limit(1)
    )
    latest_consent = result.scalar_one_or_none()

    if not latest_consent:
        return ConsentStatus(
            has_consented=False,
            current_version=settings.consent_version,
            needs_reconsent=True,
        )

    needs_reconsent = latest_consent.consent_version != settings.consent_version

    return ConsentStatus(
        has_consented=True,
        consent_version=latest_consent.consent_version,
        agreed_at=latest_consent.agreed_at,
        current_version=settings.consent_version,
        needs_reconsent=needs_reconsent,
    )


@router.get("/history", response_model=list[ConsentRead])
async def get_consent_history(
    patient: CurrentPatient,
    session: DbSession,
) -> list[Consent]:
    """Get patient's consent history.

    Returns all consent records for audit purposes.
    """
    result = await session.execute(
        select(Consent)
        .where(Consent.patient_id == patient.id)
        .order_by(Consent.agreed_at.desc())
    )
    return list(result.scalars().all())


@router.post("/capture", response_model=ConsentRead, status_code=status.HTTP_201_CREATED)
async def capture_consent(
    body: ConsentCapture,
    patient: CurrentPatient,
    session: DbSession,
    request: Request,
) -> Consent:
    """Capture patient consent.

    Creates an immutable consent record with timestamp and version.
    Required consent items must be accepted.
    """
    # Validate required consent items
    required_items = ["data_processing", "privacy_policy"]
    missing_required = []
    for item in required_items:
        if item not in body.consent_items or not body.consent_items[item]:
            missing_required.append(item)

    if missing_required:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Required consent items must be accepted",
                "missing": missing_required,
            },
        )

    now = datetime.now(timezone.utc)
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent")

    # Create consent record
    consent = Consent(
        patient_id=patient.id,
        consent_version=settings.consent_version,
        channels=body.channels,
        agreed_at=now,
        ip_address=client_ip,
        user_agent=user_agent,
        consent_items=body.consent_items,
    )
    session.add(consent)
    await session.commit()
    await session.refresh(consent)

    # Update patient's consent tracking fields
    patient.consent_given_at = now
    patient.privacy_policy_version = settings.consent_version
    await session.commit()

    # Audit event
    audit_service = AuditService(session)
    await audit_service.log_event(
        actor_type="patient",
        actor_id=patient.id,
        actor_email=patient.email,
        action="consent_captured",
        action_category="clinical",
        entity_type="consent",
        entity_id=consent.id,
        metadata={
            "consent_version": settings.consent_version,
            "channels": body.channels,
            "consent_items": list(body.consent_items.keys()),
        },
        ip_address=client_ip,
        user_agent=user_agent,
    )

    return consent
