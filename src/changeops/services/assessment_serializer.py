import uuid

from changeops.db.models import ImpactAssessment
from changeops.schemas.assessments import (
    ActionTarget,
    AssessmentSummary,
    CategorizedEnterpriseImpacts,
    EnterpriseImpactResponse,
    EvidenceResponse,
    FindingResponse,
    ImpactAssessmentResponse,
    ImpactCountsByDomain,
    ProposedActionResponse,
    RelationshipPathElementResponse,
    UnresolvedQuestionResponse,
    WorkerReference,
    WorkerResultResponse,
)

IMPACT_DOMAINS = (
    "people",
    "teams",
    "systems",
    "documents",
    "training",
    "customer_commitments",
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
    evidence = sorted(assessment.evidence, key=lambda item: item.evidence_key)
    impacts = sorted(assessment.enterprise_impacts, key=lambda item: item.sort_key)
    proposed_actions = sorted(
        assessment.proposed_actions,
        key=lambda item: (
            item.worker_id or "",
            item.action_type,
            item.target_identifier,
        ),
    )
    unresolved_questions = sorted(
        assessment.unresolved_questions,
        key=lambda item: item.sequence,
    )

    action_ids_by_impact_id: dict[uuid.UUID, list[uuid.UUID]] = {}
    for action in proposed_actions:
        if action.enterprise_impact_id is not None:
            action_ids_by_impact_id.setdefault(action.enterprise_impact_id, []).append(action.id)

    serialized_impacts = [
        EnterpriseImpactResponse(
            id=item.id,
            domain=item.domain,
            object_type=item.object_type,
            source_key=item.source_key,
            display_name=item.display_name,
            classification=item.classification,
            explanation=item.explanation,
            reason_code=item.reason_code,
            evidence_ids=[
                evidence_item.id
                for evidence_item in sorted(
                    item.evidence,
                    key=lambda evidence_item: evidence_item.evidence_key,
                )
            ],
            relationship_path=[
                RelationshipPathElementResponse(
                    sequence=element.sequence,
                    object_type=element.object_type,
                    stable_key=element.stable_key,
                    display_label=element.display_label,
                    relationship_to_next=element.relationship_to_next,
                )
                for element in sorted(
                    item.path_elements,
                    key=lambda element: element.sequence,
                )
            ],
            proposed_action_ids=action_ids_by_impact_id.get(item.id, []),
            sort_key=item.sort_key,
        )
        for item in impacts
    ]
    impacts_by_domain = {
        domain: [item for item in serialized_impacts if item.domain == domain]
        for domain in IMPACT_DOMAINS
    }

    return ImpactAssessmentResponse(
        id=assessment.id,
        policy_change_id=assessment.policy_change_id,
        status="completed",
        analyzer_version=assessment.analyzer_version,
        input_fingerprint=assessment.input_fingerprint,
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
            enterprise_impacts=len(impacts),
            impacts_by_domain=ImpactCountsByDomain(
                **{domain: len(items) for domain, items in impacts_by_domain.items()}
            ),
        ),
        worker_results=[
            WorkerResultResponse(
                worker=WorkerReference(id=item.worker.id, name=item.worker.full_name),
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
        enterprise_impacts=CategorizedEnterpriseImpacts(**impacts_by_domain),
        proposed_actions=[
            ProposedActionResponse(
                id=item.id,
                type=item.action_type,
                worker_id=item.worker_id,
                enterprise_impact_id=item.enterprise_impact_id,
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
