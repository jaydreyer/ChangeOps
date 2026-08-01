from dataclasses import dataclass
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from changeops.domain.types import InternationalTravelPolicyRules

SupportStatus = Literal["supported", "unsupported"]
ValidationOutcome = Literal["accepted", "unsupported", "validation_failed"]


class SourceProvenance(BaseModel):
    field_path: str = Field(min_length=1)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_span_order(self) -> "SourceProvenance":
        if self.end <= self.start:
            raise ValueError("provenance end must be greater than start")
        return self


class ExtractionFinding(BaseModel):
    kind: Literal["unsupported", "unresolved"]
    code: str = Field(min_length=1, pattern=r"^[a-z0-9_]+$")
    message: str = Field(min_length=1)
    field_path: str | None = None
    provenance: SourceProvenance

    model_config = ConfigDict(extra="forbid", frozen=True)


class CandidateWorkerScope(BaseModel):
    assigned_work_country: str = Field(min_length=1)
    worker_types: tuple[str, ...]

    model_config = ConfigDict(extra="forbid", frozen=True)


class CandidateTripScope(BaseModel):
    origin_country: str = Field(min_length=1)
    excluded_destination_countries: tuple[str, ...]

    model_config = ConfigDict(extra="forbid", frozen=True)


class CandidateManagerApproval(BaseModel):
    booking_before_effective_date_is_exempt: bool

    model_config = ConfigDict(extra="forbid", frozen=True)


class CandidateSecurityTraining(BaseModel):
    course_name: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid", frozen=True)


class CandidateInternationalTravelPolicyRules(BaseModel):
    kind: Literal["international_travel"]
    schema_version: Literal[1]
    effective_date: date
    worker_scope: CandidateWorkerScope
    trip_scope: CandidateTripScope
    manager_approval: CandidateManagerApproval
    security_training: CandidateSecurityTraining

    model_config = ConfigDict(extra="forbid", frozen=True)


class PolicyExtractionProposal(BaseModel):
    policy_family: str = Field(min_length=1)
    support_status: SupportStatus
    candidate_rules: CandidateInternationalTravelPolicyRules | None = None
    provenance: tuple[SourceProvenance, ...]
    findings: tuple[ExtractionFinding, ...] = ()

    model_config = ConfigDict(extra="forbid", frozen=True)


class ValidationIssue(BaseModel):
    code: str
    message: str
    field_path: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)


@dataclass(frozen=True)
class TrainingCourseReference:
    identifier: str
    name: str
    active: bool


@dataclass(frozen=True)
class ExtractionValidationResult:
    outcome: ValidationOutcome
    accepted_rules: InternationalTravelPolicyRules | None
    issues: tuple[ValidationIssue, ...]
