from changeops.db.models import PolicyAnalysisRun
from changeops.schemas.policy_analysis import (
    PolicyAnalysisMetadataResponse,
    PolicyAnalysisRunResponse,
)


def serialize_policy_analysis_run(run: PolicyAnalysisRun) -> PolicyAnalysisRunResponse:
    return PolicyAnalysisRunResponse.model_validate(
        {
            "id": run.id,
            "organization_id": run.organization_id,
            "policy_change_id": run.policy_change_id,
            "status": run.status,
            "current_step": run.current_step,
            "latest_extraction_attempt_id": run.latest_extraction_attempt_id,
            "assessment_id": run.assessment_id,
            "retry_count": run.retry_count,
            "failure_code": run.failure_code,
            "failure_detail": run.failure_detail,
            "accepted_rule_provenance": run.accepted_rule_provenance,
            "clarifications": [
                {
                    "id": item.id,
                    "question_code": item.question_code,
                    "question_text": item.question_text,
                    "expected_answer_contract": item.expected_answer_contract,
                    "affected_fields": item.affected_fields,
                    "status": item.status,
                    "answer": item.answer,
                    "responder_identity": item.responder_identity,
                    "answer_provenance": item.answer_provenance,
                    "created_at": item.created_at,
                    "answered_at": item.answered_at,
                }
                for item in run.clarifications
            ],
            "metadata": PolicyAnalysisMetadataResponse(
                workflow_version=run.workflow_version,
                model_provider=run.model_provider,
                model_identifier=run.model_identifier,
                prompt_version=run.prompt_version,
                schema_version=run.schema_version,
            ),
            "created_at": run.created_at,
            "updated_at": run.updated_at,
            "completed_at": run.completed_at,
        }
    )
