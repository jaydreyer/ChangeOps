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


class ImpactDeltaEvidenceResponse(BaseModel):
    record_id: uuid.UUID
    evidence_key: str
    evidence_type: str
    source_type: str
    source_id: str
    label: str
    snapshot: dict[str, Any]

    model_config = ConfigDict(extra="forbid")


class WorkerDeltaSideResponse(BaseModel):
    worker_id: str
    display_name: str
    trip_id: str
    classification: Literal["affected", "unaffected"]
    explanation: str
    reason_codes: list[str]
    evidence: list[ImpactDeltaEvidenceResponse]

    model_config = ConfigDict(extra="forbid")


class FindingDeltaSideResponse(BaseModel):
    worker_id: str
    trip_id: str
    finding_type: str
    severity: str
    rule_code: str
    explanation: str
    evidence: list[ImpactDeltaEvidenceResponse]

    model_config = ConfigDict(extra="forbid")


class ImpactDeltaPathElementResponse(BaseModel):
    sequence: int
    object_type: str
    stable_key: str
    display_label: str
    relationship_to_next: str | None

    model_config = ConfigDict(extra="forbid")


class EnterpriseImpactDeltaSideResponse(BaseModel):
    domain: str
    object_type: str
    source_key: str
    display_name: str
    classification: str
    explanation: str
    reason_code: str
    evidence: list[ImpactDeltaEvidenceResponse]
    relationship_path: list[ImpactDeltaPathElementResponse]

    model_config = ConfigDict(extra="forbid")


class WorkerDeltaResponse(BaseModel):
    id: uuid.UUID
    sequence: int
    stable_identity: str
    change_type: Literal["became_affected", "no_longer_affected", "remained_affected"]
    delta_reason_code: str
    baseline_record_id: uuid.UUID | None
    proposed_record_id: uuid.UUID | None
    baseline: WorkerDeltaSideResponse | None
    proposed: WorkerDeltaSideResponse | None

    model_config = ConfigDict(extra="forbid")


class FindingDeltaResponse(BaseModel):
    id: uuid.UUID
    sequence: int
    stable_identity: str
    change_type: Literal["introduced", "disappeared"]
    delta_reason_code: str
    baseline_record_id: uuid.UUID | None
    proposed_record_id: uuid.UUID | None
    baseline: FindingDeltaSideResponse | None
    proposed: FindingDeltaSideResponse | None

    model_config = ConfigDict(extra="forbid")


class EnterpriseImpactDeltaResponse(BaseModel):
    id: uuid.UUID
    sequence: int
    stable_identity: str
    change_type: Literal["introduced", "removed"]
    delta_reason_code: str
    baseline_record_id: uuid.UUID | None
    proposed_record_id: uuid.UUID | None
    baseline: EnterpriseImpactDeltaSideResponse | None
    proposed: EnterpriseImpactDeltaSideResponse | None

    model_config = ConfigDict(extra="forbid")


class ImpactDeltaSummaryResponse(BaseModel):
    workers_became_affected: int
    workers_no_longer_affected: int
    workers_remained_affected: int
    findings_introduced: int
    findings_disappeared: int
    enterprise_impacts_introduced: int
    enterprise_impacts_removed: int

    model_config = ConfigDict(extra="forbid")


class PolicyComparisonImpactDeltaResponse(BaseModel):
    id: uuid.UUID
    baseline_assessment_id: uuid.UUID
    proposed_assessment_id: uuid.UUID
    impact_delta_contract_version: str
    impact_delta_fingerprint: str
    summary: ImpactDeltaSummaryResponse
    worker_deltas: list[WorkerDeltaResponse]
    finding_deltas: list[FindingDeltaResponse]
    enterprise_impact_deltas: list[EnterpriseImpactDeltaResponse]
    created_by: str
    created_at: datetime

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
    impact_delta: PolicyComparisonImpactDeltaResponse | None
    created_by: str
    created_at: datetime

    model_config = ConfigDict(extra="forbid")
