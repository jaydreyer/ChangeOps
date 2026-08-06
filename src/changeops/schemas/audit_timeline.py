import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, JsonValue


class AuditActorCategory(StrEnum):
    AI_ASSISTED = "ai_assisted"
    DETERMINISTIC_SYSTEM = "deterministic_system"
    HUMAN = "human"
    EXTERNAL_SYSTEM = "external_system"


class AuditOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"
    REQUESTED = "requested"
    COMPLETED = "completed"
    PREVENTED = "prevented"
    RECORDED = "recorded"


class AuditEventType(StrEnum):
    ANALYSIS_REQUESTED = "analysis_requested"
    ANALYSIS_FAILED = "analysis_failed"
    EXTRACTION_ATTEMPTED = "extraction_attempted"
    EXTRACTION_ACCEPTED = "extraction_accepted"
    EXTRACTION_REJECTED = "extraction_rejected"
    CLARIFICATION_REQUESTED = "clarification_requested"
    CLARIFICATION_ANSWERED = "clarification_answered"
    ASSESSMENT_CREATED = "assessment_created"
    IMPACT_ASSESSMENT_COMPLETED = "impact_assessment_completed"
    INTERPRETATION_ATTEMPTED = "interpretation_attempted"
    INTERPRETATION_ACCEPTED = "interpretation_accepted"
    INTERPRETATION_FAILED = "interpretation_failed"
    CHANGE_PLAN_CREATED = "change_plan_created"
    COMPARISON_CREATED = "comparison_created"
    IMPACT_DELTA_CREATED = "impact_delta_created"
    ACTION_REVIEW_CREATED = "action_review_created"
    HUMAN_ACTION_DECISION_RECORDED = "human_action_decision_recorded"
    APPROVAL_COMPLETED = "approval_completed"
    APPROVAL_FAILED = "approval_failed"
    EXECUTION_COMMAND_PREPARED = "execution_command_prepared"
    EXECUTION_REQUESTED = "execution_requested"
    EXECUTION_SUCCEEDED = "execution_succeeded"
    SIMULATED_SIDE_EFFECT_CREATED = "simulated_side_effect_created"
    JIRA_ISSUE_CREATED = "jira_issue_created"
    EXECUTION_REPLAY_PREVENTED = "execution_replay_prevented"
    EXECUTION_FAILED = "execution_failed"


class AuditArtifactReference(BaseModel):
    artifact_type: str
    artifact_id: str
    href: str | None = None


class AuditTimelineEntry(BaseModel):
    entry_key: str
    occurred_at: datetime
    actor_category: AuditActorCategory
    actor_identity: str | None = None
    event_type: AuditEventType
    title: str
    description: str
    outcome: AuditOutcome
    artifact: AuditArtifactReference
    metadata: dict[str, JsonValue] = Field(default_factory=dict)


class AuditTimelineResponse(BaseModel):
    subject_type: str
    subject_id: uuid.UUID
    entries: list[AuditTimelineEntry]
