import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from changeops.domain.policy_interpretation import ValidatedChangePlan


class ChangePlanResponse(BaseModel):
    id: uuid.UUID
    policy_analysis_run_id: uuid.UUID
    impact_assessment_id: uuid.UUID
    interpretation_attempt_id: uuid.UUID
    schema_version: str
    created_at: datetime
    change_plan: ValidatedChangePlan


class PolicyInterpretationAttemptResponse(BaseModel):
    id: uuid.UUID
    policy_analysis_run_id: uuid.UUID
    impact_assessment_id: uuid.UUID
    status: Literal["accepted", "invalid", "provider_failed"]
    raw_output: Any | None
    candidate_change_plan: dict[str, Any] | None
    validated_change_plan: dict[str, Any] | None
    validation_errors: list[dict[str, Any]]
    model_provider: str
    model_identifier: str
    prompt_version: str
    schema_version: str
    created_at: datetime
    completed_at: datetime
    failure_code: str | None
    failure_message: str | None
