"""Add real Jira create-issue execution.

Revision ID: 0012_jira_execution
Revises: 0011_enterprise_impact_delta
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_jira_execution"
down_revision: str | None = "0011_enterprise_impact_delta"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_execution_commands_supported_mapping", "execution_commands", type_="check"
    )
    op.create_check_constraint(
        "ck_execution_commands_supported_mapping",
        "execution_commands",
        "(system = 'learning' AND operation = 'assign_training') OR "
        "(system = 'jira' AND operation = 'create_issue')",
    )
    op.execute("DROP TRIGGER execution_commands_validate_insert ON execution_commands")
    op.execute("DROP FUNCTION validate_execution_command_insert()")
    op.execute(
        """
        CREATE FUNCTION validate_execution_command_insert()
        RETURNS trigger AS $$
        DECLARE
            run_status text; review_status text; decision_value text;
            original_action jsonb; edited_action jsonb; authorized_effective_action jsonb;
            comparison_count integer;
        BEGIN
            SELECT status INTO run_status FROM action_approval_runs
            WHERE id = NEW.approval_run_id FOR UPDATE;
            SELECT status, original_action_snapshot INTO review_status, original_action
            FROM action_reviews WHERE id = NEW.action_review_id;
            SELECT decision, edited_action_snapshot INTO decision_value, edited_action
            FROM action_review_decisions WHERE id = NEW.action_review_decision_id
            AND action_review_id = NEW.action_review_id;
            IF run_status IS DISTINCT FROM 'completed' OR review_status IS DISTINCT FROM 'approved'
               OR decision_value IS DISTINCT FROM 'approved' THEN
                RAISE EXCEPTION 'execution command requires completed approved lineage';
            END IF;
            authorized_effective_action := original_action
                || jsonb_build_object('schema_version', 'effective-approved-action-v1')
                || COALESCE(edited_action, '{}'::jsonb);
            IF NEW.effective_action_snapshot IS DISTINCT FROM authorized_effective_action
               OR authorized_effective_action->>'proposed_action_id'
                  IS DISTINCT FROM NEW.proposed_action_id::text
               OR authorized_effective_action->>'assessment_id'
                  IS DISTINCT FROM NEW.assessment_id::text
               OR authorized_effective_action->>'target_type' IS DISTINCT FROM NEW.target_type
               OR authorized_effective_action->>'target_identifier'
                  IS DISTINCT FROM NEW.target_identifier
               OR authorized_effective_action->>'execution_status' IS DISTINCT FROM 'not_executed'
               OR jsonb_typeof(NEW.parameters_snapshot) IS DISTINCT FROM 'object' THEN
                RAISE EXCEPTION 'execution command snapshot is inconsistent';
            END IF;
            IF NEW.system = 'learning' THEN
                IF authorized_effective_action->>'action_type' <> 'training_assignment'
                   OR authorized_effective_action->>'target_type' <> 'worker'
                   OR authorized_effective_action->>'worker_id'
                      IS DISTINCT FROM authorized_effective_action->>'target_identifier'
                   OR NEW.parameters_snapshot->>'worker_identifier'
                      IS DISTINCT FROM authorized_effective_action->>'worker_id'
                   OR NEW.parameters_snapshot->>'course_identifier'
                      IS DISTINCT FROM 'international-travel-security'
                   OR NEW.parameters_snapshot->>'description'
                      IS DISTINCT FROM authorized_effective_action->>'description'
                   OR NEW.parameters_snapshot->'due_date'
                      IS DISTINCT FROM authorized_effective_action->'due_date' THEN
                    RAISE EXCEPTION 'learning command parameters are inconsistent';
                END IF;
            ELSE
                SELECT count(*) INTO comparison_count
                FROM policy_comparison_impact_deltas delta
                WHERE delta.policy_comparison_id =
                      (NEW.parameters_snapshot->>'comparison_id')::uuid
                  AND delta.baseline_assessment_id =
                      (NEW.parameters_snapshot->>'baseline_assessment_id')::uuid
                  AND delta.proposed_assessment_id = NEW.assessment_id;
                IF authorized_effective_action->>'action_type' <> 'operational_remediation'
                   OR authorized_effective_action->>'target_type' <> 'enterprise_document'
                   OR NEW.parameters_snapshot->>'execution_command_id' <> NEW.id::text
                   OR NEW.parameters_snapshot->>'target_identifier' <> NEW.target_identifier
                   OR NEW.parameters_snapshot->>'proposed_assessment_id' <> NEW.assessment_id::text
                   OR comparison_count <> 1 THEN
                    RAISE EXCEPTION 'jira command parameters are inconsistent';
                END IF;
            END IF;
            RETURN NEW;
        END; $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER execution_commands_validate_insert BEFORE INSERT ON execution_commands "
        "FOR EACH ROW EXECUTE FUNCTION validate_execution_command_insert()"
    )

    op.create_table(
        "jira_execution_deliveries",
        sa.Column("execution_command_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "state IN ('reserved', 'retryable_failure', 'outcome_unknown', 'succeeded')",
            name="ck_jira_execution_deliveries_state",
        ),
        sa.ForeignKeyConstraint(["execution_command_id"], ["execution_commands.id"]),
        sa.PrimaryKeyConstraint("execution_command_id"),
    )
    op.create_table(
        "jira_issues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("execution_command_id", sa.Uuid(), nullable=False),
        sa.Column("issue_id", sa.String(length=100), nullable=False),
        sa.Column("issue_key", sa.String(length=100), nullable=False),
        sa.Column("api_url", sa.Text(), nullable=False),
        sa.Column("browse_url", sa.Text(), nullable=False),
        sa.Column("project_id_or_key", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["execution_command_id"], ["execution_commands.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_command_id", name="uq_jira_issues_execution_command"),
        sa.UniqueConstraint("issue_id", name="uq_jira_issues_external_id"),
        sa.UniqueConstraint("issue_key", name="uq_jira_issues_external_key"),
    )
    op.create_index("ix_jira_issues_execution_command_id", "jira_issues", ["execution_command_id"])

    op.execute("DROP TRIGGER execution_results_validate_insert ON execution_results")
    op.execute("DROP FUNCTION validate_execution_result_insert()")
    op.drop_constraint(
        "ck_execution_results_assignment_outcome", "execution_results", type_="check"
    )
    op.drop_constraint("ck_execution_results_status", "execution_results", type_="check")
    op.add_column("execution_results", sa.Column("jira_issue_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_execution_results_jira_issue",
        "execution_results",
        "jira_issues",
        ["jira_issue_id"],
        ["id"],
    )
    op.create_index("ix_execution_results_jira_issue_id", "execution_results", ["jira_issue_id"])
    op.create_check_constraint(
        "ck_execution_results_status",
        "execution_results",
        "status IN ('succeeded', 'already_applied', 'rejected_unsupported', "
        "'failed_validation', 'failed_authentication', 'failed_unavailable')",
    )
    op.create_check_constraint(
        "ck_execution_results_assignment_outcome",
        "execution_results",
        "(status IN ('succeeded', 'already_applied') AND "
        "((simulated_learning_assignment_id IS NOT NULL AND jira_issue_id IS NULL) OR "
        "(simulated_learning_assignment_id IS NULL AND jira_issue_id IS NOT NULL))) OR "
        "(status IN ('rejected_unsupported', 'failed_validation', 'failed_authentication', "
        "'failed_unavailable') AND simulated_learning_assignment_id IS NULL "
        "AND jira_issue_id IS NULL)",
    )
    op.execute(
        """
        CREATE FUNCTION validate_execution_result_insert()
        RETURNS trigger AS $$
        DECLARE
            command_key text;
            artifact_command_id uuid;
        BEGIN
            SELECT idempotency_key INTO command_key FROM execution_commands
            WHERE id = NEW.execution_command_id;
            IF command_key IS NULL OR command_key IS DISTINCT FROM NEW.command_idempotency_key THEN
                RAISE EXCEPTION 'execution result is inconsistent with command identity';
            END IF;
            IF NEW.simulated_learning_assignment_id IS NOT NULL THEN
                SELECT source_execution_command_id INTO artifact_command_id
                FROM simulated_learning_assignments
                WHERE id = NEW.simulated_learning_assignment_id;
            ELSIF NEW.jira_issue_id IS NOT NULL THEN
                SELECT execution_command_id INTO artifact_command_id
                FROM jira_issues WHERE id = NEW.jira_issue_id;
            END IF;
            IF artifact_command_id IS NOT NULL
               AND artifact_command_id IS DISTINCT FROM NEW.execution_command_id THEN
                RAISE EXCEPTION 'execution result artifact belongs to another command';
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
        CREATE FUNCTION reject_jira_issue_mutation()
        RETURNS trigger AS $$ BEGIN
            RAISE EXCEPTION 'jira issue receipts are immutable';
        END; $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER jira_issues_immutable BEFORE UPDATE OR DELETE ON jira_issues
        FOR EACH ROW EXECUTE FUNCTION reject_jira_issue_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER jira_issues_immutable ON jira_issues")
    op.execute("DROP FUNCTION reject_jira_issue_mutation()")
    op.execute("DROP TRIGGER execution_results_validate_insert ON execution_results")
    op.execute("DROP FUNCTION validate_execution_result_insert()")
    op.drop_constraint(
        "ck_execution_results_assignment_outcome", "execution_results", type_="check"
    )
    op.drop_constraint("ck_execution_results_status", "execution_results", type_="check")
    op.drop_index("ix_execution_results_jira_issue_id", table_name="execution_results")
    op.drop_constraint("fk_execution_results_jira_issue", "execution_results", type_="foreignkey")
    op.drop_column("execution_results", "jira_issue_id")
    op.create_check_constraint(
        "ck_execution_results_status",
        "execution_results",
        "status IN ('succeeded', 'already_applied', 'rejected_unsupported', 'failed_validation')",
    )
    op.create_check_constraint(
        "ck_execution_results_assignment_outcome",
        "execution_results",
        "(status IN ('succeeded', 'already_applied') AND "
        "simulated_learning_assignment_id IS NOT NULL) OR "
        "(status IN ('rejected_unsupported', 'failed_validation') AND "
        "simulated_learning_assignment_id IS NULL)",
    )
    op.execute(
        """
        CREATE FUNCTION validate_execution_result_insert()
        RETURNS trigger AS $$
        DECLARE command_key text; assignment_command_id uuid;
        BEGIN
            SELECT idempotency_key INTO command_key FROM execution_commands
            WHERE id = NEW.execution_command_id;
            IF command_key IS NULL OR command_key IS DISTINCT FROM NEW.command_idempotency_key THEN
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
        END; $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER execution_results_validate_insert BEFORE INSERT ON execution_results "
        "FOR EACH ROW EXECUTE FUNCTION validate_execution_result_insert()"
    )
    op.drop_table("jira_issues")
    op.drop_table("jira_execution_deliveries")
    op.execute("DROP TRIGGER execution_commands_validate_insert ON execution_commands")
    op.execute("DROP FUNCTION validate_execution_command_insert()")
    op.drop_constraint(
        "ck_execution_commands_supported_mapping", "execution_commands", type_="check"
    )
    op.create_check_constraint(
        "ck_execution_commands_supported_mapping",
        "execution_commands",
        "system = 'learning' AND operation = 'assign_training'",
    )
    op.execute(
        """
        CREATE FUNCTION validate_execution_command_insert()
        RETURNS trigger AS $$
        DECLARE run_status text; review_status text; decision_value text;
            original_action jsonb; edited_action jsonb; authorized_effective_action jsonb;
        BEGIN
            SELECT status INTO run_status FROM action_approval_runs
            WHERE id = NEW.approval_run_id FOR UPDATE;
            SELECT status, original_action_snapshot INTO review_status, original_action
            FROM action_reviews WHERE id = NEW.action_review_id;
            SELECT decision, edited_action_snapshot INTO decision_value, edited_action
            FROM action_review_decisions WHERE id = NEW.action_review_decision_id
            AND action_review_id = NEW.action_review_id;
            authorized_effective_action := original_action
                || jsonb_build_object('schema_version', 'effective-approved-action-v1')
                || COALESCE(edited_action, '{}'::jsonb);
            IF run_status IS DISTINCT FROM 'completed' OR review_status IS DISTINCT FROM 'approved'
               OR decision_value IS DISTINCT FROM 'approved'
               OR NEW.effective_action_snapshot IS DISTINCT FROM authorized_effective_action
               OR authorized_effective_action->>'action_type' <> 'training_assignment'
               OR authorized_effective_action->>'target_type' <> 'worker'
               OR NEW.parameters_snapshot->>'worker_identifier'
                  IS DISTINCT FROM authorized_effective_action->>'worker_id'
               OR NEW.parameters_snapshot->>'course_identifier'
                  IS DISTINCT FROM 'international-travel-security'
               OR NEW.parameters_snapshot->>'description'
                  IS DISTINCT FROM authorized_effective_action->>'description'
               OR NEW.parameters_snapshot->'due_date'
                  IS DISTINCT FROM authorized_effective_action->'due_date' THEN
                RAISE EXCEPTION 'execution command effective action snapshot is inconsistent';
            END IF;
            RETURN NEW;
        END; $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER execution_commands_validate_insert BEFORE INSERT ON execution_commands "
        "FOR EACH ROW EXECUTE FUNCTION validate_execution_command_insert()"
    )
