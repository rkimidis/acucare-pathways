"""Initial schema with all core tables.

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""

    # Permissions table
    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=False, default="general"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_permissions"),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )
    op.create_index("ix_permissions_code", "permissions", ["code"], unique=True)

    # Roles table
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_roles"),
        sa.UniqueConstraint("code", name="uq_roles_code"),
    )
    op.create_index("ix_roles_code", "roles", ["code"], unique=True)

    # Role-Permission association table
    op.create_table(
        "role_permissions",
        sa.Column("role_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name="fk_role_permissions_role_id_roles"
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            name="fk_role_permissions_permission_id_permissions",
        ),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name="pk_role_permissions"),
    )

    # Users table (staff) with MFA fields
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        # MFA fields
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, default=False),
        sa.Column("otp_secret", sa.String(32), nullable=True),
        sa.Column("mfa_backup_codes", sa.Text(), nullable=True),
        # Security fields
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, default=0),
        sa.Column("locked_until", sa.String(50), nullable=True),
        sa.Column("password_changed_at", sa.String(50), nullable=True),
        # Soft delete
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=False), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_is_deleted", "users", ["is_deleted"])

    # User-Role association table
    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_roles_user_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name="fk_user_roles_role_id_roles"
        ),
        sa.PrimaryKeyConstraint("user_id", "role_id", name="pk_user_roles"),
    )

    # Patients table
    op.create_table(
        "patients",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("date_of_birth", sa.DateTime(timezone=True), nullable=True),
        sa.Column("nhs_number", sa.String(20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("privacy_policy_version", sa.String(20), nullable=True),
        # Soft delete
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=False), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_patients"),
        sa.UniqueConstraint("email", name="uq_patients_email"),
        sa.UniqueConstraint("nhs_number", name="uq_patients_nhs_number"),
    )
    op.create_index("ix_patients_email", "patients", ["email"], unique=True)
    op.create_index("ix_patients_is_deleted", "patients", ["is_deleted"])

    # Patient magic links table
    op.create_table(
        "patient_magic_links",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_used", sa.Boolean(), nullable=False, default=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_patient_magic_links"),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_patient_magic_links_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("token", name="uq_patient_magic_links_token"),
    )
    op.create_index(
        "ix_patient_magic_links_token", "patient_magic_links", ["token"], unique=True
    )

    # Questionnaire definitions table
    op.create_table(
        "questionnaire_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("schema", postgresql.JSON(), nullable=False),
        sa.Column("schema_hash", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("display_order", sa.Integer(), nullable=False, default=0),
        sa.Column("previous_version_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_questionnaire_definitions"),
        sa.ForeignKeyConstraint(
            ["previous_version_id"],
            ["questionnaire_definitions.id"],
            name="fk_questionnaire_definitions_previous_version_id",
        ),
    )

    # Referrals table
    op.create_table(
        "referrals",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, default="pending"),
        sa.Column("patient_email", sa.String(255), nullable=False),
        sa.Column("patient_first_name", sa.String(100), nullable=False),
        sa.Column("patient_last_name", sa.String(100), nullable=False),
        sa.Column("patient_phone", sa.String(20), nullable=True),
        sa.Column("patient_dob", sa.String(20), nullable=True),
        sa.Column("referrer_name", sa.String(255), nullable=True),
        sa.Column("referrer_email", sa.String(255), nullable=True),
        sa.Column("referrer_phone", sa.String(20), nullable=True),
        sa.Column("referrer_organization", sa.String(255), nullable=True),
        sa.Column("presenting_complaint", sa.Text(), nullable=True),
        sa.Column("urgency_notes", sa.Text(), nullable=True),
        sa.Column("clinical_history", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("triage_case_id", postgresql.UUID(as_uuid=False), nullable=True),
        # Soft delete
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=False), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_referrals"),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_referrals_patient_id_patients",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name="fk_referrals_reviewed_by_users",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_referrals_patient_id", "referrals", ["patient_id"])
    op.create_index("ix_referrals_source", "referrals", ["source"])
    op.create_index("ix_referrals_status", "referrals", ["status"])
    op.create_index("ix_referrals_patient_email", "referrals", ["patient_email"])
    op.create_index("ix_referrals_is_deleted", "referrals", ["is_deleted"])

    # Triage cases table
    op.create_table(
        "triage_cases",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("tier", sa.String(20), nullable=True),
        sa.Column(
            "questionnaire_version_id", postgresql.UUID(as_uuid=False), nullable=True
        ),
        sa.Column("ruleset_version", sa.String(50), nullable=True),
        sa.Column("ruleset_hash", sa.String(64), nullable=True),
        sa.Column("tier_explanation", postgresql.JSON(), nullable=True),
        sa.Column("assigned_clinician_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("clinical_notes", sa.Text(), nullable=True),
        sa.Column("referral_id", postgresql.UUID(as_uuid=False), nullable=True),
        # Escalation
        sa.Column("escalated_at", sa.String(50), nullable=True),
        sa.Column("escalated_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("escalation_reason", sa.Text(), nullable=True),
        # Soft delete
        sa.Column("is_deleted", sa.Boolean(), nullable=False, default=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=False), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_triage_cases"),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_triage_cases_patient_id_patients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["questionnaire_version_id"],
            ["questionnaire_definitions.id"],
            name="fk_triage_cases_questionnaire_version_id",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_clinician_id"],
            ["users.id"],
            name="fk_triage_cases_assigned_clinician_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["escalated_by"],
            ["users.id"],
            name="fk_triage_cases_escalated_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["referral_id"],
            ["referrals.id"],
            name="fk_triage_cases_referral_id_referrals",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_triage_cases_tier", "triage_cases", ["tier"])
    op.create_index("ix_triage_cases_patient_id", "triage_cases", ["patient_id"])
    op.create_index("ix_triage_cases_is_deleted", "triage_cases", ["is_deleted"])

    # Add FK from referrals to triage_cases (deferred due to circular ref)
    op.create_foreign_key(
        "fk_referrals_triage_case_id_triage_cases",
        "referrals",
        "triage_cases",
        ["triage_case_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Questionnaire responses table
    op.create_table(
        "questionnaire_responses",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("triage_case_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "questionnaire_definition_id", postgresql.UUID(as_uuid=False), nullable=False
        ),
        sa.Column("answers", postgresql.JSON(), nullable=False),
        sa.Column("computed_scores", postgresql.JSON(), nullable=True),
        sa.Column("is_complete", sa.Boolean(), nullable=False, default=False),
        sa.Column("completion_time_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_questionnaire_responses"),
        sa.ForeignKeyConstraint(
            ["triage_case_id"],
            ["triage_cases.id"],
            name="fk_questionnaire_responses_triage_case_id_triage_cases",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["questionnaire_definition_id"],
            ["questionnaire_definitions.id"],
            name="fk_questionnaire_responses_questionnaire_definition_id",
        ),
    )
    op.create_index(
        "ix_questionnaire_responses_triage_case_id",
        "questionnaire_responses",
        ["triage_case_id"],
    )

    # Audit events table (append-only)
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("actor_type", sa.String(50), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("action_category", sa.String(50), nullable=True),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
    )
    op.create_index("ix_audit_events_entity_id", "audit_events", ["entity_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("audit_events")
    op.drop_table("questionnaire_responses")
    op.drop_constraint(
        "fk_referrals_triage_case_id_triage_cases", "referrals", type_="foreignkey"
    )
    op.drop_table("triage_cases")
    op.drop_table("referrals")
    op.drop_table("questionnaire_definitions")
    op.drop_table("patient_magic_links")
    op.drop_table("patients")
    op.drop_table("user_roles")
    op.drop_table("users")
    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_table("permissions")
