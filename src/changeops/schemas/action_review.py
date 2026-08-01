import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ActionReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str
    rationale: str
    edited_action: dict[str, Any] | None = None


class OriginalActionSnapshotResponse(BaseModel):
    schema_version: Literal["action-review-v1"]
    proposed_action_id: uuid.UUID
    assessment_id: uuid.UUID
    finding_id: uuid.UUID | None
    enterprise_impact_id: uuid.UUID | None
    worker_id: str | None
    action_type: str
    target_type: str
    target_identifier: str
    description: str
    due_date: date | None
    execution_status: Literal["not_executed"]


class ReviewContextResponse(BaseModel):
    finding_id: uuid.UUID | None
    enterprise_impact_id: uuid.UUID | None
    reason_code: str | None
    evidence_keys: list[str]


class EditedActionResponse(BaseModel):
    description: str | None = None
    due_date: date | None = None


class ActionReviewDecisionResponse(BaseModel):
    id: uuid.UUID
    action_review_id: uuid.UUID
    decision: Literal["approved", "rejected", "deferred", "revision_requested"]
    reviewer_identity: str
    reviewer_role: Literal["reviewer", "admin"]
    rationale: str
    edited_action: EditedActionResponse | None
    created_at: datetime


class ActionReviewResponse(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    proposed_action_id: uuid.UUID
    status: Literal[
        "pending",
        "approved",
        "rejected",
        "deferred",
        "revision_requested",
    ]
    original_action: OriginalActionSnapshotResponse
    review_context: ReviewContextResponse
    decision_history: list[ActionReviewDecisionResponse] = Field(default_factory=list)
    current_decision: ActionReviewDecisionResponse | None
    effective_approved_action: OriginalActionSnapshotResponse | None
    created_at: datetime
    completed_at: datetime | None
