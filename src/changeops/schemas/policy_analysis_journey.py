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


class PolicyAnalysisEntryResponse(BaseModel):
    policies: list[AnalysisJourneyPolicyResponse]
    recent_runs: list[AnalysisJourneyRunSummaryResponse]

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


class InterpretationJourneyResponse(BaseModel):
    status: Literal["not_available", "not_created", "available", "failed"]
    failure_code: str | None
    change_plan: ChangePlanResponse | None

    model_config = ConfigDict(extra="forbid")


class ApprovalRunReferenceResponse(BaseModel):
    id: uuid.UUID
    status: str

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

    model_config = ConfigDict(extra="forbid")
