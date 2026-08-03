import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from changeops.domain.policy_extraction import SourceProvenance, ValidationIssue
from changeops.schemas.assessments import (
    AssessmentSummary,
    CategorizedEnterpriseImpacts,
    EvidenceResponse,
    FindingResponse,
    ProposedActionResponse,
    WorkerResultResponse,
)
from changeops.schemas.policy_analysis import (
    PolicyAnalysisClarificationResponse,
    PolicyAnalysisRunResponse,
)
from changeops.schemas.policy_extractions import ExtractionMetadataResponse
from changeops.schemas.policy_interpretation import ChangePlanResponse


class AnalysisJourneyPolicyResponse(BaseModel):
    id: str
    organization_id: str
    organization_name: str
    title: str
    owner: str
    version: str
    effective_date: date
    policy_text: str

    model_config = ConfigDict(extra="forbid")


class AnalysisJourneyRunSummaryResponse(BaseModel):
    id: uuid.UUID
    policy_change_id: str
    status: str
    current_step: str
    assessment_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(extra="forbid")


class PolicyComparisonReadinessResponse(BaseModel):
    ready: bool
    status: str
    accepted_extraction_attempt_id: uuid.UUID | None

    model_config = ConfigDict(extra="forbid")


class AnalysisEntryPolicyResponse(AnalysisJourneyPolicyResponse):
    comparison_readiness: PolicyComparisonReadinessResponse


class PolicyComparisonSummaryResponse(BaseModel):
    id: uuid.UUID
    baseline_policy_change_id: str
    proposed_policy_change_id: str
    difference_count: int
    created_at: datetime

    model_config = ConfigDict(extra="forbid")


class PolicyAnalysisEntryResponse(BaseModel):
    policies: list[AnalysisEntryPolicyResponse]
    recent_runs: list[AnalysisJourneyRunSummaryResponse]
    recent_comparisons: list[PolicyComparisonSummaryResponse]

    model_config = ConfigDict(extra="forbid")


class AnalysisJourneyExtractionResponse(BaseModel):
    id: uuid.UUID
    policy_change_id: str
    policy_family: str | None
    support_status: Literal["supported", "unsupported"] | None
    validation_outcome: Literal["accepted", "unsupported", "validation_failed"]
    candidate_rules: dict[str, Any] | None
    accepted_rules: dict[str, Any] | None
    provenance: list[SourceProvenance]
    findings: list[dict[str, Any]]
    validation_errors: list[ValidationIssue]
    metadata: ExtractionMetadataResponse
    created_at: datetime

    model_config = ConfigDict(extra="forbid")


class AnalysisUncertaintyResponse(BaseModel):
    extraction_findings: list[dict[str, Any]]
    clarifications: list[PolicyAnalysisClarificationResponse]
    legacy_assessment_questions: Literal["omitted_schema_v1_fixture"]

    model_config = ConfigDict(extra="forbid")


class AnalysisJourneyAssessmentResponse(BaseModel):
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
    enterprise_impacts: CategorizedEnterpriseImpacts
    proposed_actions: list[ProposedActionResponse]

    model_config = ConfigDict(extra="forbid")


class EnterpriseCoverageObjectResponse(BaseModel):
    id: str
    display_name: str
    classification: Literal["affected", "cleared"]
    impact_ids: list[uuid.UUID]

    model_config = ConfigDict(extra="forbid")


class EnterpriseCoverageDomainResponse(BaseModel):
    domain: Literal["systems", "documents", "teams", "customer_commitments"]
    considered: int
    affected: int
    cleared: int
    objects: list[EnterpriseCoverageObjectResponse]

    model_config = ConfigDict(extra="forbid")


class ResolvedImpactReferenceResponse(BaseModel):
    impact_id: uuid.UUID
    display_name: str
    domain: str
    classification: str
    reason_code: str

    model_config = ConfigDict(extra="forbid")


class ResolvedEvidenceReferenceResponse(BaseModel):
    evidence_key: str
    label: str
    evidence_type: str
    source_type: str
    source_id: str

    model_config = ConfigDict(extra="forbid")


class ResolvedPolicySpanReferenceResponse(BaseModel):
    policy_change_id: str
    start: int
    end: int
    quote: str
    validated_against_policy_snapshot: Literal[True]

    model_config = ConfigDict(extra="forbid")


class ResolvedCoverageGapReferencesResponse(BaseModel):
    finding_key: str
    impacts: list[ResolvedImpactReferenceResponse]
    evidence: list[ResolvedEvidenceReferenceResponse]
    policy_spans: list[ResolvedPolicySpanReferenceResponse]

    model_config = ConfigDict(extra="forbid")


class InterpretationJourneyResponse(BaseModel):
    status: Literal["not_available", "not_created", "available", "failed"]
    failure_code: str | None
    change_plan: ChangePlanResponse | None
    resolved_references: list[ResolvedCoverageGapReferencesResponse]

    model_config = ConfigDict(extra="forbid")


class ApprovalRunReferenceResponse(BaseModel):
    id: uuid.UUID
    status: str

    model_config = ConfigDict(extra="forbid")


class ExecutionJourneySummaryResponse(BaseModel):
    status: Literal["unavailable", "eligible", "command_prepared", "executed", "failed"]
    command_count: int
    executed_command_count: int
    result_count: int
    replay_count: int

    model_config = ConfigDict(extra="forbid")


class PolicyAnalysisJourneyResponse(BaseModel):
    policy: AnalysisJourneyPolicyResponse
    run: PolicyAnalysisRunResponse
    extraction: AnalysisJourneyExtractionResponse | None
    uncertainty: AnalysisUncertaintyResponse
    assessment: AnalysisJourneyAssessmentResponse | None
    enterprise_coverage: list[EnterpriseCoverageDomainResponse]
    interpretation: InterpretationJourneyResponse
    approval_run: ApprovalRunReferenceResponse | None
    execution: ExecutionJourneySummaryResponse

    model_config = ConfigDict(extra="forbid")
