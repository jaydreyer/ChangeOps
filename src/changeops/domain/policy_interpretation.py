import uuid
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

INTERPRETATION_SCHEMA_VERSION = "policy-interpretation-v1"


class PolicySpanReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_change_id: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str = Field(min_length=1)


class ImpactReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment_id: uuid.UUID
    impact_id: uuid.UUID


class EvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment_id: uuid.UUID
    evidence_key: str = Field(min_length=1)
    impact_id: uuid.UUID | None = None
    finding_id: uuid.UUID | None = None


class RelationshipPathReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment_id: uuid.UUID
    impact_id: uuid.UUID
    sequence: int = Field(ge=0)


class CandidateCoverageGapFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_key: str = Field(min_length=1)
    title: str = Field(min_length=1)
    observed_limitation: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    recommended_review_action: str = Field(min_length=1)
    conclusion_type: Literal["review_concern"] = "review_concern"
    policy_spans: tuple[PolicySpanReference, ...] = Field(min_length=1)
    impact_references: tuple[ImpactReference, ...] = ()
    evidence_references: tuple[EvidenceReference, ...] = ()
    relationship_path_references: tuple[RelationshipPathReference, ...] = ()
    asserted_enterprise_facts: tuple[str, ...] = Field(default=(), max_length=0)
    impact_mutations: tuple[dict[str, Any], ...] = Field(default=(), max_length=0)


class CandidateChangePlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    coverage_gaps: tuple[CandidateCoverageGapFinding, ...] = ()


class InterpretationImpact(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    domain: str
    object_type: str
    source_key: str
    display_name: str
    classification: str
    explanation: str
    reason_code: str
    evidence_keys: tuple[str, ...]
    relationship_path: tuple[dict[str, Any], ...]


class InterpretationEvidence(BaseModel):
    id: uuid.UUID
    evidence_key: str
    evidence_type: str
    source_type: str
    source_id: str
    label: str
    snapshot: dict[str, Any]


class InterpretationFinding(BaseModel):
    id: uuid.UUID
    rule_code: str
    finding_type: str
    severity: str
    explanation: str
    evidence_keys: tuple[str, ...]


class InterpretationAction(BaseModel):
    id: uuid.UUID
    enterprise_impact_id: uuid.UUID | None
    action_type: str
    target_type: str
    target_identifier: str
    description: str
    due_date: date | None


class PolicyInterpretationInput(BaseModel):
    policy_change_id: str
    policy_text: str
    policy_effective_date: date
    policy_analysis_run_id: uuid.UUID
    accepted_extraction_attempt_id: uuid.UUID
    accepted_rules: dict[str, Any]
    accepted_source_provenance: tuple[dict[str, Any], ...]
    answered_clarifications: tuple[dict[str, Any], ...]
    impact_assessment_id: uuid.UUID
    assessment_summary: dict[str, Any]
    impacts: tuple[InterpretationImpact, ...]
    findings: tuple[InterpretationFinding, ...]
    evidence: tuple[InterpretationEvidence, ...]
    proposed_actions: tuple[InterpretationAction, ...]
    unresolved_questions: tuple[dict[str, Any], ...]
    prompt_version: str
    schema_version: str


class ValidatedChangePlan(CandidateChangePlan):
    schema_version: Literal["policy-interpretation-v1"] = INTERPRETATION_SCHEMA_VERSION


class InterpretationValidationIssue(BaseModel):
    code: str
    message: str
    finding_key: str | None = None


class ChangePlanValidationError(Exception):
    def __init__(self, issues: tuple[InterpretationValidationIssue, ...]) -> None:
        self.issues = issues
        super().__init__("; ".join(item.message for item in issues))
