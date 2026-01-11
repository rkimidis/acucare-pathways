"""Sprint 4: Dashboard, disposition finals, SLA timers, triage notes.

Revision ID: 004
Revises: 003
Create Date: 2024-01-04 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add disposition finals, SLA timers, and triage note fields."""

    # Add SLA timer fields to triage_cases
    op.add_column(
        "triage_cases",
        sa.Column("triaged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "triage_cases",
        sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "triage_cases",
        sa.Column("sla_target_minutes", sa.Integer(), nullable=True),
    )
    op.add_column(
        "triage_cases",
        sa.Column("sla_breached", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "triage_cases",
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "triage_cases",
        sa.Column(
            "reviewed_by",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Add triage note fields to triage_cases
    op.add_column(
        "triage_cases",
        sa.Column("triage_note_url", sa.String(500), nullable=True),
    )
    op.add_column(
        "triage_cases",
        sa.Column("triage_note_generated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create index on sla_deadline for efficient queue queries
    op.create_index(
        "ix_triage_cases_sla_deadline",
        "triage_cases",
        ["sla_deadline"],
    )

    # Create disposition_finals table
    op.create_table(
        "disposition_finals",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "triage_case_id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column(
            "draft_id",
            postgresql.UUID(as_uuid=False),
            nullable=True,
        ),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("pathway", sa.String(100), nullable=False),
        sa.Column("self_book_allowed", sa.Boolean(), nullable=False),
        sa.Column("is_override", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("original_tier", sa.String(20), nullable=True),
        sa.Column("original_pathway", sa.String(100), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column(
            "clinician_id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clinical_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_disposition_finals"),
        sa.ForeignKeyConstraint(
            ["triage_case_id"],
            ["triage_cases.id"],
            name="fk_disposition_finals_triage_case_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["draft_id"],
            ["disposition_drafts.id"],
            name="fk_disposition_finals_draft_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["clinician_id"],
            ["users.id"],
            name="fk_disposition_finals_clinician_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "triage_case_id",
            name="uq_disposition_finals_triage_case_id",
        ),
    )

    # Create indexes for disposition_finals
    op.create_index(
        "ix_disposition_finals_triage_case_id",
        "disposition_finals",
        ["triage_case_id"],
    )
    op.create_index(
        "ix_disposition_finals_tier",
        "disposition_finals",
        ["tier"],
    )
    op.create_index(
        "ix_disposition_finals_clinician_id",
        "disposition_finals",
        ["clinician_id"],
    )


def downgrade() -> None:
    """Remove Sprint 4 tables and columns."""

    # Drop disposition_finals table
    op.drop_table("disposition_finals")

    # Remove SLA timer indexes
    op.drop_index("ix_triage_cases_sla_deadline", table_name="triage_cases")

    # Remove triage note fields from triage_cases
    op.drop_column("triage_cases", "triage_note_generated_at")
    op.drop_column("triage_cases", "triage_note_url")

    # Remove SLA timer fields from triage_cases
    op.drop_column("triage_cases", "reviewed_by")
    op.drop_column("triage_cases", "reviewed_at")
    op.drop_column("triage_cases", "sla_breached")
    op.drop_column("triage_cases", "sla_target_minutes")
    op.drop_column("triage_cases", "sla_deadline")
    op.drop_column("triage_cases", "triaged_at")
