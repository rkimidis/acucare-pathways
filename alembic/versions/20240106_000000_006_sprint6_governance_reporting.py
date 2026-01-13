"""Sprint 6: Governance, Reporting, CQC Evidence Exports.

Revision ID: 006
Revises: 005
Create Date: 2024-01-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Incidents table
    op.create_table(
        'incidents',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('reference_number', sa.String(20), unique=True, nullable=False, index=True),
        sa.Column('triage_case_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('triage_cases.id'), nullable=True, index=True),
        sa.Column('patient_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('patients.id'), nullable=True, index=True),
        sa.Column('category', sa.String(50), nullable=False, default='other'),
        sa.Column('severity', sa.String(20), nullable=False, default='medium'),
        sa.Column('status', sa.String(20), nullable=False, default='open', index=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('immediate_actions_taken', sa.Text, nullable=True),
        sa.Column('reported_by', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('reported_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('review_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_notes', sa.Text, nullable=True),
        sa.Column('closed_by', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closure_reason', sa.Text, nullable=True),
        sa.Column('lessons_learned', sa.Text, nullable=True),
        sa.Column('preventive_actions', sa.Text, nullable=True),
        sa.Column('reportable_to_cqc', sa.Boolean, default=False),
        sa.Column('cqc_reported_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        'ix_incidents_status_severity',
        'incidents',
        ['status', 'severity']
    )

    op.create_index(
        'ix_incidents_reported_at',
        'incidents',
        ['reported_at']
    )

    # Ruleset Approvals table
    op.create_table(
        'ruleset_approvals',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('ruleset_type', sa.String(50), nullable=False, index=True),
        sa.Column('ruleset_version', sa.String(20), nullable=False),
        sa.Column('previous_version', sa.String(20), nullable=True),
        sa.Column('change_summary', sa.Text, nullable=False),
        sa.Column('change_rationale', sa.Text, nullable=False),
        sa.Column('rules_added', postgresql.JSON, nullable=True),
        sa.Column('rules_modified', postgresql.JSON, nullable=True),
        sa.Column('rules_removed', postgresql.JSON, nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('submitted_by', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending', index=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approval_notes', sa.Text, nullable=True),
        sa.Column('rejected_by', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    op.create_index(
        'ix_ruleset_approvals_type_version',
        'ruleset_approvals',
        ['ruleset_type', 'ruleset_version']
    )

    # Questionnaire Versions table
    op.create_table(
        'questionnaire_versions',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('questionnaire_code', sa.String(50), nullable=False, index=True),
        sa.Column('version', sa.String(20), nullable=False),
        sa.Column('previous_version_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('questionnaire_versions.id'), nullable=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('questions', postgresql.JSON, nullable=False),
        sa.Column('scoring_rules', postgresql.JSON, nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('change_summary', sa.Text, nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='pending'),
        sa.Column('approved_by', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean, default=False),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    op.create_index(
        'ix_questionnaire_versions_code_version',
        'questionnaire_versions',
        ['questionnaire_code', 'version'],
        unique=True
    )

    # Evidence Exports table
    op.create_table(
        'evidence_exports',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('export_type', sa.String(50), nullable=False, index=True),
        sa.Column('date_range_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('date_range_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('triage_case_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('triage_cases.id'), nullable=True),
        sa.Column('filters', postgresql.JSON, nullable=True),
        sa.Column('exported_by', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('exported_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('export_reason', sa.Text, nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_size_bytes', sa.Integer, nullable=False),
        sa.Column('file_format', sa.String(20), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('record_count', sa.Integer, nullable=False),
        sa.Column('download_count', sa.Integer, default=0),
        sa.Column('last_downloaded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_downloaded_by', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # LLM Summaries table
    op.create_table(
        'llm_summaries',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('triage_case_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('triage_cases.id'), nullable=False, index=True),
        sa.Column('source_data_type', sa.String(50), nullable=False),
        sa.Column('source_data_hash', sa.String(64), nullable=False),
        sa.Column('model_id', sa.String(100), nullable=False),
        sa.Column('model_version', sa.String(50), nullable=False),
        sa.Column('prompt_template_version', sa.String(20), nullable=False),
        sa.Column('prompt_hash', sa.String(64), nullable=False),
        sa.Column('generated_summary', sa.Text, nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='draft', index=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('clinician_edits', sa.Text, nullable=True),
        sa.Column('final_summary', sa.Text, nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_by', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('llm_summaries')
    op.drop_table('evidence_exports')
    op.drop_index('ix_questionnaire_versions_code_version', table_name='questionnaire_versions')
    op.drop_table('questionnaire_versions')
    op.drop_index('ix_ruleset_approvals_type_version', table_name='ruleset_approvals')
    op.drop_table('ruleset_approvals')
    op.drop_index('ix_incidents_reported_at', table_name='incidents')
    op.drop_index('ix_incidents_status_severity', table_name='incidents')
    op.drop_table('incidents')
