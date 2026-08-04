import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from changeops.config import get_settings
from changeops.db.models import (
    ActionApprovalRun,
    ActionApprovalRunItem,
    ActionReview,
    AssessmentEnterpriseImpact,
    Evidence,
    ExecutionCommand,
    ExecutionResult,
    PolicyComparison,
    PolicyComparisonImpactDelta,
)
from changeops.domain.action_review import (
    EditedActionSnapshot,
    OriginalActionSnapshot,
    derive_effective_approved_action,
)
from changeops.domain.execution_command import (
    ExecutionCommandCandidate,
    ExecutionMappingResult,
    UnsupportedExecutionMapping,
    command_idempotency_key,
    map_effective_action,
    snapshot_effective_action,
)
from changeops.domain.jira_execution import jira_issue_description


class ApprovalRunNotCompletedError(Exception):
    pass


class ExecutionCommandNotFoundError(Exception):
    pass


class ExecutionCommandInconsistentError(Exception):
    pass


class ExecutionCommandConflictError(Exception):
    pass


@dataclass(frozen=True)
class PreparedCommandItem:
    sequence: int
    command: ExecutionCommand


@dataclass(frozen=True)
class UnsupportedCommandItem:
    sequence: int
    review_id: uuid.UUID
    action: OriginalActionSnapshot
    unsupported: UnsupportedExecutionMapping


@dataclass(frozen=True)
class ExecutionCommandPreparation:
    approval_run_id: uuid.UUID
    approved_action_count: int
    eligible_action_count: int
    created_count: int
    commands: tuple[PreparedCommandItem, ...]
    unsupported_items: tuple[UnsupportedCommandItem, ...]


def prepare_execution_commands(
    session: Session,
    run_id: uuid.UUID,
    *,
    actor_identity: str,
    actor_role: str,
) -> ExecutionCommandPreparation:
    created_count = 0
    with session.begin():
        run = session.scalar(
            select(ActionApprovalRun).where(ActionApprovalRun.id == run_id).with_for_update()
        )
        if run is None:
            from changeops.services.action_approval_service import (
                ActionApprovalRunNotFoundError,
            )

            raise ActionApprovalRunNotFoundError(str(run_id))
        if run.status != "completed":
            raise ApprovalRunNotCompletedError(str(run_id))

        membership = _ordered_membership(session, run_id)
        existing_by_review = {
            command.action_review_id: command
            for command in session.scalars(
                select(ExecutionCommand)
                .where(ExecutionCommand.approval_run_id == run_id)
                .options(
                    selectinload(ExecutionCommand.execution_results).selectinload(
                        ExecutionResult.learning_assignment
                    ),
                    selectinload(ExecutionCommand.execution_results).selectinload(
                        ExecutionResult.jira_issue
                    ),
                )
            )
        }
        for item in membership:
            review = item.review
            if review.status != "approved":
                continue
            decision = _approval_decision(review)
            effective = _effective_action(review)
            command_id = (
                existing_by_review[item.action_review_id].id
                if item.action_review_id in existing_by_review
                else uuid.uuid4()
            )
            mapping = _map_effective_action(session, effective, command_id=command_id)
            if mapping.command is None:
                continue
            key = command_idempotency_key(
                approval_decision_id=str(decision.id),
                command=mapping.command,
            )
            existing = existing_by_review.get(review.id)
            if existing is not None:
                _validate_existing(existing, item, decision.id, mapping.command, key)
                continue

            command = ExecutionCommand(
                id=command_id,
                approval_run_id=run.id,
                action_review_id=review.id,
                action_review_decision_id=decision.id,
                proposed_action_id=item.proposed_action_id,
                assessment_id=item.assessment_id,
                schema_version=mapping.command.schema_version,
                system=mapping.command.system,
                operation=mapping.command.operation,
                target_type=mapping.command.target_type,
                target_identifier=mapping.command.target_identifier,
                parameters_snapshot=mapping.command.parameters,
                effective_action_snapshot=snapshot_effective_action(effective).model_dump(
                    mode="json"
                ),
                idempotency_key=key,
                status="pending_execution",
                prepared_by=actor_identity,
                prepared_role=actor_role,
                created_at=datetime.now(UTC),
            )
            session.add(command)
            session.flush()
            existing_by_review[review.id] = command
            created_count += 1

    return get_execution_command_preparation(
        session,
        run_id,
        created_count=created_count,
    )


