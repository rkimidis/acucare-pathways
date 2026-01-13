"""Add audit_events immutability trigger.

Revision ID: 007_audit_immutability
Revises: 006
Create Date: 2024-01-07 00:00:00.000000

This migration adds a PostgreSQL trigger to prevent UPDATE and DELETE
operations on the audit_events table, ensuring append-only behavior
at the database level for compliance with CQC and UK GDPR requirements.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "007_audit_immutability"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add immutability trigger to audit_events table."""

    # Create the trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                RAISE EXCEPTION 'SECURITY VIOLATION: Audit events are immutable and cannot be modified. Event ID: %', OLD.id;
            ELSIF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'SECURITY VIOLATION: Audit events are immutable and cannot be deleted. Event ID: %', OLD.id;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Drop existing trigger if any
    op.execute("""
        DROP TRIGGER IF EXISTS audit_immutability_trigger ON audit_events
    """)

    # Create the trigger on audit_events table
    op.execute("""
        CREATE TRIGGER audit_immutability_trigger
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_modification()
    """)

    # Add a comment to document the security control
    op.execute("""
        COMMENT ON TRIGGER audit_immutability_trigger ON audit_events IS
        'Security control: Prevents modification or deletion of audit events to ensure compliance with CQC and UK GDPR audit trail requirements. Added as part of security hardening.';
    """)

    # Also add a comment on the table itself
    op.execute("""
        COMMENT ON TABLE audit_events IS
        'Append-only audit log for compliance tracking. Protected by immutability trigger - records cannot be modified or deleted after creation.';
    """)


def downgrade() -> None:
    """Remove immutability trigger (use with caution - reduces security)."""

    # Drop the trigger
    op.execute("""
        DROP TRIGGER IF EXISTS audit_immutability_trigger ON audit_events;
    """)

    # Drop the function
    op.execute("""
        DROP FUNCTION IF EXISTS prevent_audit_modification();
    """)

    # Remove comments (optional, comments don't affect functionality)
    op.execute("""
        COMMENT ON TABLE audit_events IS NULL;
    """)
