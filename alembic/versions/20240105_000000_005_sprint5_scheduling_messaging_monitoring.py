"""Sprint 5: Scheduling, messaging, and waiting list monitoring.

Revision ID: 005
Revises: 004
Create Date: 2024-01-05 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add scheduling, messaging, and monitoring tables."""

    # ========================================================================
    # SCHEDULING TABLES
    # ========================================================================

    # Clinician profiles
    op.create_table(
        "clinician_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column("registration_number", sa.String(50), nullable=True),
        sa.Column("registration_body", sa.String(100), nullable=True),
        sa.Column("title", sa.String(150), nullable=False),
        sa.Column("specialties", postgresql.ARRAY(sa.String(50)), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("accepting_new_patients", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("max_daily_appointments", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("default_appointment_duration", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("can_handle_crisis", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_clinician_profiles"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_clinician_profiles_user_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("user_id", name="uq_clinician_profiles_user_id"),
    )
    op.create_index("ix_clinician_profiles_user_id", "clinician_profiles", ["user_id"])

    # Availability slots
    op.create_table(
        "availability_slots",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "clinician_id",
            postgresql.UUID(as_uuid=False),
            nullable=False,
        ),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_until", sa.Date(), nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("is_remote", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_availability_slots"),
        sa.ForeignKeyConstraint(
            ["clinician_id"],
            ["clinician_profiles.id"],
            name="fk_availability_slots_clinician_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_availability_slots_clinician_id", "availability_slots", ["clinician_id"])

    # Appointment types
    op.create_table(
        "appointment_types",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("buffer_minutes", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("self_book_tiers", postgresql.ARRAY(sa.String(20)), nullable=False),
        sa.Column("required_specialties", postgresql.ARRAY(sa.String(50)), nullable=False),
        sa.Column("allow_remote", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_bookable", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("color", sa.String(7), nullable=False, server_default="'#3b82f6'"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_appointment_types"),
        sa.UniqueConstraint("code", name="uq_appointment_types_code"),
    )
    op.create_index("ix_appointment_types_code", "appointment_types", ["code"])

    # Appointments
    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("clinician_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("triage_case_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("appointment_type_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="'scheduled'"),
        sa.Column("booking_source", sa.String(30), nullable=False),
        sa.Column("booked_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("is_remote", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("video_link", sa.String(500), nullable=True),
        sa.Column("patient_notes", sa.Text(), nullable=True),
        sa.Column("staff_notes", sa.Text(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_appointments"),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_appointments_patient_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clinician_id"],
            ["clinician_profiles.id"],
            name="fk_appointments_clinician_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["triage_case_id"],
            ["triage_cases.id"],
            name="fk_appointments_triage_case_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["appointment_type_id"],
            ["appointment_types.id"],
            name="fk_appointments_appointment_type_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["booked_by"],
            ["users.id"],
            name="fk_appointments_booked_by",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"])
    op.create_index("ix_appointments_clinician_id", "appointments", ["clinician_id"])
    op.create_index("ix_appointments_scheduled_start", "appointments", ["scheduled_start"])
    op.create_index("ix_appointments_status", "appointments", ["status"])

    # ========================================================================
    # MESSAGING TABLES
    # ========================================================================

    # Message templates
    op.create_table(
        "message_templates",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("template_type", sa.String(50), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("html_body", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("variables", postgresql.JSON(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_message_templates"),
    )
    op.create_index("ix_message_templates_code", "message_templates", ["code"])

    # Messages
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("recipient_address", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("html_body", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="'pending'"),
        sa.Column("provider", sa.String(50), nullable=True),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("triage_case_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("checkin_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("metadata", postgresql.JSON(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_messages"),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_messages_patient_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["message_templates.id"],
            name="fk_messages_template_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            name="fk_messages_appointment_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["triage_case_id"],
            ["triage_cases.id"],
            name="fk_messages_triage_case_id",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_messages_patient_id", "messages", ["patient_id"])
    op.create_index("ix_messages_channel", "messages", ["channel"])
    op.create_index("ix_messages_status", "messages", ["status"])
    op.create_index("ix_messages_provider_message_id", "messages", ["provider_message_id"])

    # Delivery receipts
    op.create_table(
        "delivery_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_message_id", sa.String(255), nullable=False),
        sa.Column("provider_status", sa.String(50), nullable=False),
        sa.Column("mapped_status", sa.String(30), nullable=False),
        sa.Column("raw_payload", postgresql.JSON(), nullable=False),
        sa.Column("provider_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_delivery_receipts"),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["messages.id"],
            name="fk_delivery_receipts_message_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_delivery_receipts_message_id", "delivery_receipts", ["message_id"])

    # ========================================================================
    # MONITORING TABLES
    # ========================================================================

    # Waiting list check-ins
    op.create_table(
        "waiting_list_checkins",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("triage_case_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(30), nullable=False, server_default="'scheduled'"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("phq2_q1", sa.Integer(), nullable=True),
        sa.Column("phq2_q2", sa.Integer(), nullable=True),
        sa.Column("phq2_total", sa.Integer(), nullable=True),
        sa.Column("gad2_q1", sa.Integer(), nullable=True),
        sa.Column("gad2_q2", sa.Integer(), nullable=True),
        sa.Column("gad2_total", sa.Integer(), nullable=True),
        sa.Column("suicidal_ideation", sa.Boolean(), nullable=True),
        sa.Column("self_harm", sa.Boolean(), nullable=True),
        sa.Column("wellbeing_rating", sa.Integer(), nullable=True),
        sa.Column("patient_comments", sa.Text(), nullable=True),
        sa.Column("wants_callback", sa.Boolean(), nullable=True),
        sa.Column("requires_escalation", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("escalation_reason", sa.String(50), nullable=True),
        sa.Column("escalation_notes", sa.Text(), nullable=True),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("escalated_by_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("staff_notes", sa.Text(), nullable=True),
        sa.Column("raw_response", postgresql.JSON(), nullable=True),
        sa.Column("reminders_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reminder_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_waiting_list_checkins"),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_waiting_list_checkins_patient_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["triage_case_id"],
            ["triage_cases.id"],
            name="fk_waiting_list_checkins_triage_case_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name="fk_waiting_list_checkins_reviewed_by",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_waiting_list_checkins_patient_id", "waiting_list_checkins", ["patient_id"])
    op.create_index("ix_waiting_list_checkins_triage_case_id", "waiting_list_checkins", ["triage_case_id"])
    op.create_index("ix_waiting_list_checkins_scheduled_for", "waiting_list_checkins", ["scheduled_for"])
    op.create_index("ix_waiting_list_checkins_status", "waiting_list_checkins", ["status"])

    # Add foreign key for messages.checkin_id after checkins table exists
    op.create_foreign_key(
        "fk_messages_checkin_id",
        "messages",
        "waiting_list_checkins",
        ["checkin_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Monitoring schedules
    op.create_table(
        "monitoring_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("triage_case_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("frequency_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("max_reminders", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("reminder_interval_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("expiry_hours", sa.Integer(), nullable=False, server_default="72"),
        sa.Column("missed_threshold_escalation", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("last_checkin_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_checkin_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_missed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("paused", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("paused_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pause_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_monitoring_schedules"),
        sa.ForeignKeyConstraint(
            ["triage_case_id"],
            ["triage_cases.id"],
            name="fk_monitoring_schedules_triage_case_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("triage_case_id", name="uq_monitoring_schedules_triage_case_id"),
    )
    op.create_index("ix_monitoring_schedules_next_checkin_date", "monitoring_schedules", ["next_checkin_date"])

    # Monitoring alerts
    op.create_table(
        "monitoring_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("triage_case_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("checkin_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("phq2_score", sa.Integer(), nullable=True),
        sa.Column("gad2_score", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("action_taken", sa.String(100), nullable=True),
        sa.Column("escalated_to_amber", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_monitoring_alerts"),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_monitoring_alerts_patient_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["triage_case_id"],
            ["triage_cases.id"],
            name="fk_monitoring_alerts_triage_case_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["checkin_id"],
            ["waiting_list_checkins.id"],
            name="fk_monitoring_alerts_checkin_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["acknowledged_by"],
            ["users.id"],
            name="fk_monitoring_alerts_acknowledged_by",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by"],
            ["users.id"],
            name="fk_monitoring_alerts_resolved_by",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_monitoring_alerts_patient_id", "monitoring_alerts", ["patient_id"])
    op.create_index("ix_monitoring_alerts_triage_case_id", "monitoring_alerts", ["triage_case_id"])
    op.create_index("ix_monitoring_alerts_alert_type", "monitoring_alerts", ["alert_type"])
    op.create_index("ix_monitoring_alerts_severity", "monitoring_alerts", ["severity"])


def downgrade() -> None:
    """Remove Sprint 5 tables."""

    # Drop monitoring tables
    op.drop_table("monitoring_alerts")
    op.drop_table("monitoring_schedules")

    # Drop foreign key before dropping waiting_list_checkins
    op.drop_constraint("fk_messages_checkin_id", "messages", type_="foreignkey")

    op.drop_table("waiting_list_checkins")

    # Drop messaging tables
    op.drop_table("delivery_receipts")
    op.drop_table("messages")
    op.drop_table("message_templates")

    # Drop scheduling tables
    op.drop_table("appointments")
    op.drop_table("appointment_types")
    op.drop_table("availability_slots")
    op.drop_table("clinician_profiles")
