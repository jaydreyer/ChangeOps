"""Add grounded policy interpretation attempts and change plans.

Revision ID: 0005_policy_interpretation
Revises: 0004_policy_analysis
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_policy_interpretation"
down_revision: str | None = "0004_policy_analysis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "policy_interpretation_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("policy_analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("impact_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("raw_output", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("candidate_change_plan", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("validated_change_plan", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("validation_errors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_provider", sa.String(length=100), nullable=False),
        sa.Column("model_identifier", sa.String(length=200), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("schema_version", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('accepted', 'invalid', 'provider_failed')",
            name="ck_policy_interpretation_attempts_status",
        ),
        sa.ForeignKeyConstraint(["impact_assessment_id"], ["impact_assessments.id"]),
        sa.ForeignKeyConstraint(["policy_analysis_run_id"], ["policy_analysis_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_policy_interpretation_attempts_policy_analysis_run_id",
        "policy_interpretation_attempts",
        ["policy_analysis_run_id"],
    )
    op.create_index(
        "ix_policy_interpretation_attempts_impact_assessment_id",
        "policy_interpretation_attempts",
        ["impact_assessment_id"],
    )
    op.create_table(
        "change_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("policy_analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("impact_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("interpretation_attempt_id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=100), nullable=False),
        sa.Column("validated_plan", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["impact_assessment_id"], ["impact_assessments.id"]),
        sa.ForeignKeyConstraint(
            ["interpretation_attempt_id"], ["policy_interpretation_attempts.id"]
        ),
        sa.ForeignKeyConstraint(["policy_analysis_run_id"], ["policy_analysis_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("impact_assessment_id", name="uq_change_plans_impact_assessment"),
        sa.UniqueConstraint("interpretation_attempt_id", name="uq_change_plans_attempt"),
    )
    op.create_index(
        "ix_change_plans_policy_analysis_run_id", "change_plans", ["policy_analysis_run_id"]
    )
    op.create_index(
        "ix_change_plans_impact_assessment_id", "change_plans", ["impact_assessment_id"]
    )
    op.execute(
        """
        CREATE FUNCTION reject_policy_interpretation_attempt_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'policy interpretation attempts are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER policy_interpretation_attempts_append_only
        BEFORE UPDATE OR DELETE ON policy_interpretation_attempts
        FOR EACH ROW EXECUTE FUNCTION reject_policy_interpretation_attempt_mutation()
        """
    )
    op.execute(
        """
        CREATE FUNCTION reject_change_plan_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'change plans are immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER change_plans_immutable
        BEFORE UPDATE OR DELETE ON change_plans
        FOR EACH ROW EXECUTE FUNCTION reject_change_plan_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER change_plans_immutable ON change_plans")
    op.execute("DROP FUNCTION reject_change_plan_mutation()")
    op.execute(
        "DROP TRIGGER policy_interpretation_attempts_append_only ON policy_interpretation_attempts"
    )
    op.execute("DROP FUNCTION reject_policy_interpretation_attempt_mutation()")
    op.drop_table("change_plans")
    op.drop_table("policy_interpretation_attempts")