def get_execution_command_preparation(
    session: Session,
    run_id: uuid.UUID,
    *,
    created_count: int = 0,
) -> ExecutionCommandPreparation:
    run = session.get(ActionApprovalRun, run_id)
    if run is None:
        from changeops.services.action_approval_service import ActionApprovalRunNotFoundError

        raise ActionApprovalRunNotFoundError(str(run_id))
    membership = _ordered_membership(session, run_id)
    commands_by_review = {
        command.action_review_id: command
        for command in session.scalars(
            select(ExecutionCommand)
            .where(ExecutionCommand.approval_run_id == run_id)
            .options(
                selectinload(ExecutionCommand.execution_results).selectinload(
                    ExecutionResult.learning_assignment
                ),
                selectinload(ExecutionCommand.execution_results).selectinload(
                    ExecutionResult.jira_issue
                ),
            )
        )
    }
    commands: list[PreparedCommandItem] = []
    unsupported: list[UnsupportedCommandItem] = []
    approved_count = 0
    eligible_count = 0
    for item in membership:
        review = item.review
        if review.status != "approved":
            continue
        approved_count += 1
        _approval_decision(review)
        effective = _effective_action(review)
        persisted = commands_by_review.get(review.id)
        mapping = _map_effective_action(
            session,
            effective,
            command_id=persisted.id if persisted is not None else uuid.UUID(int=0),
        )
        if mapping.command is not None:
            eligible_count += 1
            if persisted is not None:
                commands.append(PreparedCommandItem(sequence=item.sequence, command=persisted))
        elif persisted is not None:
            raise ExecutionCommandInconsistentError(
                "An unsupported approved action has a persisted execution command."
            )
        else:
            assert mapping.unsupported is not None
            unsupported.append(
                UnsupportedCommandItem(
                    sequence=item.sequence,
                    review_id=review.id,
                    action=effective,
                    unsupported=mapping.unsupported,
                )
            )
    if len(commands_by_review) != len(commands):
        raise ExecutionCommandInconsistentError(
            "A persisted execution command does not match approved run membership."
        )
    return ExecutionCommandPreparation(
        approval_run_id=run.id,
        approved_action_count=approved_count,
        eligible_action_count=eligible_count,
        created_count=created_count,
        commands=tuple(commands),
        unsupported_items=tuple(unsupported),
    )


def get_execution_command(
    session: Session,
    command_id: uuid.UUID,
) -> PreparedCommandItem:
    command = session.scalar(
        select(ExecutionCommand)
        .where(ExecutionCommand.id == command_id)
        .options(
            selectinload(ExecutionCommand.execution_results).selectinload(
                ExecutionResult.learning_assignment
            ),
            selectinload(ExecutionCommand.execution_results).selectinload(
                ExecutionResult.jira_issue
            ),
        )
    )
    if command is None:
        raise ExecutionCommandNotFoundError(str(command_id))
    sequence = session.scalar(
        select(ActionApprovalRunItem.sequence).where(
            ActionApprovalRunItem.approval_run_id == command.approval_run_id,
            ActionApprovalRunItem.action_review_id == command.action_review_id,
        )
    )
    if sequence is None:
        raise ExecutionCommandInconsistentError("Execution command membership cannot be resolved.")
    return PreparedCommandItem(sequence=sequence, command=command)


def _ordered_membership(
    session: Session,
    run_id: uuid.UUID,
) -> list[ActionApprovalRunItem]:
    return list(
        session.scalars(
            select(ActionApprovalRunItem)
            .where(ActionApprovalRunItem.approval_run_id == run_id)
            .options(
                selectinload(ActionApprovalRunItem.review).selectinload(ActionReview.decisions)
            )
            .order_by(ActionApprovalRunItem.sequence)
        )
    )


def _approval_decision(review: ActionReview):
    if len(review.decisions) != 1 or review.decisions[0].decision != "approved":
        raise ExecutionCommandInconsistentError(
            "An approved review must have exactly one approval decision."
        )
    return review.decisions[0]


def _effective_action(review: ActionReview) -> OriginalActionSnapshot:
    original = OriginalActionSnapshot.model_validate(review.original_action_snapshot)
    decision = _approval_decision(review)
    edited = (
        EditedActionSnapshot.model_validate(decision.edited_action_snapshot)
        if decision.edited_action_snapshot is not None
        else None
    )
    return derive_effective_approved_action(original, edited)


