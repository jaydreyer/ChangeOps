from dataclasses import dataclass
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CountryCode = str
ImpactDomain = Literal[
    "people",
    "teams",
    "systems",
    "documents",
    "training",
    "customer_commitments",
]
ImpactClassification = Literal[
    "directly_affected",
    "operationally_affected",
    "review_required",
    "update_required",
    "notification_required",
]


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
    manager_worker_id: str | None = None
    team_id: str | None = None


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
class TeamInput:
    id: str
    name: str
    manager_worker_id: str


@dataclass(frozen=True)
class TeamMembershipInput:
    id: str
    worker_id: str
    team_id: str


@dataclass(frozen=True)
class EnterpriseSystemInput:
    id: str
    name: str
    system_type: str
    description: str
    active: bool


@dataclass(frozen=True)
class EnterpriseDocumentInput:
    id: str
    title: str
    document_type: str
    source_system: str
    version: str
    status: str


@dataclass(frozen=True)
class TrainingCourseInput:
    id: str
    course_code: str
    name: str
    active: bool


@dataclass(frozen=True)
class PolicySystemDependencyInput:
    id: str
    rule_code: str
    system_id: str
    relationship_type: str
    explanation: str


@dataclass(frozen=True)
class PolicyDocumentDependencyInput:
    id: str
    rule_code: str
    document_id: str
    relationship_type: str
    impact_classification: Literal["review_required", "update_required"]
    explanation: str


@dataclass(frozen=True)
class PolicyTrainingDependencyInput:
    id: str
    rule_code: str
    course_id: str
    relationship_type: str
    explanation: str


@dataclass(frozen=True)
class CustomerCommitmentInput:
    id: str
    customer_name: str
    commitment_type: str
    description: str
    start_date: date
    end_date: date
    status: str


@dataclass(frozen=True)
class CommitmentAssignmentInput:
    id: str
    commitment_id: str
    worker_id: str
    assignment_role: str
    required: bool


@dataclass(frozen=True)
class QuestionInput:
    id: str
    sequence: int
    question: str


@dataclass(frozen=True)
class EnterpriseContextInput:
    teams: tuple[TeamInput, ...]
    team_memberships: tuple[TeamMembershipInput, ...]
    systems: tuple[EnterpriseSystemInput, ...]
    documents: tuple[EnterpriseDocumentInput, ...]
    courses: tuple[TrainingCourseInput, ...]
    system_dependencies: tuple[PolicySystemDependencyInput, ...]
    document_dependencies: tuple[PolicyDocumentDependencyInput, ...]
    training_dependencies: tuple[PolicyTrainingDependencyInput, ...]
    commitments: tuple[CustomerCommitmentInput, ...]
    commitment_assignments: tuple[CommitmentAssignmentInput, ...]
    questions: tuple[QuestionInput, ...]


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
class RelationshipPathElementResult:
    object_type: str
    stable_key: str
    display_label: str
    relationship_to_next: str | None


@dataclass(frozen=True)
class EnterpriseImpactResult:
    key: str
    domain: ImpactDomain
    object_type: str
    source_key: str
    display_name: str
    classification: ImpactClassification
    explanation: str
    reason_code: str
    evidence_keys: tuple[str, ...]
    relationship_path: tuple[RelationshipPathElementResult, ...]
    sort_key: str


@dataclass(frozen=True)
class EnterpriseProposedActionResult:
    key: str
    impact_key: str
    action_type: str
    target_type: str
    target_identifier: str
    description: str
    due_date: date | None = None
    worker_id: str | None = None
    execution_status: Literal["not_executed"] = "not_executed"


@dataclass(frozen=True)
class EnterpriseAnalysisResult:
    impacts: tuple[EnterpriseImpactResult, ...]
    proposed_actions: tuple[EnterpriseProposedActionResult, ...]


@dataclass(frozen=True)
class AnalysisResult:
    worker_results: tuple[WorkerAnalysis, ...]
    findings: tuple[FindingResult, ...]
    proposed_actions: tuple[ProposedActionResult, ...]
