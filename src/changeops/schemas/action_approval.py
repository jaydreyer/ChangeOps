import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ApprovalSummaryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    total: int
    pending: int
    approved: int
    rejected: int
    deferred: int
    revision_requested: int


class ActionApprovalRunItemResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    sequence: int
    proposed_action_id: uuid.UUID
    review_id: uuid.UUID
    review_status: Literal[
        "pending",
        "approved",
        "rejected",
        "deferred",
        "revision_requested",
    ]
    assessment_url: str
    review_url: str


class ActionApprovalTransitionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    from_status: str | None
    to_status: str
    from_step: str | None
    to_step: str
    reason_code: str
    trigger_type: str
    trigger_reference: str | None
    actor_identity: str | None
    created_at: datetime


class ActionApprovalRunResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: uuid.UUID
    assessment_id: uuid.UUID
    policy_analysis_run_id: uuid.UUID
    status: Literal["initializing", "awaiting_decisions", "completed", "failed"]
    current_step: Literal[
        "create_reviews",
        "evaluate_reviews",
        "await_decisions",
        "finalize",
    ]
    summary: ApprovalSummaryResponse
    failure_code: str | None
    failure_message: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    items: list[ActionApprovalRunItemResponse]
    transitions: list[ActionApprovalTransitionResponse]
