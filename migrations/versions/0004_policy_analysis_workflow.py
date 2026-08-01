"""Add durable policy analysis workflow records.

Revision ID: 0004_policy_analysis
Revises: 0003_policy_extraction
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_policy_analysis"
down_revision: str | None = "0003_policy_extraction"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "policy_analysis_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.String(length=100), nullable=False),
        sa.Column("policy_change_id", sa.String(length=100), nullable=False),
        sa.Column("policy_text_snapshot", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("current_step", sa.String(length=40), nullable=False),
        sa.Column("latest_extraction_attempt_id", sa.Uuid(), nullable=True),
        sa.Column("assessment_id", sa.Uuid(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("failure_detail", sa.Text(), nullable=True),
        sa.Column("workflow_version", sa.String(length=100), nullable=False),
        sa.Column("model_provider", sa.String(length=100), nullable=False),
        sa.Column("model_identifier", sa.String(length=200), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("schema_version", sa.String(length=100), nullable=False),
        sa.Column(
            "accepted_rule_provenance",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'awaiting_clarification', "
            "'completed', 'unsupported', 'failed')",
            name="ck_policy_analysis_runs_status",
        ),
        sa.CheckConstraint(
            "current_step IN ('initialize', 'extract', 'evaluate_extraction', "
            "'evaluate_clarification', 'await_clarification', "
            "'create_assessment', 'finalize', 'terminal')",
            name="ck_policy_analysis_runs_current_step",
        ),
        sa.CheckConstraint("retry_count >= 0", name="ck_policy_analysis_runs_retry_count"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["policy_change_id"], ["policy_changes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_policy_analysis_runs_organization_id",
        "policy_analysis_runs",
        ["organization_id"],
    )
    op.create_index(
        "ix_policy_analysis_runs_policy_change_id",
        "policy_analysis_runs",
        ["policy_change_id"],
    )

    op.add_column(
        "policy_extraction_attempts",
        sa.Column("policy_analysis_run_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "policy_extraction_attempts",
        sa.Column("retry_reason", sa.String(length=100), nullable=True),
    )
    op.create_foreign_key(
        "fk_policy_extraction_attempts_analysis_run",
        "policy_extraction_attempts",
        "policy_analysis_runs",
        ["policy_analysis_run_id"],
        ["id"],
    )
    op.create_index(
        "ix_policy_extraction_attempts_policy_analysis_run_id",
        "policy_extraction_attempts",
        ["policy_analysis_run_id"],
    )
    op.create_foreign_key(
        "fk_policy_analysis_runs_latest_attempt",
        "policy_analysis_runs",
        "policy_extraction_attempts",
        ["latest_extraction_attempt_id"],
        ["id"],
    )

    op.create_table(
        "policy_analysis_clarifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("policy_analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("question_code", sa.String(length=100), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column(
            "expected_answer_contract",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "affected_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column(
            "answer",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("responder_identity", sa.String(length=200), nullable=True),
        sa.Column(
            "answer_provenance",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'answered', 'superseded')",
            name="ck_policy_analysis_clarifications_status",
        ),
        sa.ForeignKeyConstraint(["policy_analysis_run_id"], ["policy_analysis_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "policy_analysis_run_id",
            "question_code",
            name="uq_policy_analysis_clarifications_run_question",
        ),
    )
    op.create_index(
        "ix_policy_analysis_clarifications_policy_analysis_run_id",
        "policy_analysis_clarifications",
        ["policy_analysis_run_id"],
    )

    op.add_column(
        "impact_assessments",
        sa.Column("policy_analysis_run_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_impact_assessments_policy_analysis_run_id",
        "impact_assessments",
        ["policy_analysis_run_id"],
    )
    op.create_unique_constraint(
        "uq_impact_assessments_policy_analysis_run",
        "impact_assessments",
        ["policy_analysis_run_id"],
    )
    op.create_foreign_key(
        "fk_impact_assessments_policy_analysis_run",
        "impact_assessments",
        "policy_analysis_runs",
        ["policy_analysis_run_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_policy_analysis_runs_assessment",
        "policy_analysis_runs",
        "impact_assessments",
        ["assessment_id"],
        ["id"],
    )

    op.execute(
        """
        CREATE FUNCTION reject_policy_analysis_clarification_question_mutation()
        RETURNS trigger AS $$
        BEGIN
            IF OLD.policy_analysis_run_id IS DISTINCT FROM NEW.policy_analysis_run_id
               OR OLD.question_code IS DISTINCT FROM NEW.question_code
               OR OLD.question_text IS DISTINCT FROM NEW.question_text
               OR OLD.expected_answer_contract IS DISTINCT FROM NEW.expected_answer_contract
               OR OLD.affected_fields IS DISTINCT FROM NEW.affected_fields
               OR OLD.created_at IS DISTINCT FROM NEW.created_at THEN
                RAISE EXCEPTION 'policy analysis clarification questions are immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER policy_analysis_clarification_question_immutable
        BEFORE UPDATE ON policy_analysis_clarifications
        FOR EACH ROW EXECUTE FUNCTION reject_policy_analysis_clarification_question_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER policy_analysis_clarification_question_immutable "
        "ON policy_analysis_clarifications"
    )
    op.execute("DROP FUNCTION reject_policy_analysis_clarification_question_mutation()")
    op.drop_constraint(
        "fk_policy_analysis_runs_assessment",
        "policy_analysis_runs",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_impact_assessments_policy_analysis_run",
        "impact_assessments",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_impact_assessments_policy_analysis_run",
        "impact_assessments",
        type_="unique",
    )
    op.drop_index(
        "ix_impact_assessments_policy_analysis_run_id",
        table_name="impact_assessments",
    )
    op.drop_column("impact_assessments", "policy_analysis_run_id")
    op.drop_table("policy_analysis_clarifications")
    op.drop_constraint(
        "fk_policy_analysis_runs_latest_attempt",
        "policy_analysis_runs",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_policy_extraction_attempts_policy_analysis_run_id",
        table_name="policy_extraction_attempts",
    )
    op.drop_constraint(
        "fk_policy_extraction_attempts_analysis_run",
        "policy_extraction_attempts",
        type_="foreignkey",
    )
    op.drop_column("policy_extraction_attempts", "retry_reason")
    op.drop_column("policy_extraction_attempts", "policy_analysis_run_id")
    op.drop_table("policy_analysis_runs")
