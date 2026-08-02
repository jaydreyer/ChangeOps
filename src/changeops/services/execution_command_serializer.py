from changeops.schemas.execution_commands import (
    ExecutionCommandPreparationResponse,
    ExecutionCommandResponse,
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
        execution_performed=False,
    )


def serialize_execution_command(
    item: PreparedCommandItem,
) -> ExecutionCommandResponse:
    command = item.command
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
        execution_performed=False,
    )
