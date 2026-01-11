"""FastAPI dependency injection utilities."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.services.auth import AuthService
from app.services.rbac import Permission, RBACService

# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict | None:
    """Extract and decode the current JWT token.

    Args:
        credentials: Bearer token credentials

    Returns:
        Decoded token payload or None
    """
    if not credentials:
        return None

    payload = decode_access_token(credentials.credentials)
    return payload


async def get_current_user(
    token: Annotated[dict | None, Depends(get_current_token)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get the current authenticated staff user.

    Args:
        token: Decoded JWT token
        session: Database session

    Returns:
        Authenticated User

    Raises:
        HTTPException: If not authenticated or not a staff user
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token.get("actor_type") != "staff":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff authentication required",
        )

    auth_service = AuthService(session)
    user = await auth_service.get_staff_by_id(token["sub"])

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


async def get_current_patient(
    token: Annotated[dict | None, Depends(get_current_token)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Patient:
    """Get the current authenticated patient.

    Args:
        token: Decoded JWT token
        session: Database session

    Returns:
        Authenticated Patient

    Raises:
        HTTPException: If not authenticated or not a patient
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token.get("actor_type") != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient authentication required",
        )

    auth_service = AuthService(session)
    patient = await auth_service.get_patient_by_id(token["sub"])

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Patient not found",
        )

    if not patient.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient account is disabled",
        )

    return patient


async def get_optional_user(
    token: Annotated[dict | None, Depends(get_current_token)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """Get current user if authenticated, otherwise None.

    Args:
        token: Decoded JWT token
        session: Database session

    Returns:
        User if authenticated, None otherwise
    """
    if not token or token.get("actor_type") != "staff":
        return None

    auth_service = AuthService(session)
    return await auth_service.get_staff_by_id(token["sub"])


def require_permissions(*permissions: Permission):
    """Create a dependency that requires specific permissions.

    Usage:
        @router.get("/", dependencies=[Depends(require_permissions(Permission.TRIAGE_READ))])

    Args:
        permissions: Required permissions (user must have all)

    Returns:
        Dependency function
    """

    async def permission_checker(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if not RBACService.has_all_permissions(user.role, list(permissions)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return permission_checker


def get_client_ip(request: Request) -> str | None:
    """Extract client IP from request.

    Args:
        request: FastAPI request

    Returns:
        Client IP address or None
    """
    # Check for forwarded header (when behind proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Fall back to direct client
    if request.client:
        return request.client.host

    return None


def get_request_id(request: Request) -> str | None:
    """Extract request ID from headers.

    Args:
        request: FastAPI request

    Returns:
        Request ID or None
    """
    return request.headers.get("X-Request-ID")


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentPatient = Annotated[Patient, Depends(get_current_patient)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]
