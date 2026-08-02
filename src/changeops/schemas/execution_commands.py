import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class ExecutionCommandResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    approval_run_id: uuid.UUID
    action_review_id: uuid.UUID
    action_review_decision_id: uuid.UUID
    proposed_action_id: uuid.UUID
    assessment_id: uuid.UUID
    sequence: int
    schema_version: Literal["execution-command-v1"]
    system: Literal["learning"]
    operation: Literal["assign_training"]
    target_type: str
    target_identifier: str
    parameters: dict[str, Any]
    effective_action: dict[str, Any]
    idempotency_key: str
    status: Literal["pending_execution"]
    prepared_by: str
    prepared_role: Literal["admin"]
    created_at: datetime
    execution_performed: Literal[False] = False


class UnsupportedExecutionActionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    sequence: int
    action_review_id: uuid.UUID
    proposed_action_id: uuid.UUID
    action_type: str
    target_type: str
    target_identifier: str
    reason_code: Literal["unsupported_action_type", "unsupported_target_type"]
    reason: str


class ExecutionCommandPreparationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    approval_run_id: uuid.UUID
    approved_action_count: int
    eligible_action_count: int
    prepared_command_count: int
    unsupported_approved_action_count: int
    commands: list[ExecutionCommandResponse]
    unsupported_items: list[UnsupportedExecutionActionResponse]
    execution_performed: Literal[False] = False
