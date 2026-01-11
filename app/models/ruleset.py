"""Ruleset definition model for version-controlled triage rules."""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class RulesetDefinition(Base, TimestampMixin):
    """Registered ruleset definition with version control.

    Rulesets are loaded from YAML files but registered in the database
    for version tracking and audit trail.
    """

    __tablename__ = "ruleset_definitions"

    # Unique identifier for the ruleset
    ruleset_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    # Semantic version (e.g., "1.0.0")
    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    # SHA256 hash of the YAML content for integrity verification
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
    )
    # Human-readable description
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    # Author/approver of this ruleset version
    author: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    # Whether this is the active version for its ruleset_id
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    # Filename where this ruleset is stored
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    # Full ruleset content as JSON (for audit/comparison)
    content_json: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )
    # Number of rules in this ruleset
    rule_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )
    # Evaluation mode (first_match_wins, all_matches, etc.)
    evaluation_mode: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="first_match_wins",
    )

    def __repr__(self) -> str:
        active = "active" if self.is_active else "inactive"
        return f"<RulesetDefinition {self.ruleset_id} v{self.version} ({active})>"
