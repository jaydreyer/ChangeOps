from changeops.db.models import ImpactAssessment
from changeops.schemas.assessments import (
    ActionTarget,
    AssessmentSummary,
    EvidenceResponse,
    FindingResponse,
    ImpactAssessmentResponse,
    ProposedActionResponse,
    UnresolvedQuestionResponse,
    WorkerReference,
    WorkerResultResponse,
)


def serialize_assessment(
    assessment: ImpactAssessment,
) -> ImpactAssessmentResponse:
    worker_results = sorted(
        assessment.worker_results,
        key=lambda item: (item.worker_id, item.trip_id),
    )
    findings = sorted(
        assessment.findings,
        key=lambda item: (
            item.worker_result.worker_id,
            item.rule_code,
            item.finding_type,
        ),
    )
    evidence = sorted(
        assessment.evidence,
        key=lambda item: item.evidence_key,
    )
    proposed_actions = sorted(
        assessment.proposed_actions,
        key=lambda item: (
            item.worker_id,
            item.action_type,
            item.target_identifier,
        ),
    )
    unresolved_questions = sorted(
        assessment.unresolved_questions,
        key=lambda item: item.sequence,
    )

    return ImpactAssessmentResponse(
        id=assessment.id,
        policy_change_id=assessment.policy_change_id,
        status="completed",
        analyzer_version=assessment.analyzer_version,
        created_at=assessment.created_at,
        completed_at=assessment.completed_at,
        summary=AssessmentSummary(
            affected_workers=sum(item.classification == "affected" for item in worker_results),
            unaffected_workers=sum(item.classification == "unaffected" for item in worker_results),
            manager_approvals_required=sum(
                item.action_type == "manager_approval_request" for item in proposed_actions
            ),
            training_assignments_required=sum(
                item.action_type == "training_assignment" for item in proposed_actions
            ),
        ),
        worker_results=[
            WorkerResultResponse(
                worker=WorkerReference(
                    id=item.worker.id,
                    name=item.worker.full_name,
                ),
                trip_id=item.trip_id,
                classification=item.classification,
                explanation=item.explanation,
                reason_codes=list(item.reason_codes),
            )
            for item in worker_results
        ],
        findings=[
            FindingResponse(
                id=item.id,
                type=item.finding_type,
                severity=item.severity,
                rule_code=item.rule_code,
                worker_id=item.worker_result.worker_id,
                explanation=item.explanation,
                evidence_ids=[
                    evidence_item.id
                    for evidence_item in sorted(
                        item.evidence,
                        key=lambda evidence_item: evidence_item.evidence_key,
                    )
                ],
            )
            for item in findings
        ],
        evidence=[
            EvidenceResponse(
                id=item.id,
                type=item.evidence_type,
                source_type=item.source_type,
                source_id=item.source_id,
                label=item.label,
                snapshot=item.snapshot,
            )
            for item in evidence
        ],
        proposed_actions=[
            ProposedActionResponse(
                id=item.id,
                type=item.action_type,
                worker_id=item.worker_id,
                target=ActionTarget(
                    type=item.target_type,
                    identifier=item.target_identifier,
                ),
                description=item.description,
                due_date=item.due_date,
                execution_status="not_executed",
            )
            for item in proposed_actions
        ],
        unresolved_questions=[
            UnresolvedQuestionResponse(
                sequence=item.sequence,
                question=item.question,
            )
            for item in unresolved_questions
        ],
    )