def _validate_existing(
    existing: ExecutionCommand,
    item: ActionApprovalRunItem,
    decision_id: uuid.UUID,
    candidate: ExecutionCommandCandidate,
    idempotency_key: str,
) -> None:
    linkage = (
        existing.approval_run_id,
        existing.action_review_id,
        existing.action_review_decision_id,
        existing.proposed_action_id,
        existing.assessment_id,
    )
    expected_linkage = (
        item.approval_run_id,
        item.action_review_id,
        decision_id,
        item.proposed_action_id,
        item.assessment_id,
    )
    if linkage != expected_linkage:
        raise ExecutionCommandConflictError(
            "The approved review already has a conflicting execution command."
        )
    if (
        existing.schema_version != candidate.schema_version
        or existing.system != candidate.system
        or existing.operation != candidate.operation
        or existing.target_type != candidate.target_type
        or existing.target_identifier != candidate.target_identifier
        or existing.parameters_snapshot != candidate.parameters
        or existing.idempotency_key != idempotency_key
    ):
        raise ExecutionCommandConflictError(
            "The approved review already has a command with different semantics."
        )


def _map_effective_action(
    session: Session,
    action: OriginalActionSnapshot,
    *,
    command_id: uuid.UUID,
) -> ExecutionMappingResult:
    if action.action_type != "operational_remediation":
        return map_effective_action(action)
    settings = get_settings()
    configured = (
        settings.jira_project_id_or_key,
        settings.jira_issue_type_id,
    )
    if not all(configured) or action.enterprise_impact_id is None:
        return map_effective_action(action)
    deltas = list(
        session.scalars(
            select(PolicyComparisonImpactDelta).where(
                PolicyComparisonImpactDelta.proposed_assessment_id == action.assessment_id
            )
        )
    )
    if len(deltas) != 1:
        return map_effective_action(action)
    delta = deltas[0]
    comparison = session.get(PolicyComparison, delta.policy_comparison_id)
    impact = session.scalar(
        select(AssessmentEnterpriseImpact)
        .where(
            AssessmentEnterpriseImpact.id == action.enterprise_impact_id,
            AssessmentEnterpriseImpact.assessment_id == action.assessment_id,
        )
        .options(selectinload(AssessmentEnterpriseImpact.evidence))
    )
    if comparison is None or impact is None:
        return map_effective_action(action)
    changes = [
        f"{difference.field_path.replace('_', ' ')}: "
        f"{difference.change_type.replace('_', ' ')} "
        f"({difference.baseline_value!s} → {difference.proposed_value!s})"
        for difference in comparison.differences
    ]
    proposed = comparison.proposed_policy_snapshot
    summary = f"Update {impact.display_name}"
    description = jira_issue_description(
        business_summary=(
            f"Update the source policy document to reflect the approved revision effective "
            f"{_human_date(proposed['effective_date'])}."
        ),
        policy_changes=changes,
        operational_impact=impact.explanation,
        deterministic_reason=f"{impact.explanation} (Reason: {impact.reason_code})",
        evidence=[_jira_evidence_summary(item) for item in impact.evidence],
        command_id=str(command_id),
        comparison_id=str(comparison.id),
        baseline_assessment_id=str(delta.baseline_assessment_id),
        proposed_assessment_id=str(delta.proposed_assessment_id),
        baseline_extraction_attempt_id=str(comparison.baseline_extraction_attempt_id),
        proposed_extraction_attempt_id=str(comparison.proposed_extraction_attempt_id),
    )
    candidate = ExecutionCommandCandidate(
        system="jira",
        operation="create_issue",
        target_type="enterprise_document",
        target_identifier=action.target_identifier,
        parameters={
            "project_id_or_key": settings.jira_project_id_or_key,
            "issue_type_id": settings.jira_issue_type_id,
            "summary": summary,
            "description": description,
            "execution_command_id": str(command_id),
            "comparison_id": str(comparison.id),
            "baseline_assessment_id": str(delta.baseline_assessment_id),
            "proposed_assessment_id": str(delta.proposed_assessment_id),
            "target_identifier": action.target_identifier,
        },
    )
    return map_effective_action(action, jira_command=candidate)


def _jira_evidence_summary(evidence: Evidence) -> str:
    snapshot = evidence.snapshot
    if evidence.source_type == "enterprise_document":
        return (
            f"{snapshot['title']}, version {snapshot['version']}, "
            f"published in {snapshot['source_system']}"
        )
    if evidence.source_type == "policy_change":
        return f"Approved revision effective {_human_date(snapshot['effective_date'])}"
    if evidence.source_type == "policy_document_dependency":
        return "Primary policy-document dependency requires an update"
    return evidence.label


def _human_date(value: str) -> str:
    parsed = date.fromisoformat(value)
    return f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"
