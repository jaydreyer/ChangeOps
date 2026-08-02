"""Execute training assignments against a simulated learning system.

Revision ID: 0009_learning_execution
Revises: 0008_execution_commands
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_learning_execution"
down_revision: str | None = "0008_execution_commands"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "simulated_learning_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("worker_id", sa.String(length=100), nullable=False),
        sa.Column("training_course_id", sa.String(length=100), nullable=False),
        sa.Column("source_execution_command_id", sa.Uuid(), nullable=False),
        sa.Column("source_approved_action_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_status", sa.String(length=30), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "assignment_status = 'assigned'",
            name="ck_simulated_learning_assignments_status",
        ),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"]),
        sa.ForeignKeyConstraint(["training_course_id"], ["training_courses.id"]),
        sa.ForeignKeyConstraint(
            ["source_execution_command_id"],
            ["execution_commands.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_approved_action_id"],
            ["proposed_actions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_execution_command_id",
            name="uq_simulated_learning_assignments_command",
        ),
    )
    for column in (
        "worker_id",
        "training_course_id",
        "source_execution_command_id",
        "source_approved_action_id",
    ):
        op.create_index(
            f"ix_simulated_learning_assignments_{column}",
            "simulated_learning_assignments",
            [column],
        )

    op.create_table(
        "execution_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("execution_command_id", sa.Uuid(), nullable=False),
        sa.Column("simulated_learning_assignment_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("outcome_code", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("command_idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("attempted_by", sa.String(length=200), nullable=False),
        sa.Column("attempted_role", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN "
            "('succeeded', 'already_applied', 'rejected_unsupported', 'failed_validation')",
            name="ck_execution_results_status",
        ),
        sa.CheckConstraint(
            "(status IN ('succeeded', 'already_applied') "
            "AND simulated_learning_assignment_id IS NOT NULL) "
            "OR (status IN ('rejected_unsupported', 'failed_validation') "
            "AND simulated_learning_assignment_id IS NULL)",
            name="ck_execution_results_assignment_outcome",
        ),
        sa.CheckConstraint(
            "attempted_role = 'admin' AND length(btrim(attempted_by)) > 0",
            name="ck_execution_results_attempted_role",
        ),
        sa.ForeignKeyConstraint(
            ["execution_command_id"],
            ["execution_commands.id"],
        ),
        sa.ForeignKeyConstraint(
            ["simulated_learning_assignment_id"],
            ["simulated_learning_assignments.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_execution_results_execution_command_id",
        "execution_results",
        ["execution_command_id"],
    )
    op.create_index(
        "ix_execution_results_simulated_learning_assignment_id",
        "execution_results",
        ["simulated_learning_assignment_id"],
    )

    op.execute(
        """
        CREATE FUNCTION validate_simulated_learning_assignment_insert()
        RETURNS trigger AS $$
        DECLARE
            command_record execution_commands%ROWTYPE;
        BEGIN
            SELECT * INTO command_record
            FROM execution_commands
            WHERE id = NEW.source_execution_command_id
            FOR UPDATE;

            IF command_record.id IS NULL
               OR command_record.system IS DISTINCT FROM 'learning'
               OR command_record.operation IS DISTINCT FROM 'assign_training'
               OR command_record.status IS DISTINCT FROM 'pending_execution'
               OR command_record.target_type IS DISTINCT FROM 'worker'
               OR command_record.target_identifier IS DISTINCT FROM NEW.worker_id
               OR command_record.parameters_snapshot->>'worker_identifier'
                  IS DISTINCT FROM NEW.worker_id
               OR command_record.parameters_snapshot->>'course_identifier'
                  IS DISTINCT FROM NEW.training_course_id
               OR command_record.proposed_action_id
                  IS DISTINCT FROM NEW.source_approved_action_id THEN
                RAISE EXCEPTION 'simulated learning assignment is inconsistent with command';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER simulated_learning_assignments_validate_insert
        BEFORE INSERT ON simulated_learning_assignments
        FOR EACH ROW EXECUTE FUNCTION validate_simulated_learning_assignment_insert()
        """
    )
    op.execute(
        """
        CREATE FUNCTION reject_simulated_learning_assignment_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'simulated learning assignments are immutable in this slice';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER simulated_learning_assignments_immutable
        BEFORE UPDATE OR DELETE ON simulated_learning_assignments
        FOR EACH ROW EXECUTE FUNCTION reject_simulated_learning_assignment_mutation()
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_execution_result_insert()
        RETURNS trigger AS $$
        DECLARE
            command_key text;
            assignment_command_id uuid;
        BEGIN
            SELECT idempotency_key INTO command_key
            FROM execution_commands
            WHERE id = NEW.execution_command_id;

            IF command_key IS NULL
               OR command_key IS DISTINCT FROM NEW.command_idempotency_key THEN
                RAISE EXCEPTION 'execution result is inconsistent with command identity';
            END IF;

            IF NEW.simulated_learning_assignment_id IS NOT NULL THEN
                SELECT source_execution_command_id INTO assignment_command_id
                FROM simulated_learning_assignments
                WHERE id = NEW.simulated_learning_assignment_id;
                IF assignment_command_id IS DISTINCT FROM NEW.execution_command_id THEN
                    RAISE EXCEPTION 'execution result assignment belongs to another command';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER execution_results_validate_insert
        BEFORE INSERT ON execution_results
        FOR EACH ROW EXECUTE FUNCTION validate_execution_result_insert()
        """
    )
    op.execute(
        """
        CREATE FUNCTION reject_execution_result_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'execution results are immutable audit records';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER execution_results_immutable
        BEFORE UPDATE OR DELETE ON execution_results
        FOR EACH ROW EXECUTE FUNCTION reject_execution_result_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER execution_results_immutable ON execution_results")
    op.execute("DROP FUNCTION reject_execution_result_mutation()")
    op.execute("DROP TRIGGER execution_results_validate_insert ON execution_results")
    op.execute("DROP FUNCTION validate_execution_result_insert()")
    op.execute(
        "DROP TRIGGER simulated_learning_assignments_immutable ON simulated_learning_assignments"
    )
    op.execute("DROP FUNCTION reject_simulated_learning_assignment_mutation()")
    op.execute(
        "DROP TRIGGER simulated_learning_assignments_validate_insert "
        "ON simulated_learning_assignments"
    )
    op.execute("DROP FUNCTION validate_simulated_learning_assignment_insert()")
    op.drop_table("execution_results")
    op.drop_table("simulated_learning_assignments")
