"""Add durable action approval workflow runs.

Revision ID: 0007_action_approval_workflow
Revises: 0006_action_reviews
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_action_approval_workflow"
down_revision: str | None = "0006_action_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_action_reviews_id_action_assessment",
        "action_reviews",
        ["id", "proposed_action_id", "assessment_id"],
    )
    op.create_table(
        "action_approval_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("policy_analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("current_step", sa.String(length=30), nullable=False),
        sa.Column("total_action_count", sa.Integer(), nullable=False),
        sa.Column("pending_count", sa.Integer(), nullable=False),
        sa.Column("approved_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("deferred_count", sa.Integer(), nullable=False),
        sa.Column("revision_requested_count", sa.Integer(), nullable=False),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('initializing', 'awaiting_decisions', 'completed', 'failed')",
            name="ck_action_approval_runs_status",
        ),
        sa.CheckConstraint(
            "current_step IN ('create_reviews', 'evaluate_reviews', 'await_decisions', 'finalize')",
            name="ck_action_approval_runs_current_step",
        ),
        sa.CheckConstraint(
            "total_action_count >= 0 AND pending_count >= 0 AND approved_count >= 0 "
            "AND rejected_count >= 0 AND deferred_count >= 0 "
            "AND revision_requested_count >= 0",
            name="ck_action_approval_runs_nonnegative_counts",
        ),
        sa.CheckConstraint(
            "total_action_count = pending_count + approved_count + rejected_count "
            "+ deferred_count + revision_requested_count",
            name="ck_action_approval_runs_count_total",
        ),
        sa.CheckConstraint(
            "(status = 'awaiting_decisions' AND pending_count > 0) "
            "OR status <> 'awaiting_decisions'",
            name="ck_action_approval_runs_awaiting_pending",
        ),
        sa.CheckConstraint(
            "(status = 'completed' AND pending_count = 0 AND completed_at IS NOT NULL) "
            "OR (status <> 'completed' AND completed_at IS NULL)",
            name="ck_action_approval_runs_completion",
        ),
        sa.ForeignKeyConstraint(["assessment_id"], ["impact_assessments.id"]),
        sa.ForeignKeyConstraint(["policy_analysis_run_id"], ["policy_analysis_runs.id"]),
        sa.ForeignKeyConstraint(
            ["assessment_id", "policy_analysis_run_id"],
            ["impact_assessments.id", "impact_assessments.policy_analysis_run_id"],
            name="fk_action_approval_runs_assessment_analysis",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_id", name="uq_action_approval_runs_assessment"),
        sa.UniqueConstraint(
            "id",
            "assessment_id",
            name="uq_action_approval_runs_id_assessment",
        ),
    )
    op.create_index(
        "ix_action_approval_runs_assessment_id",
        "action_approval_runs",
        ["assessment_id"],
    )
    op.create_index(
        "ix_action_approval_runs_policy_analysis_run_id",
        "action_approval_runs",
        ["policy_analysis_run_id"],
    )
    op.create_table(
        "action_approval_run_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("approval_run_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("proposed_action_id", sa.Uuid(), nullable=False),
        sa.Column("action_review_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "sequence >= 0",
            name="ck_action_approval_run_items_sequence",
        ),
        sa.ForeignKeyConstraint(["approval_run_id"], ["action_approval_runs.id"]),
        sa.ForeignKeyConstraint(["assessment_id"], ["impact_assessments.id"]),
        sa.ForeignKeyConstraint(["proposed_action_id"], ["proposed_actions.id"]),
        sa.ForeignKeyConstraint(["action_review_id"], ["action_reviews.id"]),
        sa.ForeignKeyConstraint(
            ["approval_run_id", "assessment_id"],
            ["action_approval_runs.id", "action_approval_runs.assessment_id"],
            name="fk_action_approval_items_run_assessment",
        ),
        sa.ForeignKeyConstraint(
            ["proposed_action_id", "assessment_id"],
            ["proposed_actions.id", "proposed_actions.assessment_id"],
            name="fk_action_approval_items_action_assessment",
        ),
        sa.ForeignKeyConstraint(
            ["action_review_id", "proposed_action_id", "assessment_id"],
            [
                "action_reviews.id",
                "action_reviews.proposed_action_id",
                "action_reviews.assessment_id",
            ],
            name="fk_action_approval_items_review_action_assessment",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "approval_run_id",
            "proposed_action_id",
            name="uq_action_approval_run_items_action",
        ),
        sa.UniqueConstraint(
            "approval_run_id",
            "action_review_id",
            name="uq_action_approval_run_items_review",
        ),
        sa.UniqueConstraint(
            "approval_run_id",
            "sequence",
            name="uq_action_approval_run_items_sequence",
        ),
    )
    op.create_index(
        "ix_action_approval_run_items_approval_run_id",
        "action_approval_run_items",
        ["approval_run_id"],
    )
    op.create_index(
        "ix_action_approval_run_items_proposed_action_id",
        "action_approval_run_items",
        ["proposed_action_id"],
    )
    op.create_index(
        "ix_action_approval_run_items_action_review_id",
        "action_approval_run_items",
        ["action_review_id"],
    )
    op.create_table(
        "action_approval_run_transitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("approval_run_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=False),
        sa.Column("from_step", sa.String(length=30), nullable=True),
        sa.Column("to_step", sa.String(length=30), nullable=False),
        sa.Column("reason_code", sa.String(length=100), nullable=False),
        sa.Column("trigger_type", sa.String(length=30), nullable=False),
        sa.Column("trigger_reference", sa.String(length=200), nullable=True),
        sa.Column("actor_identity", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "trigger_type IN "
            "('run_created', 'initialized', 'decision_recorded', "
            "'manual_resume', 'completed', 'failed')",
            name="ck_action_approval_run_transitions_trigger",
        ),
        sa.ForeignKeyConstraint(["approval_run_id"], ["action_approval_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_action_approval_run_transitions_approval_run_id",
        "action_approval_run_transitions",
        ["approval_run_id"],
    )

    op.execute(
        """
        CREATE FUNCTION validate_action_approval_run()
        RETURNS trigger AS $$
        DECLARE
            assessment_status text;
            analysis_status text;
            persisted_total integer;
            persisted_pending integer;
            persisted_approved integer;
            persisted_rejected integer;
            persisted_deferred integer;
            persisted_revision_requested integer;
        BEGIN
            SELECT status INTO assessment_status
            FROM impact_assessments
            WHERE id = NEW.assessment_id
              AND policy_analysis_run_id = NEW.policy_analysis_run_id;
            SELECT status INTO analysis_status
            FROM policy_analysis_runs
            WHERE id = NEW.policy_analysis_run_id;
            IF assessment_status IS DISTINCT FROM 'completed'
               OR analysis_status IS DISTINCT FROM 'completed' THEN
                RAISE EXCEPTION 'approval run requires a completed assessment and analysis run';
            END IF;

            IF NEW.status IN ('awaiting_decisions', 'completed') THEN
                SELECT
                    count(*),
                    count(*) FILTER (WHERE r.status = 'pending'),
                    count(*) FILTER (WHERE r.status = 'approved'),
                    count(*) FILTER (WHERE r.status = 'rejected'),
                    count(*) FILTER (WHERE r.status = 'deferred'),
                    count(*) FILTER (WHERE r.status = 'revision_requested')
                INTO
                    persisted_total,
                    persisted_pending,
                    persisted_approved,
                    persisted_rejected,
                    persisted_deferred,
                    persisted_revision_requested
                FROM action_approval_run_items i
                JOIN action_reviews r ON r.id = i.action_review_id
                WHERE i.approval_run_id = NEW.id;
                IF (NEW.total_action_count, NEW.pending_count, NEW.approved_count,
                    NEW.rejected_count, NEW.deferred_count,
                    NEW.revision_requested_count)
                   IS DISTINCT FROM
                   (persisted_total, persisted_pending, persisted_approved,
                    persisted_rejected, persisted_deferred,
                    persisted_revision_requested) THEN
                    RAISE EXCEPTION 'approval run counts do not match persisted reviews';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER action_approval_runs_validate
        BEFORE INSERT OR UPDATE ON action_approval_runs
        FOR EACH ROW EXECUTE FUNCTION validate_action_approval_run()
        """
    )
    op.execute(
        """
        CREATE FUNCTION enforce_action_approval_run_mutation()
        RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'approval runs are durable audit records';
            END IF;
            IF OLD.id IS DISTINCT FROM NEW.id
               OR OLD.assessment_id IS DISTINCT FROM NEW.assessment_id
               OR OLD.policy_analysis_run_id IS DISTINCT FROM NEW.policy_analysis_run_id
               OR OLD.created_at IS DISTINCT FROM NEW.created_at THEN
                RAISE EXCEPTION 'approval run identity is immutable';
            END IF;
            IF OLD.status = 'completed' THEN
                RAISE EXCEPTION 'completed approval runs are immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER action_approval_runs_immutable
        BEFORE UPDATE OR DELETE ON action_approval_runs
        FOR EACH ROW EXECUTE FUNCTION enforce_action_approval_run_mutation()
        """
    )
    op.execute(
        """
        CREATE FUNCTION enforce_action_approval_item_insert()
        RETURNS trigger AS $$
        DECLARE
            run_status text;
            run_step text;
        BEGIN
            SELECT status, current_step INTO run_status, run_step
            FROM action_approval_runs
            WHERE id = NEW.approval_run_id
            FOR UPDATE;
            IF run_status IS DISTINCT FROM 'initializing'
               OR run_step IS DISTINCT FROM 'create_reviews' THEN
                RAISE EXCEPTION 'approval membership is closed';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER action_approval_run_items_validate_insert
        BEFORE INSERT ON action_approval_run_items
        FOR EACH ROW EXECUTE FUNCTION enforce_action_approval_item_insert()
        """
    )
    op.execute(
        """
        CREATE FUNCTION reject_action_approval_audit_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'approval workflow audit records are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER action_approval_run_items_immutable
        BEFORE UPDATE OR DELETE ON action_approval_run_items
        FOR EACH ROW EXECUTE FUNCTION reject_action_approval_audit_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER action_approval_run_transitions_append_only
        BEFORE UPDATE OR DELETE ON action_approval_run_transitions
        FOR EACH ROW EXECUTE FUNCTION reject_action_approval_audit_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER action_approval_run_transitions_append_only "
        "ON action_approval_run_transitions"
    )
    op.execute("DROP TRIGGER action_approval_run_items_immutable ON action_approval_run_items")
    op.execute("DROP FUNCTION reject_action_approval_audit_mutation()")
    op.execute(
        "DROP TRIGGER action_approval_run_items_validate_insert ON action_approval_run_items"
    )
    op.execute("DROP FUNCTION enforce_action_approval_item_insert()")
    op.execute("DROP TRIGGER action_approval_runs_immutable ON action_approval_runs")
    op.execute("DROP FUNCTION enforce_action_approval_run_mutation()")
    op.execute("DROP TRIGGER action_approval_runs_validate ON action_approval_runs")
    op.execute("DROP FUNCTION validate_action_approval_run()")
    op.drop_table("action_approval_run_transitions")
    op.drop_table("action_approval_run_items")
    op.drop_table("action_approval_runs")
    op.drop_constraint(
        "uq_action_reviews_id_action_assessment",
        "action_reviews",
        type_="unique",
    )
