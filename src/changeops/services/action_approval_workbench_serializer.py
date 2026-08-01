from changeops.schemas.action_approval_workbench import (
    ActionApprovalWorkbenchResponse,
    ApprovalWorkbenchAssessmentResponse,
    ApprovalWorkbenchEnterpriseImpactResponse,
    ApprovalWorkbenchFindingResponse,
    ApprovalWorkbenchItemResponse,
    ReviewerEvidenceResponse,
)
from changeops.schemas.assessments import RelationshipPathElementResponse
from changeops.services.action_approval_serializer import serialize_action_approval_run
from changeops.services.action_approval_workbench_service import (
    ActionApprovalWorkbenchData,
    evidence_detail,
)
from changeops.services.action_review_serializer import serialize_action_review


def serialize_action_approval_workbench(
    data: ActionApprovalWorkbenchData,
) -> ActionApprovalWorkbenchResponse:
    assessment = data.assessment
    return ActionApprovalWorkbenchResponse(
        run=serialize_action_approval_run(data.run),
        assessment=ApprovalWorkbenchAssessmentResponse(
            id=assessment.id,
            policy_change_id=assessment.policy_change_id,
            completed_at=assessment.completed_at,
            affected_worker_count=sum(
                item.classification == "affected" for item in assessment.worker_results
            ),
            enterprise_impact_count=len(assessment.enterprise_impacts),
            proposed_action_count=len(assessment.proposed_actions),
        ),
        items=[
            ApprovalWorkbenchItemResponse(
                sequence=item.membership.sequence,
                review=serialize_action_review(item.membership.review),
                evidence=[
                    ReviewerEvidenceResponse(
                        key=evidence.evidence_key,
                        source_type=(
                            "policy_quote"
                            if evidence.source_type == "policy_change"
                            else (
                                "enterprise_impact"
                                if item.enterprise_impact is not None
                                else "deterministic_finding"
                            )
                        ),
                        label=evidence.label,
                        detail=evidence_detail(evidence),
                        policy_quote=(
                            evidence.snapshot.get("policy_text")
                            if evidence.source_type == "policy_change"
                            else None
                        ),
                        reason_code=item.membership.review.review_context_snapshot.get(
                            "reason_code"
                        ),
                    )
                    for evidence in item.evidence
                ]
                + _relationship_evidence(item),
                finding=(
                    ApprovalWorkbenchFindingResponse(
                        id=item.finding.id,
                        finding_type=item.finding.finding_type,
                        severity=item.finding.severity,
                        rule_code=item.finding.rule_code,
                        worker_id=item.finding.worker_result.worker_id,
                        explanation=item.finding.explanation,
                    )
                    if item.finding is not None
                    else None
                ),
                enterprise_impact=(
                    ApprovalWorkbenchEnterpriseImpactResponse(
                        id=item.enterprise_impact.id,
                        domain=item.enterprise_impact.domain,
                        object_type=item.enterprise_impact.object_type,
                        source_key=item.enterprise_impact.source_key,
                        display_name=item.enterprise_impact.display_name,
                        classification=item.enterprise_impact.classification,
                        explanation=item.enterprise_impact.explanation,
                        reason_code=item.enterprise_impact.reason_code,
                        relationship_path=[
                            RelationshipPathElementResponse(
                                sequence=element.sequence,
                                object_type=element.object_type,
                                stable_key=element.stable_key,
                                display_label=element.display_label,
                                relationship_to_next=element.relationship_to_next,
                            )
                            for element in sorted(
                                item.enterprise_impact.path_elements,
                                key=lambda element: element.sequence,
                            )
                        ],
                    )
                    if item.enterprise_impact is not None
                    else None
                ),
            )
            for item in data.items
        ],
    )


def _relationship_evidence(item) -> list[ReviewerEvidenceResponse]:
    if item.enterprise_impact is None:
        return []
    elements = sorted(item.enterprise_impact.path_elements, key=lambda element: element.sequence)
    path = [element.display_label for element in elements]
    if not path:
        return []
    return [
        ReviewerEvidenceResponse(
            key=f"relationship-path:{item.enterprise_impact.id}",
            source_type="relationship_path",
            label="Ordered relationship path",
            detail=" → ".join(path),
            reason_code=item.enterprise_impact.reason_code,
            relationship_path=path,
        )
    ]
