"""MFA (Multi-Factor Authentication) endpoints for staff.

Note: This is a placeholder implementation. Actual OTP verification
is stubbed for development. In production, integrate with a proper
TOTP library like pyotp.
"""

import secrets
from urllib.parse import quote
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession, get_client_ip
from app.models.audit_event import ActorType
from app.models.user import User
from app.services.audit import write_audit_event

router = APIRouter()


class MFASetupResponse(BaseModel):
    """Response for MFA setup initiation."""

    secret: str
    provisioning_uri: str
    backup_codes: list[str]


class MFAEnableRequest(BaseModel):
    """Request to enable MFA after setup."""

    otp_code: str = Field(min_length=6, max_length=6)


class MFAVerifyRequest(BaseModel):
    """Request to verify MFA during login."""

    user_id: str
    otp_code: str = Field(min_length=6, max_length=6)


class MFADisableRequest(BaseModel):
    """Request to disable MFA."""

    password: str
    otp_code: str = Field(min_length=6, max_length=6)


class MFAStatusResponse(BaseModel):
    """MFA status for current user."""

    mfa_enabled: bool
    has_backup_codes: bool


def generate_otp_secret() -> str:
    """Generate a random OTP secret.

    In production, use pyotp.random_base32()
    """
    return secrets.token_hex(16).upper()[:32]


def generate_backup_codes(count: int = 10) -> list[str]:
    """Generate backup codes for MFA recovery."""
    return [secrets.token_hex(4).upper() for _ in range(count)]


def generate_provisioning_uri(secret: str, email: str) -> str:
    """Generate TOTP provisioning URI for authenticator apps.

    In production, use pyotp.TOTP(secret).provisioning_uri()
    """
    # Placeholder URI format
    issuer = "AcuCare Pathways"
    label = quote(f"{issuer}:{email}")
    issuer_param = quote(issuer)
    return f"otpauth://totp/{label}?secret={secret}&issuer={issuer_param}"


def verify_otp(secret: str, code: str) -> bool:
    """Verify OTP code against secret.

    STUB: In production, use pyotp.TOTP(secret).verify(code)
    For development, accepts any 6-digit code or "000000" as valid.
    """
    # Development stub - always accept "000000" or any 6-digit code
    if code == "000000":
        return True
    # In production, implement actual TOTP verification
    return len(code) == 6 and code.isdigit()


@router.get(
    "/status",
    response_model=MFAStatusResponse,
    summary="Get MFA status",
    description="Check if MFA is enabled for the current user",
)
async def get_mfa_status(user: CurrentUser) -> MFAStatusResponse:
    """Get MFA status for current user."""
    return MFAStatusResponse(
        mfa_enabled=user.mfa_enabled,
        has_backup_codes=user.mfa_backup_codes is not None,
    )


@router.post(
    "/setup",
    response_model=MFASetupResponse,
    summary="Setup MFA",
    description="Initialize MFA setup and get secret + backup codes",
)
async def setup_mfa(
    request: Request,
    user: CurrentUser,
    session: DbSession,
) -> MFASetupResponse:
    """Initialize MFA setup for current user.

    Returns secret and backup codes. User must call /enable
    with a valid OTP to complete setup.
    """
    if user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled",
        )

    # Generate new secret
    secret = generate_otp_secret()
    backup_codes = generate_backup_codes()

    # Store secret (not enabled yet)
    user.otp_secret = secret
    # Store backup codes as JSON (in production, hash these)
    import json

    user.mfa_backup_codes = json.dumps(backup_codes)

    await session.commit()

    # Log setup initiation
    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="mfa_setup_initiated",
        action_category="auth",
        entity_type="user",
        entity_id=user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    return MFASetupResponse(
        secret=secret,
        provisioning_uri=generate_provisioning_uri(secret, user.email),
        backup_codes=backup_codes,
    )


@router.post(
    "/enable",
    status_code=status.HTTP_200_OK,
    summary="Enable MFA",
    description="Complete MFA setup by verifying OTP code",
)
async def enable_mfa(
    request: Request,
    body: MFAEnableRequest,
    user: CurrentUser,
    session: DbSession,
) -> dict:
    """Enable MFA after verifying OTP code.

    User must have called /setup first to get their secret.
    """
    if user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled",
        )

    if not user.otp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup not initiated. Call /setup first",
        )

    # Verify OTP
    if not verify_otp(user.otp_secret, body.otp_code):
        await write_audit_event(
            session=session,
            actor_type=ActorType.STAFF,
            actor_id=user.id,
            actor_email=user.email,
            action="mfa_enable_failed",
            action_category="auth",
            entity_type="user",
            entity_id=user.id,
            metadata={"reason": "invalid_otp"},
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OTP code",
        )

    # Enable MFA
    user.mfa_enabled = True
    await session.commit()

    # Log enablement
    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="mfa_enabled",
        action_category="auth",
        entity_type="user",
        entity_id=user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    return {"message": "MFA enabled successfully"}


@router.post(
    "/verify",
    status_code=status.HTTP_200_OK,
    summary="Verify MFA",
    description="Verify OTP code during login (second factor)",
)
async def verify_mfa(
    request: Request,
    body: MFAVerifyRequest,
    session: DbSession,
) -> dict:
    """Verify MFA code during login flow.

    Called after password verification if user has MFA enabled.
    """
    # Get user
    result = await session.execute(select(User).where(User.id == body.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.mfa_enabled or not user.otp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA not enabled for this user",
        )

    # Verify OTP
    if not verify_otp(user.otp_secret, body.otp_code):
        # Log failed attempt
        await write_audit_event(
            session=session,
            actor_type=ActorType.STAFF,
            actor_id=user.id,
            actor_email=user.email,
            action="mfa_verify_failed",
            action_category="auth",
            entity_type="user",
            entity_id=user.id,
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OTP code",
        )

    # Log successful verification
    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="mfa_verify_success",
        action_category="auth",
        entity_type="user",
        entity_id=user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    return {"message": "MFA verification successful", "verified": True}


@router.post(
    "/disable",
    status_code=status.HTTP_200_OK,
    summary="Disable MFA",
    description="Disable MFA (requires password and current OTP)",
)
async def disable_mfa(
    request: Request,
    body: MFADisableRequest,
    user: CurrentUser,
    session: DbSession,
) -> dict:
    """Disable MFA for current user.

    Requires password and valid OTP for security.
    """
    if not user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled",
        )

    # Verify password
    from app.core.security import verify_password

    if not verify_password(body.password, user.hashed_password):
        await write_audit_event(
            session=session,
            actor_type=ActorType.STAFF,
            actor_id=user.id,
            actor_email=user.email,
            action="mfa_disable_failed",
            action_category="auth",
            entity_type="user",
            entity_id=user.id,
            metadata={"reason": "invalid_password"},
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )

    # Verify OTP
    if not user.otp_secret or not verify_otp(user.otp_secret, body.otp_code):
        await write_audit_event(
            session=session,
            actor_type=ActorType.STAFF,
            actor_id=user.id,
            actor_email=user.email,
            action="mfa_disable_failed",
            action_category="auth",
            entity_type="user",
            entity_id=user.id,
            metadata={"reason": "invalid_otp"},
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OTP code",
        )

    # Disable MFA
    user.mfa_enabled = False
    user.otp_secret = None
    user.mfa_backup_codes = None
    await session.commit()

    # Log disablement
    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="mfa_disabled",
        action_category="auth",
        entity_type="user",
        entity_id=user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    return {"message": "MFA disabled successfully"}
