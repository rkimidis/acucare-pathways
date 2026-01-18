"""Cancellation and rescheduling with tier-based rules.

Revision ID: 012
Revises: 011
Create Date: 2024-01-12 00:00:00.000000

Adds:
- Patient behavior tracking fields (cancellation_count_90d, no_show_count_90d)
- Appointment reschedule tracking (reschedule_count, rescheduled_from_id)
- CancellationRequest table for request-only flows (AMBER/RED tiers, within 24h)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: Union[str, None] = "007_audit_immutability"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cancellation/rescheduling tables and columns."""

    # ========================================================================
    # PATIENT BEHAVIOR TRACKING
    # ========================================================================

    # Add behavior tracking columns to patients table
    op.add_column(
        "patients",
        sa.Column(
            "cancellation_count_90d",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "patients",
        sa.Column(
            "no_show_count_90d",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "patients",
        sa.Column(
            "last_behavior_reset_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # ========================================================================
    # APPOINTMENT RESCHEDULE TRACKING
    # ========================================================================

    # Add reschedule tracking to appointments table
    op.add_column(
        "appointments",
        sa.Column(
            "reschedule_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "appointments",
        sa.Column(
            "rescheduled_from_id",
            postgresql.UUID(as_uuid=False),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_appointments_rescheduled_from",
        "appointments",
        "appointments",
        ["rescheduled_from_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_appointments_rescheduled_from_id",
        "appointments",
        ["rescheduled_from_id"],
    )

    # ========================================================================
    # CANCELLATION REQUESTS TABLE
    # ========================================================================

    op.create_table(
        "cancellation_requests",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "appointment_id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column(
            "triage_case_id",
            postgresql.UUID(as_uuid=False),
            nullable=True,
        ),
        # Request type: 'cancel' or 'reschedule'
        sa.Column("request_type", sa.String(20), nullable=False),
        # Tier at time of request (for audit)
        sa.Column("tier_at_request", sa.String(20), nullable=False),
        # Patient-provided reason
        sa.Column("reason", sa.Text(), nullable=True),
        # Safety concern detected in reason
        sa.Column(
            "safety_concern_flagged",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        # Request status: pending, approved, denied, auto_approved
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="'pending'",
        ),
        # Was request made within 24h of appointment
        sa.Column(
            "within_24h",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        # For reschedule requests: requested new time
        sa.Column(
            "requested_new_start",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "requested_new_clinician_id",
            postgresql.UUID(as_uuid=False),
            nullable=True,
        ),
        # Staff review fields
        sa.Column(
            "reviewed_by",
            postgresql.UUID(as_uuid=False),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        # Constraints
        sa.PrimaryKeyConstraint("id", name="pk_cancellation_requests"),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            name="fk_cancellation_requests_appointment_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_cancellation_requests_patient_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["triage_case_id"],
            ["triage_cases.id"],
            name="fk_cancellation_requests_triage_case_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name="fk_cancellation_requests_reviewed_by",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["requested_new_clinician_id"],
            ["clinician_profiles.id"],
            name="fk_cancellation_requests_new_clinician_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_cancellation_requests_appointment_id",
        "cancellation_requests",
        ["appointment_id"],
    )
    op.create_index(
        "ix_cancellation_requests_patient_id",
        "cancellation_requests",
        ["patient_id"],
    )
    op.create_index(
        "ix_cancellation_requests_status",
        "cancellation_requests",
        ["status"],
    )
    op.create_index(
        "ix_cancellation_requests_safety_flagged",
        "cancellation_requests",
        ["safety_concern_flagged"],
        postgresql_where=sa.text("safety_concern_flagged = true"),
    )


def downgrade() -> None:
    """Remove cancellation/rescheduling tables and columns."""

    # Drop cancellation_requests table
    op.drop_index("ix_cancellation_requests_safety_flagged", table_name="cancellation_requests")
    op.drop_index("ix_cancellation_requests_status", table_name="cancellation_requests")
    op.drop_index("ix_cancellation_requests_patient_id", table_name="cancellation_requests")
    op.drop_index("ix_cancellation_requests_appointment_id", table_name="cancellation_requests")
    op.drop_table("cancellation_requests")

    # Drop appointment reschedule columns
    op.drop_index("ix_appointments_rescheduled_from_id", table_name="appointments")
    op.drop_constraint("fk_appointments_rescheduled_from", "appointments", type_="foreignkey")
    op.drop_column("appointments", "rescheduled_from_id")
    op.drop_column("appointments", "reschedule_count")

    # Drop patient behavior columns
    op.drop_column("patients", "last_behavior_reset_at")
    op.drop_column("patients", "no_show_count_90d")
    op.drop_column("patients", "cancellation_count_90d")
