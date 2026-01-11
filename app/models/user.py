"""Staff user model with MFA support."""

from enum import Enum

from sqlalchemy import Boolean, Column, ForeignKey, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin


class UserRole(str, Enum):
    """Staff user roles for RBAC."""

    ADMIN = "admin"
    CLINICAL_LEAD = "clinical_lead"
    CLINICIAN = "clinician"
    RECEPTIONIST = "receptionist"
    READONLY = "readonly"


# Association table for many-to-many user-role relationship
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", UUID(as_uuid=False), ForeignKey("users.id"), primary_key=True),
    Column("role_id", UUID(as_uuid=False), ForeignKey("roles.id"), primary_key=True),
)

# Association table for many-to-many role-permission relationship
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", UUID(as_uuid=False), ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", UUID(as_uuid=False), ForeignKey("permissions.id"), primary_key=True),
)


class Permission(Base, TimestampMixin):
    """Permission model for granular access control."""

    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="general",
    )

    # Relationships
    roles: Mapped[list["Role"]] = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions",
    )

    def __repr__(self) -> str:
        return f"<Permission {self.code}>"


class Role(Base, TimestampMixin):
    """Role model for RBAC."""

    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary=user_roles,
        back_populates="roles_rel",
    )

    def has_permission(self, permission_code: str) -> bool:
        """Check if role has a specific permission."""
        return any(p.code == permission_code for p in self.permissions)

    def __repr__(self) -> str:
        return f"<Role {self.code}>"


class User(Base, TimestampMixin, SoftDeleteMixin):
    """Staff user model for clinic personnel.

    Represents clinic staff including administrators, clinicians,
    and support staff. Not to be confused with patients.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    # Legacy role field (kept for backward compatibility)
    role: Mapped[UserRole] = mapped_column(
        String(50),
        default=UserRole.READONLY,
        nullable=False,
    )
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # MFA fields
    mfa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    otp_secret: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    mfa_backup_codes: Mapped[str | None] = mapped_column(
        Text,  # JSON array of hashed backup codes
        nullable=True,
    )

    # Account security
    failed_login_attempts: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
    )
    locked_until: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    password_changed_at: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    # Relationships
    roles_rel: Mapped[list["Role"]] = relationship(
        "Role",
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",
    )

    @property
    def full_name(self) -> str:
        """Return user's full name."""
        return f"{self.first_name} {self.last_name}"

    def has_permission(self, permission_code: str) -> bool:
        """Check if user has a specific permission through any of their roles."""
        return any(role.has_permission(permission_code) for role in self.roles_rel)

    def get_all_permissions(self) -> set[str]:
        """Get all permission codes for this user."""
        permissions: set[str] = set()
        for role in self.roles_rel:
            for perm in role.permissions:
                permissions.add(perm.code)
        return permissions

    def __repr__(self) -> str:
        return f"<User {self.email} ({self.role})>"
