import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel


class AssessmentSummary(BaseModel):
    affected_workers: int
    unaffected_workers: int
    manager_approvals_required: int
    training_assignments_required: int


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
    type: str
    worker_id: str
    target: ActionTarget
    description: str
    due_date: date | None
    execution_status: Literal["not_executed"]


class UnresolvedQuestionResponse(BaseModel):
    sequence: int
    question: str


class ImpactAssessmentResponse(BaseModel):
    id: uuid.UUID
    policy_change_id: str
    status: Literal["completed"]
    analyzer_version: str
    created_at: datetime
    completed_at: datetime
    summary: AssessmentSummary
    worker_results: list[WorkerResultResponse]
    findings: list[FindingResponse]
    evidence: list[EvidenceResponse]
    proposed_actions: list[ProposedActionResponse]
    unresolved_questions: list[UnresolvedQuestionResponse]
