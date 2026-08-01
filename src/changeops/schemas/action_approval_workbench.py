import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from changeops.schemas.action_approval import ActionApprovalRunResponse
from changeops.schemas.action_review import ActionReviewResponse
from changeops.schemas.assessments import RelationshipPathElementResponse


class ReviewerEvidenceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    source_type: Literal[
        "policy_quote",
        "deterministic_finding",
        "enterprise_impact",
        "relationship_path",
    ]
    label: str
    detail: str
    policy_quote: str | None = None
    reason_code: str | None = None
    relationship_path: list[str] = Field(default_factory=list)


class ApprovalWorkbenchFindingResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    finding_type: str
    severity: str
    rule_code: str
    worker_id: str
    explanation: str


class ApprovalWorkbenchEnterpriseImpactResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    domain: str
    object_type: str
    source_key: str
    display_name: str
    classification: str
    explanation: str
    reason_code: str
    relationship_path: list[RelationshipPathElementResponse]


class ApprovalWorkbenchItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    sequence: int
    review: ActionReviewResponse
    evidence: list[ReviewerEvidenceResponse]
    finding: ApprovalWorkbenchFindingResponse | None
    enterprise_impact: ApprovalWorkbenchEnterpriseImpactResponse | None


class ApprovalWorkbenchAssessmentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    policy_change_id: str
    completed_at: datetime
    affected_worker_count: int
    enterprise_impact_count: int
    proposed_action_count: int


class ActionApprovalWorkbenchResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    run: ActionApprovalRunResponse
    assessment: ApprovalWorkbenchAssessmentResponse
    items: list[ApprovalWorkbenchItemResponse]
