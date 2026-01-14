"""Role-Based Access Control (RBAC) service.

Implements least-privilege access control for UK GDPR compliance.
"""

from enum import Enum
from typing import Annotated

from fastapi import Depends, HTTPException, status

from app.models.user import UserRole


class Permission(str, Enum):
    """Available permissions in the system."""

    # Patient management
    PATIENTS_READ = "patients:read"
    PATIENTS_WRITE = "patients:write"
    IDENTIFIERS_WRITE = "identifiers:write"  # Admin-only: add/modify patient identifiers

    # Triage management
    TRIAGE_READ = "triage:read"
    TRIAGE_WRITE = "triage:write"
    TRIAGE_ASSIGN = "triage:assign"
    TRIAGE_ESCALATE = "triage:escalate"

    # Disposition management
    DISPOSITION_CONFIRM = "disposition:confirm"  # Confirm draft disposition
    DISPOSITION_OVERRIDE = "disposition:override"  # Override tier/pathway (requires rationale)
    DISPOSITION_EXPORT = "disposition:export"  # Export triage note PDF

    # Clinical operations
    CLINICAL_NOTES_READ = "clinical:notes:read"
    CLINICAL_NOTES_WRITE = "clinical:notes:write"

    # Questionnaire management
    QUESTIONNAIRE_READ = "questionnaire:read"
    QUESTIONNAIRE_WRITE = "questionnaire:write"

    # Audit access
    AUDIT_READ = "audit:read"

    # User management
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"

    # System administration
    ADMIN_ALL = "admin:all"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.ADMIN: {
        Permission.PATIENTS_READ,
        Permission.PATIENTS_WRITE,
        Permission.IDENTIFIERS_WRITE,  # Admin-only: manage patient identifiers
        Permission.TRIAGE_READ,
        Permission.TRIAGE_WRITE,
        Permission.TRIAGE_ASSIGN,
        Permission.TRIAGE_ESCALATE,
        Permission.DISPOSITION_CONFIRM,
        Permission.DISPOSITION_OVERRIDE,
        Permission.DISPOSITION_EXPORT,
        Permission.CLINICAL_NOTES_READ,
        Permission.CLINICAL_NOTES_WRITE,
        Permission.QUESTIONNAIRE_READ,
        Permission.QUESTIONNAIRE_WRITE,
        Permission.AUDIT_READ,
        Permission.USERS_READ,
        Permission.USERS_WRITE,
        Permission.ADMIN_ALL,
    },
    UserRole.CLINICAL_LEAD: {
        Permission.PATIENTS_READ,
        Permission.PATIENTS_WRITE,
        Permission.TRIAGE_READ,
        Permission.TRIAGE_WRITE,
        Permission.TRIAGE_ASSIGN,
        Permission.TRIAGE_ESCALATE,
        Permission.DISPOSITION_CONFIRM,
        Permission.DISPOSITION_OVERRIDE,
        Permission.DISPOSITION_EXPORT,
        Permission.CLINICAL_NOTES_READ,
        Permission.CLINICAL_NOTES_WRITE,
        Permission.QUESTIONNAIRE_READ,
        Permission.QUESTIONNAIRE_WRITE,
        Permission.AUDIT_READ,
        Permission.USERS_READ,
    },
    UserRole.CLINICIAN: {
        Permission.PATIENTS_READ,
        Permission.PATIENTS_WRITE,  # Clinicians can edit patient details during pilot
        Permission.TRIAGE_READ,
        Permission.TRIAGE_WRITE,
        Permission.DISPOSITION_CONFIRM,
        Permission.DISPOSITION_OVERRIDE,
        Permission.DISPOSITION_EXPORT,
        Permission.CLINICAL_NOTES_READ,
        Permission.CLINICAL_NOTES_WRITE,
        Permission.QUESTIONNAIRE_READ,
    },
    UserRole.RECEPTIONIST: {
        # NOTE: Receptionists can view but NOT override dispositions
        Permission.PATIENTS_READ,
        Permission.PATIENTS_WRITE,
        Permission.TRIAGE_READ,
        Permission.QUESTIONNAIRE_READ,
    },
    UserRole.READONLY: {
        Permission.PATIENTS_READ,
        Permission.TRIAGE_READ,
        Permission.QUESTIONNAIRE_READ,
    },
}


class RBACService:
    """Service for checking role-based permissions."""

    @staticmethod
    def get_permissions(role: UserRole) -> set[Permission]:
        """Get all permissions for a role.

        Args:
            role: User role

        Returns:
            Set of permissions granted to the role
        """
        return ROLE_PERMISSIONS.get(role, set())

    @staticmethod
    def has_permission(role: UserRole, permission: Permission) -> bool:
        """Check if a role has a specific permission.

        Args:
            role: User role to check
            permission: Permission to verify

        Returns:
            True if role has permission
        """
        permissions = ROLE_PERMISSIONS.get(role, set())
        return permission in permissions

    @staticmethod
    def has_any_permission(role: UserRole, permissions: list[Permission]) -> bool:
        """Check if a role has any of the specified permissions.

        Args:
            role: User role to check
            permissions: List of permissions (any match succeeds)

        Returns:
            True if role has at least one permission
        """
        role_permissions = ROLE_PERMISSIONS.get(role, set())
        return any(p in role_permissions for p in permissions)

    @staticmethod
    def has_all_permissions(role: UserRole, permissions: list[Permission]) -> bool:
        """Check if a role has all specified permissions.

        Args:
            role: User role to check
            permissions: List of permissions (all must match)

        Returns:
            True if role has all permissions
        """
        role_permissions = ROLE_PERMISSIONS.get(role, set())
        return all(p in role_permissions for p in permissions)


def require_permission(permission: Permission):
    """FastAPI dependency factory for permission checks.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_permission(Permission.ADMIN_ALL))])
        async def admin_endpoint():
            ...

    Args:
        permission: Required permission

    Returns:
        Dependency function that raises 403 if permission not met
    """

    async def check_permission(role: str | None = None) -> None:
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        try:
            user_role = UserRole(role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid role",
            )

        if not RBACService.has_permission(user_role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value}",
            )

    return check_permission


def require_any_permission(*permissions: Permission):
    """FastAPI dependency factory requiring any of the specified permissions.

    Args:
        permissions: Permissions where at least one must be present

    Returns:
        Dependency function
    """

    async def check_permissions(role: str | None = None) -> None:
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        try:
            user_role = UserRole(role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid role",
            )

        if not RBACService.has_any_permission(user_role, list(permissions)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )

    return check_permissions
