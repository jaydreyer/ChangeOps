from changeops.db.models import PolicyExtractionAttempt
from changeops.schemas.policy_extractions import (
    ExtractionMetadataResponse,
    PolicyExtractionAttemptResponse,
)


def serialize_policy_extraction_attempt(
    attempt: PolicyExtractionAttempt,
) -> PolicyExtractionAttemptResponse:
    parsed_output = attempt.parsed_output or {}
    return PolicyExtractionAttemptResponse.model_validate(
        {
            "id": attempt.id,
            "policy_change_id": attempt.policy_change_id,
            "policy_family": parsed_output.get("policy_family"),
            "support_status": attempt.support_status,
            "validation_outcome": attempt.validation_outcome,
            "candidate_rules": attempt.candidate_rules,
            "accepted_rules": attempt.accepted_rules,
            "provenance": attempt.provenance,
            "findings": attempt.findings,
            "validation_errors": attempt.validation_errors,
            "raw_output": attempt.raw_output,
            "metadata": ExtractionMetadataResponse(
                model_provider=attempt.model_provider,
                model_identifier=attempt.model_identifier,
                prompt_version=attempt.prompt_version,
                schema_version=attempt.schema_version,
            ),
            "created_at": attempt.created_at,
        }
    )
