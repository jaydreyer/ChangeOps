import json
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from changeops.db.models import (
    ActionApprovalRun,
    ActionApprovalRunItem,
    AssessmentEnterpriseImpact,
    Evidence,
    Finding,
    ImpactAssessment,
)
from changeops.domain.action_review import OriginalActionSnapshot
from changeops.services.action_approval_service import get_action_approval_run
from changeops.services.assessment_service import get_impact_assessment


class ActionApprovalWorkbenchInconsistencyError(Exception):
    pass


@dataclass(frozen=True)
class ActionApprovalWorkbenchData:
    run: ActionApprovalRun
    assessment: ImpactAssessment
    items: tuple["ActionApprovalWorkbenchItemData", ...]


@dataclass(frozen=True)
class ActionApprovalWorkbenchItemData:
    membership: ActionApprovalRunItem
    finding: Finding | None
    enterprise_impact: AssessmentEnterpriseImpact | None
    evidence: tuple[Evidence, ...]


def get_action_approval_workbench(
    session: Session,
    run_id: uuid.UUID,
) -> ActionApprovalWorkbenchData:
    run = get_action_approval_run(session, run_id)
    assessment = get_impact_assessment(session, run.assessment_id)
    ordered_membership = sorted(run.items, key=lambda item: item.sequence)

    if len(ordered_membership) != run.total_action_count:
        raise _inconsistent("Approval membership does not match the run action count.")
    if [item.sequence for item in ordered_membership] != list(range(len(ordered_membership))):
        raise _inconsistent("Approval membership sequence is not contiguous.")

    findings = {item.id: item for item in assessment.findings}
    impacts = {item.id: item for item in assessment.enterprise_impacts}
    evidence_by_key = {item.evidence_key: item for item in assessment.evidence}
    proposed_action_ids = {item.id for item in assessment.proposed_actions}
    items: list[ActionApprovalWorkbenchItemData] = []

    for membership in ordered_membership:
        review = membership.review
        if (
            membership.assessment_id != assessment.id
            or membership.proposed_action_id not in proposed_action_ids
            or review.assessment_id != assessment.id
            or review.proposed_action_id != membership.proposed_action_id
        ):
            raise _inconsistent("Approval membership references inconsistent assessment data.")
        original = OriginalActionSnapshot.model_validate(review.original_action_snapshot)
        if (
            original.assessment_id != assessment.id
            or original.proposed_action_id != membership.proposed_action_id
        ):
            raise _inconsistent("An original action snapshot references inconsistent data.")

        context = review.review_context_snapshot
        finding_id = _optional_uuid(context.get("finding_id"), "finding")
        impact_id = _optional_uuid(context.get("enterprise_impact_id"), "enterprise impact")
        finding = findings.get(finding_id) if finding_id is not None else None
        impact = impacts.get(impact_id) if impact_id is not None else None
        if finding_id is not None and finding is None:
            raise _inconsistent("A review references a finding that cannot be resolved.")
        if impact_id is not None and impact is None:
            raise _inconsistent("A review references an enterprise impact that cannot be resolved.")

        evidence_keys = context.get("evidence_keys")
        if not isinstance(evidence_keys, list) or any(
            not isinstance(key, str) for key in evidence_keys
        ):
            raise _inconsistent("A review contains invalid evidence references.")
        missing = [key for key in evidence_keys if key not in evidence_by_key]
        if missing:
            raise _inconsistent(f"Review evidence reference cannot be resolved: {missing[0]}.")
        expected_evidence_keys = sorted(
            evidence.evidence_key
            for evidence in (
                impact.evidence
                if impact is not None
                else finding.evidence
                if finding is not None
                else []
            )
        )
        if evidence_keys != expected_evidence_keys:
            raise _inconsistent("Review evidence does not match its persisted context.")
        if impact is not None and not impact.path_elements:
            raise _inconsistent("An enterprise impact relationship path cannot be resolved.")

        expected_reason = (
            impact.reason_code
            if impact is not None
            else (finding.rule_code if finding is not None else None)
        )
        if context.get("reason_code") != expected_reason:
            raise _inconsistent("A review reason code does not match its persisted context.")
        items.append(
            ActionApprovalWorkbenchItemData(
                membership=membership,
                finding=finding,
                enterprise_impact=impact,
                evidence=tuple(evidence_by_key[key] for key in evidence_keys),
            )
        )

    return ActionApprovalWorkbenchData(
        run=run,
        assessment=assessment,
        items=tuple(items),
    )


def evidence_detail(evidence: Evidence) -> str:
    values = []
    for key in sorted(evidence.snapshot):
        if key == "policy_text":
            continue
        value = evidence.snapshot[key]
        rendered = (
            json.dumps(value, sort_keys=True, separators=(",", ":"))
            if isinstance(value, (dict, list))
            else str(value)
        )
        values.append(f"{key.replace('_', ' ')}: {rendered}")
    return "; ".join(values)


def _optional_uuid(value: object, label: str) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as error:
        raise _inconsistent(f"A review contains an invalid {label} reference.") from error


def _inconsistent(message: str) -> ActionApprovalWorkbenchInconsistencyError:
    return ActionApprovalWorkbenchInconsistencyError(message)
