from dataclasses import dataclass
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CountryCode = str


class WorkerScopeRules(BaseModel):
    assigned_work_country: CountryCode
    worker_types: tuple[str, ...]

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("assigned_work_country")
    @classmethod
    def validate_country(cls, value: str) -> str:
        if len(value) != 2 or value != value.upper():
            raise ValueError("country codes must be two uppercase characters")
        return value


class TripScopeRules(BaseModel):
    origin_country: CountryCode
    excluded_destination_countries: tuple[CountryCode, ...]

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("origin_country")
    @classmethod
    def validate_origin_country(cls, value: str) -> str:
        if len(value) != 2 or value != value.upper():
            raise ValueError("country codes must be two uppercase characters")
        return value

    @field_validator("excluded_destination_countries")
    @classmethod
    def validate_destination_countries(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(len(country) != 2 or country != country.upper() for country in value):
            raise ValueError("country codes must be two uppercase characters")
        return value


class ManagerApprovalRules(BaseModel):
    booking_before_effective_date_is_exempt: Literal[True]

    model_config = ConfigDict(extra="forbid", frozen=True)


class SecurityTrainingRules(BaseModel):
    course_identifier: str = Field(min_length=1)

    model_config = ConfigDict(extra="forbid", frozen=True)


class InternationalTravelPolicyRules(BaseModel):
    kind: Literal["international_travel"]
    schema_version: Literal[1]
    worker_scope: WorkerScopeRules
    trip_scope: TripScopeRules
    manager_approval: ManagerApprovalRules
    security_training: SecurityTrainingRules

    model_config = ConfigDict(extra="forbid", frozen=True)


@dataclass(frozen=True)
class PolicyInput:
    id: str
    title: str
    version: str
    effective_date: date
    policy_text: str
    rules: InternationalTravelPolicyRules


@dataclass(frozen=True)
class WorkerInput:
    id: str
    full_name: str
    worker_type: str
    department: str
    manager_name: str
    assigned_work_country: CountryCode


@dataclass(frozen=True)
class TripInput:
    id: str
    worker_id: str
    origin_country: CountryCode
    destination_country: CountryCode
    departure_date: date
    booking_date: date | None
    booking_status: str


@dataclass(frozen=True)
class TrainingInput:
    id: str
    worker_id: str
    course_identifier: str
    completion_status: str
    completion_date: date | None


@dataclass(frozen=True)
class WorkerAnalysis:
    worker_id: str
    trip_id: str
    classification: Literal["affected", "unaffected"]
    explanation: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class FindingResult:
    key: str
    worker_id: str
    finding_type: str
    severity: Literal["action_required", "informational"]
    rule_code: str
    explanation: str
    evidence_keys: tuple[str, ...]


@dataclass(frozen=True)
class ProposedActionResult:
    key: str
    finding_key: str
    worker_id: str
    action_type: str
    target_type: str
    target_identifier: str
    description: str
    due_date: date | None
    execution_status: Literal["not_executed"] = "not_executed"


@dataclass(frozen=True)
class AnalysisResult:
    worker_results: tuple[WorkerAnalysis, ...]
    findings: tuple[FindingResult, ...]
    proposed_actions: tuple[ProposedActionResult, ...]
