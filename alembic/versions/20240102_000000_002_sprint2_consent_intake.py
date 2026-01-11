"""Sprint 2: Consent model and questionnaire submitted_at field.

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add consent table and submitted_at to questionnaire_responses."""

    # Add submitted_at column to questionnaire_responses
    op.add_column(
        "questionnaire_responses",
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create consents table
    op.create_table(
        "consents",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("consent_version", sa.String(50), nullable=False),
        sa.Column("channels", postgresql.JSON(), nullable=False),
        sa.Column("agreed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("consent_items", postgresql.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_consents"),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name="fk_consents_patient_id_patients",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_consents_patient_id", "consents", ["patient_id"])
    op.create_index("ix_consents_agreed_at", "consents", ["agreed_at"])
    op.create_index("ix_consents_consent_version", "consents", ["consent_version"])


def downgrade() -> None:
    """Remove consent table and submitted_at column."""
    op.drop_table("consents")
    op.drop_column("questionnaire_responses", "submitted_at")
