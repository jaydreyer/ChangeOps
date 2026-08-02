"""Materialize immutable execution commands.

Revision ID: 0008_execution_commands
Revises: 0007_action_approval_workflow
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_execution_commands"
down_revision: str | None = "0007_action_approval_workflow"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_action_review_decisions_id_review",
        "action_review_decisions",
        ["id", "action_review_id"],
    )
    op.create_unique_constraint(
        "uq_action_approval_items_execution_owner",
        "action_approval_run_items",
        [
            "approval_run_id",
            "action_review_id",
            "proposed_action_id",
            "assessment_id",
        ],
    )
    op.create_table(
        "execution_commands",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("approval_run_id", sa.Uuid(), nullable=False),
        sa.Column("action_review_id", sa.Uuid(), nullable=False),
        sa.Column("action_review_decision_id", sa.Uuid(), nullable=False),
        sa.Column("proposed_action_id", sa.Uuid(), nullable=False),
        sa.Column("assessment_id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=50), nullable=False),
        sa.Column("system", sa.String(length=50), nullable=False),
        sa.Column("operation", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_identifier", sa.String(length=200), nullable=False),
        sa.Column(
            "parameters_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "effective_action_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("prepared_by", sa.String(length=200), nullable=False),
        sa.Column("prepared_role", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status = 'pending_execution'",
            name="ck_execution_commands_status",
        ),
        sa.CheckConstraint(
            "schema_version = 'execution-command-v1'",
            name="ck_execution_commands_schema_version",
        ),
        sa.CheckConstraint(
            "system = 'learning' AND operation = 'assign_training'",
            name="ck_execution_commands_supported_mapping",
        ),
        sa.CheckConstraint(
            "prepared_role = 'admin'",
            name="ck_execution_commands_prepared_role",
        ),
        sa.ForeignKeyConstraint(["approval_run_id"], ["action_approval_runs.id"]),
        sa.ForeignKeyConstraint(["action_review_id"], ["action_reviews.id"]),
        sa.ForeignKeyConstraint(
            ["action_review_decision_id"],
            ["action_review_decisions.id"],
        ),
        sa.ForeignKeyConstraint(["proposed_action_id"], ["proposed_actions.id"]),
        sa.ForeignKeyConstraint(["assessment_id"], ["impact_assessments.id"]),
        sa.ForeignKeyConstraint(
            [
                "approval_run_id",
                "action_review_id",
                "proposed_action_id",
                "assessment_id",
            ],
            [
                "action_approval_run_items.approval_run_id",
                "action_approval_run_items.action_review_id",
                "action_approval_run_items.proposed_action_id",
                "action_approval_run_items.assessment_id",
            ],
            name="fk_execution_commands_membership",
        ),
        sa.ForeignKeyConstraint(
            ["action_review_decision_id", "action_review_id"],
            ["action_review_decisions.id", "action_review_decisions.action_review_id"],
            name="fk_execution_commands_approval_decision",
        ),
        sa.ForeignKeyConstraint(
            ["action_review_id", "proposed_action_id", "assessment_id"],
            [
                "action_reviews.id",
                "action_reviews.proposed_action_id",
                "action_reviews.assessment_id",
            ],
            name="fk_execution_commands_review_lifecycle",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "action_review_id",
            name="uq_execution_commands_action_review",
        ),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_execution_commands_idempotency_key",
        ),
    )
    for column in (
        "approval_run_id",
        "action_review_id",
        "action_review_decision_id",
        "proposed_action_id",
        "assessment_id",
    ):
        op.create_index(
            f"ix_execution_commands_{column}",
            "execution_commands",
            [column],
        )

    op.execute(
        """
        CREATE FUNCTION validate_execution_command_insert()
        RETURNS trigger AS $$
        DECLARE
            run_status text;
            review_status text;
            decision_value text;
            original_action jsonb;
            edited_action jsonb;
            authorized_effective_action jsonb;
        BEGIN
            SELECT status INTO run_status
            FROM action_approval_runs
            WHERE id = NEW.approval_run_id
            FOR UPDATE;
            SELECT status, original_action_snapshot
            INTO review_status, original_action
            FROM action_reviews
            WHERE id = NEW.action_review_id;
            SELECT decision, edited_action_snapshot
            INTO decision_value, edited_action
            FROM action_review_decisions
            WHERE id = NEW.action_review_decision_id
              AND action_review_id = NEW.action_review_id;

            IF run_status IS DISTINCT FROM 'completed' THEN
                RAISE EXCEPTION 'execution command requires a completed approval run';
            END IF;
            IF review_status IS DISTINCT FROM 'approved'
               OR decision_value IS DISTINCT FROM 'approved' THEN
                RAISE EXCEPTION 'execution command requires an approved review decision';
            END IF;

            authorized_effective_action :=
                original_action
                || jsonb_build_object(
                    'schema_version',
                    'effective-approved-action-v1'
                )
                || COALESCE(edited_action, '{}'::jsonb);

            IF NEW.effective_action_snapshot
               IS DISTINCT FROM authorized_effective_action
               OR authorized_effective_action->>'proposed_action_id'
                  IS DISTINCT FROM NEW.proposed_action_id::text
               OR authorized_effective_action->>'assessment_id'
                  IS DISTINCT FROM NEW.assessment_id::text
               OR authorized_effective_action->>'action_type'
                  IS DISTINCT FROM 'training_assignment'
               OR authorized_effective_action->>'target_type'
                  IS DISTINCT FROM 'worker'
               OR authorized_effective_action->>'worker_id'
                  IS DISTINCT FROM authorized_effective_action->>'target_identifier'
               OR authorized_effective_action->>'target_type'
                  IS DISTINCT FROM NEW.target_type
               OR authorized_effective_action->>'target_identifier'
                  IS DISTINCT FROM NEW.target_identifier
               OR authorized_effective_action->>'execution_status'
                  IS DISTINCT FROM 'not_executed' THEN
                RAISE EXCEPTION 'execution command effective action snapshot is inconsistent';
            END IF;
            IF jsonb_typeof(NEW.parameters_snapshot) IS DISTINCT FROM 'object' THEN
                RAISE EXCEPTION 'execution command parameters must be an object';
            END IF;
            IF NEW.parameters_snapshot->>'worker_identifier'
               IS DISTINCT FROM authorized_effective_action->>'worker_id'
               OR NEW.parameters_snapshot->>'course_identifier'
                  IS DISTINCT FROM 'international-travel-security'
               OR NEW.parameters_snapshot->>'description'
                  IS DISTINCT FROM authorized_effective_action->>'description'
               OR NEW.parameters_snapshot->'due_date'
                  IS DISTINCT FROM authorized_effective_action->'due_date' THEN
                RAISE EXCEPTION 'execution command parameters are inconsistent';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER execution_commands_validate_insert
        BEFORE INSERT ON execution_commands
        FOR EACH ROW EXECUTE FUNCTION validate_execution_command_insert()
        """
    )
    op.execute(
        """
        CREATE FUNCTION reject_execution_command_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'execution commands are immutable audit records';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER execution_commands_immutable
        BEFORE UPDATE OR DELETE ON execution_commands
        FOR EACH ROW EXECUTE FUNCTION reject_execution_command_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER execution_commands_immutable ON execution_commands")
    op.execute("DROP FUNCTION reject_execution_command_mutation()")
    op.execute("DROP TRIGGER execution_commands_validate_insert ON execution_commands")
    op.execute("DROP FUNCTION validate_execution_command_insert()")
    op.drop_table("execution_commands")
    op.drop_constraint(
        "uq_action_approval_items_execution_owner",
        "action_approval_run_items",
        type_="unique",
    )
    op.drop_constraint(
        "uq_action_review_decisions_id_review",
        "action_review_decisions",
        type_="unique",
    )
