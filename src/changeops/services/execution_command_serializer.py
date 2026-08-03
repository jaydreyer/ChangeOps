from changeops.db.models import ExecutionResult, JiraIssue, SimulatedLearningAssignment
from changeops.schemas.execution_commands import (
    ExecutionCommandPreparationResponse,
    ExecutionCommandResponse,
    ExecutionResultResponse,
    JiraIssueResponse,
    SimulatedLearningAssignmentResponse,
    UnsupportedExecutionActionResponse,
)
from changeops.services.execution_command_service import (
    ExecutionCommandPreparation,
    PreparedCommandItem,
)


def serialize_execution_command_preparation(
    result: ExecutionCommandPreparation,
) -> ExecutionCommandPreparationResponse:
    return ExecutionCommandPreparationResponse(
        approval_run_id=result.approval_run_id,
        approved_action_count=result.approved_action_count,
        eligible_action_count=result.eligible_action_count,
        prepared_command_count=len(result.commands),
        unsupported_approved_action_count=len(result.unsupported_items),
        commands=[serialize_execution_command(item) for item in result.commands],
        unsupported_items=[
            UnsupportedExecutionActionResponse(
                sequence=item.sequence,
                action_review_id=item.review_id,
                proposed_action_id=item.action.proposed_action_id,
                action_type=item.action.action_type,
                target_type=item.action.target_type,
                target_identifier=item.action.target_identifier,
                reason_code=item.unsupported.code,
                reason=item.unsupported.message,
            )
            for item in result.unsupported_items
        ],
        execution_performed=any(item.command.execution_results for item in result.commands),
    )


def serialize_execution_command(
    item: PreparedCommandItem,
) -> ExecutionCommandResponse:
    command = item.command
    execution_succeeded = any(
        result.status in {"succeeded", "already_applied"} for result in command.execution_results
    )
    execution_state = (
        "executed"
        if execution_succeeded
        else "execution_failed"
        if command.execution_results
        else "pending_execution"
    )
    return ExecutionCommandResponse(
        id=command.id,
        approval_run_id=command.approval_run_id,
        action_review_id=command.action_review_id,
        action_review_decision_id=command.action_review_decision_id,
        proposed_action_id=command.proposed_action_id,
        assessment_id=command.assessment_id,
        sequence=item.sequence,
        schema_version=command.schema_version,
        system=command.system,
        operation=command.operation,
        target_type=command.target_type,
        target_identifier=command.target_identifier,
        parameters=command.parameters_snapshot,
        effective_action=command.effective_action_snapshot,
        idempotency_key=command.idempotency_key,
        status=command.status,
        prepared_by=command.prepared_by,
        prepared_role=command.prepared_role,
        created_at=command.created_at,
        execution_state=execution_state,
        execution_results=[
            serialize_execution_result(result) for result in command.execution_results
        ],
        execution_performed=bool(command.execution_results),
    )


def serialize_execution_result(result: ExecutionResult) -> ExecutionResultResponse:
    return ExecutionResultResponse(
        id=result.id,
        execution_command_id=result.execution_command_id,
        status=result.status,
        outcome_code=result.outcome_code,
        message=result.message,
        command_idempotency_key=result.command_idempotency_key,
        attempted_by=result.attempted_by,
        attempted_role=result.attempted_role,
        created_at=result.created_at,
        learning_assignment=(
            serialize_learning_assignment(result.learning_assignment)
            if result.learning_assignment is not None
            else None
        ),
        jira_issue=(
            serialize_jira_issue(result.jira_issue) if result.jira_issue is not None else None
        ),
    )


def serialize_learning_assignment(
    assignment: SimulatedLearningAssignment,
) -> SimulatedLearningAssignmentResponse:
    return SimulatedLearningAssignmentResponse(
        id=assignment.id,
        worker_id=assignment.worker_id,
        training_course_id=assignment.training_course_id,
        source_execution_command_id=assignment.source_execution_command_id,
        source_approved_action_id=assignment.source_approved_action_id,
        assignment_status=assignment.assignment_status,
        assigned_at=assignment.assigned_at,
        created_at=assignment.created_at,
    )


def serialize_jira_issue(issue: JiraIssue) -> JiraIssueResponse:
    return JiraIssueResponse(
        id=issue.id,
        issue_id=issue.issue_id,
        issue_key=issue.issue_key,
        api_url=issue.api_url,
        browse_url=issue.browse_url,
        project_id_or_key=issue.project_id_or_key,
        execution_command_id=issue.execution_command_id,
        created_at=issue.created_at,
    )
