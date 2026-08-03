import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CreatePolicyComparisonRequest(BaseModel):
    baseline_policy_change_id: str = Field(min_length=1)
    proposed_policy_change_id: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid")


class PolicyComparisonSourceResponse(BaseModel):
    policy_change_id: str
    title: str
    version: str
    effective_date: date
    accepted_extraction_attempt_id: uuid.UUID

    model_config = ConfigDict(extra="forbid")


class PolicyComparisonDifferenceResponse(BaseModel):
    id: uuid.UUID
    sequence: int
    rule_identity: str
    field_path: str
    change_type: Literal["added", "removed", "modified"]
    baseline_value: Any | None
    proposed_value: Any | None
    material: Literal[True]
    reason_code: str
    baseline_provenance: dict[str, Any] | None
    proposed_provenance: dict[str, Any] | None

    model_config = ConfigDict(extra="forbid")


class PolicyComparisonResponse(BaseModel):
    id: uuid.UUID
    organization_id: str
    baseline: PolicyComparisonSourceResponse
    proposed: PolicyComparisonSourceResponse
    comparison_contract_version: str
    comparison_fingerprint: str
    difference_count: int
    differences: list[PolicyComparisonDifferenceResponse]
    created_by: str
    created_at: datetime

    model_config = ConfigDict(extra="forbid")
