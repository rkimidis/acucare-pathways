"""Staff authentication endpoints."""

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import DbSession, get_client_ip
from app.core.config import settings
from app.models.audit_event import ActorType
from app.schemas.auth import StaffLoginRequest, TokenResponse
from app.services.audit import write_audit_event
from app.services.auth import AuthService

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Staff login",
    description="Authenticate staff user with email and password",
)
async def staff_login(
    request: Request,
    credentials: StaffLoginRequest,
    session: DbSession,
) -> TokenResponse:
    """Authenticate staff user and return JWT token.

    Args:
        request: FastAPI request
        credentials: Email and password
        session: Database session

    Returns:
        JWT access token

    Raises:
        HTTPException: If credentials are invalid
    """
    auth_service = AuthService(session)
    user = await auth_service.authenticate_staff(
        email=credentials.email,
        password=credentials.password,
    )

    if not user:
        # Log failed attempt
        await write_audit_event(
            session=session,
            actor_type=ActorType.SYSTEM,
            actor_id=None,
            action="login_failed",
            action_category="auth",
            entity_type="user",
            entity_id=None,
            metadata={"email": credentials.email, "reason": "invalid_credentials"},
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create token
    access_token = await auth_service.create_staff_token(user)

    # Log successful login
    await write_audit_event(
        session=session,
        actor_type=ActorType.STAFF,
        actor_id=user.id,
        actor_email=user.email,
        action="login_success",
        action_category="auth",
        entity_type="user",
        entity_id=user.id,
        metadata={"role": user.role.value if hasattr(user.role, 'value') else user.role},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
    )
