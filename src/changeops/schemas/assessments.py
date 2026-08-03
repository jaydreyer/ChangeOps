import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

ImpactDomain = Literal[
    "people",
    "teams",
    "systems",
    "documents",
    "training",
    "customer_commitments",
]
ImpactClassification = Literal[
    "directly_affected",
    "operationally_affected",
    "review_required",
    "update_required",
    "notification_required",
]
ImpactObjectType = Literal[
    "worker",
    "manager",
    "team",
    "enterprise_system",
    "enterprise_document",
    "training_course",
    "worker_training_requirement",
    "customer_commitment",
]
ActionType = Literal[
    "manager_approval_request",
    "training_assignment",
    "review_team_travel",
    "review_system_workflow",
    "operational_remediation",
    "update_document",
    "review_document",
    "review_customer_commitment",
]


class ImpactCountsByDomain(BaseModel):
    people: int
    teams: int
    systems: int
    documents: int
    training: int
    customer_commitments: int


class AssessmentSummary(BaseModel):
    affected_workers: int
    unaffected_workers: int
    manager_approvals_required: int
    training_assignments_required: int
    enterprise_impacts: int
    impacts_by_domain: ImpactCountsByDomain


class WorkerReference(BaseModel):
    id: str
    name: str


class WorkerResultResponse(BaseModel):
    worker: WorkerReference
    trip_id: str
    classification: Literal["affected", "unaffected"]
    explanation: str
    reason_codes: list[str]


class FindingResponse(BaseModel):
    id: uuid.UUID
    type: str
    severity: Literal["action_required", "informational"]
    rule_code: str
    worker_id: str
    explanation: str
    evidence_ids: list[uuid.UUID]


class EvidenceResponse(BaseModel):
    id: uuid.UUID
    type: str
    source_type: str
    source_id: str
    label: str
    snapshot: dict[str, Any]


class ActionTarget(BaseModel):
    type: str
    identifier: str


class ProposedActionResponse(BaseModel):
    id: uuid.UUID
    type: ActionType
    worker_id: str | None
    enterprise_impact_id: uuid.UUID | None
    target: ActionTarget
    description: str
    due_date: date | None
    execution_status: Literal["not_executed"]


class UnresolvedQuestionResponse(BaseModel):
    sequence: int
    question: str


class RelationshipPathElementResponse(BaseModel):
    sequence: int
    object_type: str
    stable_key: str
    display_label: str
    relationship_to_next: str | None


class EnterpriseImpactResponse(BaseModel):
    id: uuid.UUID
    domain: ImpactDomain
    object_type: ImpactObjectType
    source_key: str
    display_name: str
    classification: ImpactClassification
    explanation: str
    reason_code: str
    evidence_ids: list[uuid.UUID] = Field(min_length=1)
    relationship_path: list[RelationshipPathElementResponse] = Field(min_length=1)
    proposed_action_ids: list[uuid.UUID]
    sort_key: str

    @model_validator(mode="after")
    def validate_domain_classification(self) -> "EnterpriseImpactResponse":
        valid = {
            "people": {"directly_affected", "operationally_affected"},
            "teams": {"operationally_affected"},
            "systems": {"operationally_affected"},
            "documents": {"review_required", "update_required"},
            "training": {"operationally_affected", "notification_required"},
            "customer_commitments": {"review_required"},
        }
        if self.classification not in valid[self.domain]:
            raise ValueError(
                f"classification {self.classification!r} is invalid for domain {self.domain!r}"
            )
        return self


class CategorizedEnterpriseImpacts(BaseModel):
    people: list[EnterpriseImpactResponse]
    teams: list[EnterpriseImpactResponse]
    systems: list[EnterpriseImpactResponse]
    documents: list[EnterpriseImpactResponse]
    training: list[EnterpriseImpactResponse]
    customer_commitments: list[EnterpriseImpactResponse]


class ImpactAssessmentResponse(BaseModel):
    id: uuid.UUID
    policy_change_id: str
    status: Literal["completed"]
    analyzer_version: str
    input_fingerprint: str
    created_at: datetime
    completed_at: datetime
    summary: AssessmentSummary
    worker_results: list[WorkerResultResponse]
    findings: list[FindingResponse]
    evidence: list[EvidenceResponse]
    enterprise_impacts: CategorizedEnterpriseImpacts
    proposed_actions: list[ProposedActionResponse]
    unresolved_questions: list[UnresolvedQuestionResponse]
