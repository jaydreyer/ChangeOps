import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from changeops.domain.action_review import OriginalActionSnapshot

EFFECTIVE_ACTION_SCHEMA_VERSION = "effective-approved-action-v1"
EXECUTION_COMMAND_SCHEMA_VERSION = "execution-command-v1"
INTERNATIONAL_TRAVEL_SECURITY_COURSE_ID = "international-travel-security"

ExecutionCommandStatus = Literal["pending_execution"]
ExecutionSystem = Literal["learning", "jira"]
ExecutionOperation = Literal["assign_training", "create_issue"]
UnsupportedReasonCode = Literal["unsupported_action_type", "unsupported_target_type"]


class EffectiveApprovedActionSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["effective-approved-action-v1"] = EFFECTIVE_ACTION_SCHEMA_VERSION
    proposed_action_id: str
    assessment_id: str
    finding_id: str | None
    enterprise_impact_id: str | None
    worker_id: str | None
    action_type: str
    target_type: str
    target_identifier: str
    description: str
    due_date: str | None
    execution_status: Literal["not_executed"]


class ExecutionCommandCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["execution-command-v1"] = EXECUTION_COMMAND_SCHEMA_VERSION
    system: ExecutionSystem
    operation: ExecutionOperation
    target_type: str
    target_identifier: str
    parameters: dict[str, Any]


class UnsupportedExecutionMapping(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: UnsupportedReasonCode
    message: str


class ExecutionMappingResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    command: ExecutionCommandCandidate | None = None
    unsupported: UnsupportedExecutionMapping | None = None


def snapshot_effective_action(
    action: OriginalActionSnapshot,
) -> EffectiveApprovedActionSnapshot:
    return EffectiveApprovedActionSnapshot(
        proposed_action_id=str(action.proposed_action_id),
        assessment_id=str(action.assessment_id),
        finding_id=str(action.finding_id) if action.finding_id is not None else None,
        enterprise_impact_id=(
            str(action.enterprise_impact_id) if action.enterprise_impact_id is not None else None
        ),
        worker_id=action.worker_id,
        action_type=action.action_type,
        target_type=action.target_type,
        target_identifier=action.target_identifier,
        description=action.description,
        due_date=action.due_date.isoformat() if action.due_date is not None else None,
        execution_status=action.execution_status,
    )


def map_effective_action(
    action: OriginalActionSnapshot,
    *,
    jira_command: ExecutionCommandCandidate | None = None,
) -> ExecutionMappingResult:
    if action.action_type == "operational_remediation":
        if action.target_type != "enterprise_document":
            return ExecutionMappingResult(
                unsupported=UnsupportedExecutionMapping(
                    code="unsupported_target_type",
                    message="Operational remediation requires an enterprise-document target.",
                )
            )
        if jira_command is None:
            return ExecutionMappingResult(
                unsupported=UnsupportedExecutionMapping(
                    code="unsupported_action_type",
                    message="Operational remediation requires immutable comparison lineage.",
                )
            )
        return ExecutionMappingResult(command=jira_command)
    if action.action_type != "training_assignment":
        return ExecutionMappingResult(
            unsupported=UnsupportedExecutionMapping(
                code="unsupported_action_type",
                message=f"Action type '{action.action_type}' has no execution mapping.",
            )
        )
    if action.target_type != "worker" or action.worker_id != action.target_identifier:
        return ExecutionMappingResult(
            unsupported=UnsupportedExecutionMapping(
                code="unsupported_target_type",
                message=(
                    "Training assignments require a worker target whose identifier "
                    "matches the approved action worker."
                ),
            )
        )
    return ExecutionMappingResult(
        command=ExecutionCommandCandidate(
            system="learning",
            operation="assign_training",
            target_type="worker",
            target_identifier=action.target_identifier,
            parameters={
                "course_identifier": INTERNATIONAL_TRAVEL_SECURITY_COURSE_ID,
                "description": action.description,
                "due_date": action.due_date.isoformat() if action.due_date is not None else None,
                "worker_identifier": action.target_identifier,
            },
        )
    )


def command_idempotency_key(
    *,
    approval_decision_id: str,
    command: ExecutionCommandCandidate,
) -> str:
    semantic_payload = {
        "schema_version": command.schema_version,
        "approval_decision_id": approval_decision_id,
        "system": command.system,
        "operation": command.operation,
        "target_type": command.target_type,
        "target_identifier": command.target_identifier,
        "parameters": command.parameters,
    }
    canonical = json.dumps(
        semantic_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
