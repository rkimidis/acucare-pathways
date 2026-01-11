"""Sprint 3: Scoring, rules engine, risk flags, disposition drafts.

Revision ID: 003
Revises: 002
Create Date: 2024-01-03 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add scoring, rules, risk flags, and disposition draft tables."""

    # Add new columns to triage_cases
    op.add_column(
        "triage_cases",
        sa.Column("pathway", sa.String(100), nullable=True),
    )
    op.add_column(
        "triage_cases",
        sa.Column("clinician_review_required", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "triage_cases",
        sa.Column("self_book_allowed", sa.Boolean(), nullable=False, server_default="true"),
    )

    # Create scores table
    op.create_table(
        "scores",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("triage_case_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("questionnaire_response_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("score_type", sa.String(50), nullable=False),
        sa.Column("score_version", sa.String(20), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("max_score", sa.Integer(), nullable=False),
        sa.Column("severity_band", sa.String(50), nullable=False),
        sa.Column("item_scores", postgresql.JSON(), nullable=False),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_scores"),
        sa.ForeignKeyConstraint(
            ["triage_case_id"],
            ["triage_cases.id"],
            name="fk_scores_triage_case_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["questionnaire_response_id"],
            ["questionnaire_responses.id"],
            name="fk_scores_questionnaire_response_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_scores_triage_case_id", "scores", ["triage_case_id"])
    op.create_index("ix_scores_questionnaire_response_id", "scores", ["questionnaire_response_id"])
    op.create_index("ix_scores_score_type", "scores", ["score_type"])

    # Create ruleset_definitions table
    op.create_table(
        "ruleset_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("ruleset_id", sa.String(100), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_json", postgresql.JSON(), nullable=False),
        sa.Column("rule_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evaluation_mode", sa.String(50), nullable=False, server_default="'first_match_wins'"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_ruleset_definitions"),
        sa.UniqueConstraint("content_hash", name="uq_ruleset_definitions_content_hash"),
    )
    op.create_index("ix_ruleset_definitions_ruleset_id", "ruleset_definitions", ["ruleset_id"])
    op.create_index("ix_ruleset_definitions_is_active", "ruleset_definitions", ["is_active"])

    # Create risk_flags table
    op.create_table(
        "risk_flags",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("triage_case_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("rule_id", sa.String(100), nullable=False),
        sa.Column("flag_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("reviewed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_risk_flags"),
        sa.ForeignKeyConstraint(
            ["triage_case_id"],
            ["triage_cases.id"],
            name="fk_risk_flags_triage_case_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name="fk_risk_flags_reviewed_by",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_risk_flags_triage_case_id", "risk_flags", ["triage_case_id"])
    op.create_index("ix_risk_flags_flag_type", "risk_flags", ["flag_type"])

    # Create disposition_drafts table
    op.create_table(
        "disposition_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("triage_case_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("pathway", sa.String(100), nullable=False),
        sa.Column("self_book_allowed", sa.Boolean(), nullable=False),
        sa.Column("clinician_review_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("rules_fired", postgresql.JSON(), nullable=False),
        sa.Column("explanations", postgresql.JSON(), nullable=False),
        sa.Column("ruleset_version", sa.String(50), nullable=False),
        sa.Column("ruleset_hash", sa.String(64), nullable=False),
        sa.Column("evaluation_context", postgresql.JSON(), nullable=True),
        sa.Column("is_applied", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("approved_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_disposition_drafts"),
        sa.ForeignKeyConstraint(
            ["triage_case_id"],
            ["triage_cases.id"],
            name="fk_disposition_drafts_triage_case_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["users.id"],
            name="fk_disposition_drafts_approved_by",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_disposition_drafts_triage_case_id", "disposition_drafts", ["triage_case_id"])
    op.create_index("ix_disposition_drafts_tier", "disposition_drafts", ["tier"])


def downgrade() -> None:
    """Remove Sprint 3 tables and columns."""
    op.drop_table("disposition_drafts")
    op.drop_table("risk_flags")
    op.drop_table("ruleset_definitions")
    op.drop_table("scores")

    op.drop_column("triage_cases", "self_book_allowed")
    op.drop_column("triage_cases", "clinician_review_required")
    op.drop_column("triage_cases", "pathway")
