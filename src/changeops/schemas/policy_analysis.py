import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from changeops.domain.policy_analysis import FailureCode, RunStatus, RunStep


class CreatePolicyAnalysisRunRequest(BaseModel):
    policy_change_id: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class ClarificationAnswerRequest(BaseModel):
    value: StrictBool
    responder_identity: str = Field(min_length=1, max_length=200)

    model_config = ConfigDict(extra="forbid")


class PolicyAnalysisClarificationResponse(BaseModel):
    id: uuid.UUID
    question_code: str
    question_text: str
    expected_answer_contract: dict[str, Any]
    affected_fields: list[str]
    status: Literal["pending", "answered", "superseded"]
    answer: dict[str, Any] | None
    responder_identity: str | None
    answer_provenance: dict[str, Any] | None
    created_at: datetime
    answered_at: datetime | None

    model_config = ConfigDict(extra="forbid")


class PolicyAnalysisMetadataResponse(BaseModel):
    workflow_version: str
    model_provider: str
    model_identifier: str
    prompt_version: str
    schema_version: str

    model_config = ConfigDict(extra="forbid")


class PolicyAnalysisRunResponse(BaseModel):
    id: uuid.UUID
    organization_id: str
    policy_change_id: str
    status: RunStatus
    current_step: RunStep
    latest_extraction_attempt_id: uuid.UUID | None
    assessment_id: uuid.UUID | None
    retry_count: int
    failure_code: FailureCode | None
    failure_detail: str | None
    accepted_rule_provenance: list[dict[str, Any]]
    clarifications: list[PolicyAnalysisClarificationResponse]
    metadata: PolicyAnalysisMetadataResponse
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(extra="forbid")
