import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from changeops.domain.policy_extraction import SourceProvenance, ValidationIssue
from changeops.domain.types import InternationalTravelPolicyRules


class ExtractionMetadataResponse(BaseModel):
    model_provider: str
    model_identifier: str
    prompt_version: str
    schema_version: str

    model_config = ConfigDict(extra="forbid")


class PolicyExtractionAttemptResponse(BaseModel):
    id: uuid.UUID
    policy_change_id: str
    policy_family: str | None
    support_status: Literal["supported", "unsupported"] | None
    validation_outcome: Literal["accepted", "unsupported", "validation_failed"]
    candidate_rules: dict[str, Any] | None
    accepted_rules: InternationalTravelPolicyRules | None
    provenance: list[SourceProvenance]
    findings: list[dict[str, Any]]
    validation_errors: list[ValidationIssue]
    raw_output: Any | None
    metadata: ExtractionMetadataResponse
    created_at: datetime

    model_config = ConfigDict(extra="forbid")
