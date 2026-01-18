"""SQLAlchemy 2.0 declarative base configuration."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, MetaData
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column, registry

# Naming convention for constraints (important for migrations)
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Shared registry for all models
_mapper_registry = registry(metadata=MetaData(naming_convention=convention))


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models with UUID id."""

    registry = _mapper_registry
    metadata = _mapper_registry.metadata

    # Common columns for all models
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        # Convert CamelCase to snake_case
        name = cls.__name__
        return "".join(["_" + c.lower() if c.isupper() else c for c in name]).lstrip("_")


class BaseNoId(DeclarativeBase):
    """Base class for models that don't use a standard UUID id column.

    Use this for tables where the primary key is a foreign key (1:1 relationships).
    """

    registry = _mapper_registry
    metadata = _mapper_registry.metadata


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )


class SoftDeleteMixin:
    """Mixin for soft delete support.

    Clinical data should never be hard-deleted for compliance reasons.
    """

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    deleted_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )

    def soft_delete(self, deleted_by_id: str | None = None) -> None:
        """Mark record as deleted without removing from database."""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        self.deleted_by = deleted_by_id


class AuditMixin:
    """Mixin for audit fields."""

    created_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )
    updated_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)
