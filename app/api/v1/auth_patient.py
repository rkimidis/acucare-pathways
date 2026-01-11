"""Patient authentication endpoints."""

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import DbSession, get_client_ip
from app.core.config import settings
from app.models.audit_event import ActorType
from app.schemas.auth import (
    MagicLinkRequest,
    MagicLinkResponse,
    PatientLoginRequest,
    TokenResponse,
)
from app.services.audit import write_audit_event
from app.services.auth import AuthService

router = APIRouter()


@router.post(
    "/request-magic-link",
    response_model=MagicLinkResponse,
    status_code=status.HTTP_200_OK,
    summary="Request magic link",
    description="Request a magic link for patient authentication (dev returns token, prod sends email)",
)
async def request_magic_link(
    request: Request,
    body: MagicLinkRequest,
    session: DbSession,
) -> MagicLinkResponse:
    """Request a magic link for patient authentication.

    In development, returns the token directly.
    In production, would send an email (not implemented in scaffold).

    Args:
        request: FastAPI request
        body: Email address to send link to
        session: Database session

    Returns:
        Magic link details (token in dev mode)

    Raises:
        HTTPException: If patient not found
    """
    auth_service = AuthService(session)
    patient = await auth_service.get_patient_by_email(body.email)

    if not patient:
        # Don't reveal whether email exists for security
        # Log the attempt
        await write_audit_event(
            session=session,
            actor_type=ActorType.SYSTEM,
            actor_id=None,
            action="magic_link_request_unknown_email",
            action_category="auth",
            entity_type="patient",
            entity_id=None,
            metadata={"email": body.email},
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )

        # Return success anyway to prevent email enumeration
        return MagicLinkResponse(
            token="",  # Empty in this case
            expires_in_minutes=settings.patient_magic_link_ttl_minutes,
            message="If the email exists, a magic link has been sent",
        )

    if not patient.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient account is disabled",
        )

    # Create magic link
    magic_link = await auth_service.create_magic_link(patient)

    # Log the request
    await write_audit_event(
        session=session,
        actor_type=ActorType.PATIENT,
        actor_id=patient.id,
        actor_email=patient.email,
        action="magic_link_requested",
        action_category="auth",
        entity_type="patient_magic_link",
        entity_id=magic_link.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    # In dev mode, return the token directly
    # In prod, this would trigger an email send
    if settings.is_dev:
        return MagicLinkResponse(
            token=magic_link.token,
            expires_in_minutes=settings.patient_magic_link_ttl_minutes,
            message="Magic link token (dev mode only)",
        )

    return MagicLinkResponse(
        token="",  # Don't expose in non-dev
        expires_in_minutes=settings.patient_magic_link_ttl_minutes,
        message="If the email exists, a magic link has been sent",
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Patient login",
    description="Authenticate patient with magic link token",
)
async def patient_login(
    request: Request,
    body: PatientLoginRequest,
    session: DbSession,
) -> TokenResponse:
    """Authenticate patient using magic link token.

    Args:
        request: FastAPI request
        body: Magic link token
        session: Database session

    Returns:
        JWT access token

    Raises:
        HTTPException: If token is invalid or expired
    """
    auth_service = AuthService(session)
    magic_link = await auth_service.validate_magic_link(body.token)

    if not magic_link:
        # Log failed attempt
        await write_audit_event(
            session=session,
            actor_type=ActorType.SYSTEM,
            actor_id=None,
            action="magic_link_login_failed",
            action_category="auth",
            entity_type="patient_magic_link",
            entity_id=None,
            metadata={"reason": "invalid_or_expired_token"},
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired magic link",
        )

    # Consume the token
    consumed = await auth_service.consume_magic_link(magic_link)
    if not consumed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Magic link already used",
        )

    # Get patient
    patient = await auth_service.get_patient_by_id(magic_link.patient_id)
    if not patient or not patient.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient account is disabled",
        )

    # Create token
    access_token = await auth_service.create_patient_token(patient)

    # Log successful login
    await write_audit_event(
        session=session,
        actor_type=ActorType.PATIENT,
        actor_id=patient.id,
        actor_email=patient.email,
        action="login_success",
        action_category="auth",
        entity_type="patient",
        entity_id=patient.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )
