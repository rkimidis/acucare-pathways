"""RBAC Middleware for enforcing permissions on staff endpoints."""

import logging
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.security import decode_access_token
from app.services.rbac import ROLE_PERMISSIONS, Permission

logger = logging.getLogger(__name__)


# Endpoint to required permissions mapping
ENDPOINT_PERMISSIONS: dict[tuple[str, str], list[Permission]] = {
    # Triage endpoints
    ("GET", "/api/v1/triage-cases"): [Permission.TRIAGE_READ],
    ("GET", "/api/v1/triage-cases/{case_id}"): [Permission.TRIAGE_READ],
    ("POST", "/api/v1/triage-cases"): [Permission.TRIAGE_WRITE],
    ("PATCH", "/api/v1/triage-cases/{case_id}"): [Permission.TRIAGE_WRITE],
    # Audit endpoints
    ("GET", "/api/v1/audit/events"): [Permission.AUDIT_READ],
    ("GET", "/api/v1/audit/events/{entity_type}/{entity_id}"): [Permission.AUDIT_READ],
    # User management (admin only)
    ("GET", "/api/v1/users"): [Permission.USERS_READ],
    ("POST", "/api/v1/users"): [Permission.USERS_WRITE],
    ("PATCH", "/api/v1/users/{user_id}"): [Permission.USERS_WRITE],
    # Patient management
    ("GET", "/api/v1/patients"): [Permission.PATIENTS_READ],
    ("POST", "/api/v1/patients"): [Permission.PATIENTS_WRITE],
    ("PATCH", "/api/v1/patients/{patient_id}"): [Permission.PATIENTS_WRITE],
    # Referrals
    ("GET", "/api/v1/referrals"): [Permission.TRIAGE_READ],
    ("POST", "/api/v1/referrals"): [Permission.TRIAGE_WRITE],
    ("PATCH", "/api/v1/referrals/{referral_id}"): [Permission.TRIAGE_WRITE],
}

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = {
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/health",
    "/api/v1/health/ready",
    "/api/v1/auth/staff/login",
    "/api/v1/auth/patient/request-magic-link",
    "/api/v1/auth/patient/login",
    "/api/v1/auth/staff/mfa/verify",
}


def normalize_path(path: str) -> str:
    """Normalize path by replacing UUIDs with placeholders."""
    import re

    # Replace UUID patterns with {param}
    uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    normalized = re.sub(uuid_pattern, "{id}", path, flags=re.IGNORECASE)

    # Also handle short UUIDs (first 8 chars)
    short_uuid = r"/[0-9a-f]{8}(?=/|$)"
    normalized = re.sub(short_uuid, "/{id}", normalized, flags=re.IGNORECASE)

    return normalized


def get_required_permissions(method: str, path: str) -> list[Permission] | None:
    """Get required permissions for an endpoint.

    Returns None if endpoint is public or not mapped.
    """
    normalized = normalize_path(path)

    # Check direct match first
    key = (method, normalized)
    if key in ENDPOINT_PERMISSIONS:
        return ENDPOINT_PERMISSIONS[key]

    # Check pattern matches
    for (ep_method, ep_path), perms in ENDPOINT_PERMISSIONS.items():
        if ep_method != method:
            continue

        # Simple pattern matching for parameterized paths
        ep_parts = ep_path.split("/")
        path_parts = normalized.split("/")

        if len(ep_parts) != len(path_parts):
            continue

        match = True
        for ep_part, path_part in zip(ep_parts, path_parts, strict=False):
            if ep_part.startswith("{") and ep_part.endswith("}"):
                continue  # Parameter placeholder matches anything
            if ep_part != path_part:
                match = False
                break

        if match:
            return perms

    return None


class RBACMiddleware(BaseHTTPMiddleware):
    """Middleware for enforcing RBAC on staff endpoints."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        """Process request and enforce RBAC."""
        path = request.url.path
        method = request.method

        # Skip public endpoints
        if path in PUBLIC_ENDPOINTS:
            return await call_next(request)

        # Skip patient portal endpoints (handled separately)
        if path.startswith("/api/v1/portal/"):
            return await call_next(request)

        # Get required permissions
        required_perms = get_required_permissions(method, path)

        if required_perms is None:
            # No permission mapping - let endpoint handle auth
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                content='{"detail":"Authentication required"}',
                status_code=401,
                media_type="application/json",
            )

        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)

        if not payload:
            return Response(
                content='{"detail":"Invalid or expired token"}',
                status_code=401,
                media_type="application/json",
            )

        # Check actor type
        actor_type = payload.get("actor_type")
        if actor_type != "staff":
            return Response(
                content='{"detail":"Staff authentication required"}',
                status_code=403,
                media_type="application/json",
            )

        # Get user role and check permissions
        role_str = payload.get("role")
        if not role_str:
            return Response(
                content='{"detail":"Invalid token: missing role"}',
                status_code=403,
                media_type="application/json",
            )

        try:
            from app.models.user import UserRole

            user_role = UserRole(role_str)
        except ValueError:
            return Response(
                content='{"detail":"Invalid role"}',
                status_code=403,
                media_type="application/json",
            )

        # Check if user has required permissions
        role_permissions = ROLE_PERMISSIONS.get(user_role, set())
        has_permission = any(perm in role_permissions for perm in required_perms)

        if not has_permission:
            logger.warning(
                f"Permission denied: user={payload.get('sub')} "
                f"role={role_str} required={[p.value for p in required_perms]}"
            )
            return Response(
                content='{"detail":"Insufficient permissions"}',
                status_code=403,
                media_type="application/json",
            )

        # Permission granted - continue to endpoint
        return await call_next(request)
