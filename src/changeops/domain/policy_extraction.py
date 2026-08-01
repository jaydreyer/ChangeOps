from dataclasses import dataclass
from datetime import date
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator

from changeops.domain.types import InternationalTravelPolicyRules

SupportStatus = Literal["supported", "unsupported"]
ValidationOutcome = Literal["accepted", "unsupported", "validation_failed"]
CountryCode = Annotated[str, Field(pattern=r"^[A-Z]{2}$")]
WorkerType = Literal["employee", "contractor"]
MaterialFieldPath = Literal[
    "policy_family",
    "candidate_rules.kind",
    "candidate_rules.schema_version",
    "candidate_rules.effective_date",
    "candidate_rules.worker_scope.assigned_work_country",
    "candidate_rules.worker_scope.worker_types",
    "candidate_rules.trip_scope.origin_country",
    "candidate_rules.trip_scope.excluded_destination_countries",
    "candidate_rules.manager_approval.booking_before_effective_date_is_exempt",
    "candidate_rules.security_training.course_name",
]
MATERIAL_FIELD_PATHS = frozenset(get_args(MaterialFieldPath))


class SourceProvenance(BaseModel):
    field_path: MaterialFieldPath
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_span_order(self) -> "SourceProvenance":
        if self.end <= self.start:
            raise ValueError("provenance end must be greater than start")
        return self


class FindingSourceProvenance(BaseModel):
    field_path: str = Field(pattern=r"^finding\.[a-z0-9_]+$")
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_span_order(self) -> "FindingSourceProvenance":
        if self.end <= self.start:
            raise ValueError("provenance end must be greater than start")
        return self


class ExtractionFinding(BaseModel):
    kind: Literal["unsupported", "unresolved"]
    code: str = Field(min_length=1, pattern=r"^[a-z0-9_]+$")
    message: str = Field(min_length=1)
    field_path: str | None = None
    provenance: FindingSourceProvenance

    model_config = ConfigDict(extra="forbid", frozen=True)


class CandidateWorkerScope(BaseModel):
    assigned_work_country: CountryCode = Field(
        description=(
            "Two-letter uppercase country code normalized from the policy text, "
            "for example U.S. or United States becomes US."
        )
    )
    worker_types: tuple[WorkerType, ...] = Field(
        description=(
            "Singular normalized worker types; employees becomes employee and "
            "contractors becomes contractor."
        )
    )

    model_config = ConfigDict(extra="forbid", frozen=True)


class CandidateTripScope(BaseModel):
    origin_country: CountryCode = Field(
        description=(
            "Two-letter uppercase country code normalized from the policy text, "
            "for example United States becomes US."
        )
    )
    excluded_destination_countries: tuple[CountryCode, ...] = Field(
        description=("Two-letter uppercase country codes for every country named in the exclusion.")
    )

    model_config = ConfigDict(extra="forbid", frozen=True)


class CandidateManagerApproval(BaseModel):
    booking_before_effective_date_is_exempt: bool

    model_config = ConfigDict(extra="forbid", frozen=True)


class CandidateSecurityTraining(BaseModel):
    course_name: str = Field(
        min_length=1,
        description=(
            "Exact proper title of the course, excluding the generic word 'course' "
            "unless it is part of the title."
        ),
    )

    model_config = ConfigDict(extra="forbid", frozen=True)


class CandidateInternationalTravelPolicyRules(BaseModel):
    kind: Literal["international_travel"]
    schema_version: Literal[1]
    effective_date: date = Field(
        description=(
            "ISO 8601 date parsed from the policy's stated effective date; preserve "
            "the source year exactly."
        )
    )
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
