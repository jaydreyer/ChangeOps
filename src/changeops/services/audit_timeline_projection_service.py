import uuid
from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from changeops.db.models import (
    ActionApprovalRun,
    ActionReview,
    ActionReviewDecision,
    ChangePlan,
    ExecutionCommand,
    ExecutionResult,
    ImpactAssessment,
    JiraIssue,
    PolicyAnalysisClarification,
    PolicyAnalysisRun,
    PolicyComparison,
    PolicyComparisonImpactDelta,
    PolicyExtractionAttempt,
    PolicyInterpretationAttempt,
    SimulatedLearningAssignment,
)
from changeops.schemas.audit_timeline import (
    AuditActorCategory,
    AuditArtifactReference,
    AuditEventType,
    AuditOutcome,
    AuditTimelineEntry,
    AuditTimelineResponse,
)


class AuditTimelineNotFoundError(Exception):
    pass


EVENT_PRECEDENCE = {
    event_type: index
    for index, event_type in enumerate(
        (
            AuditEventType.ANALYSIS_REQUESTED,
            AuditEventType.EXTRACTION_ATTEMPTED,
            AuditEventType.EXTRACTION_ACCEPTED,
            AuditEventType.EXTRACTION_REJECTED,
            AuditEventType.CLARIFICATION_REQUESTED,
            AuditEventType.CLARIFICATION_ANSWERED,
            AuditEventType.ASSESSMENT_CREATED,
            AuditEventType.IMPACT_ASSESSMENT_COMPLETED,
            AuditEventType.INTERPRETATION_ATTEMPTED,
            AuditEventType.INTERPRETATION_ACCEPTED,
            AuditEventType.INTERPRETATION_FAILED,
            AuditEventType.CHANGE_PLAN_CREATED,
            AuditEventType.COMPARISON_CREATED,
            AuditEventType.IMPACT_DELTA_CREATED,
            AuditEventType.ACTION_REVIEW_CREATED,
            AuditEventType.HUMAN_ACTION_DECISION_RECORDED,
            AuditEventType.APPROVAL_COMPLETED,
            AuditEventType.APPROVAL_FAILED,
            AuditEventType.EXECUTION_COMMAND_PREPARED,
            AuditEventType.EXECUTION_REQUESTED,
            AuditEventType.EXECUTION_SUCCEEDED,
            AuditEventType.SIMULATED_SIDE_EFFECT_CREATED,
            AuditEventType.JIRA_ISSUE_CREATED,
            AuditEventType.EXECUTION_REPLAY_PREVENTED,
            AuditEventType.EXECUTION_FAILED,
            AuditEventType.ANALYSIS_FAILED,
        )
    )
}


def get_audit_timeline(
    session: Session,
    run_id: uuid.UUID,
) -> AuditTimelineResponse:
    run = session.get(PolicyAnalysisRun, run_id)
    if run is None:
        raise AuditTimelineNotFoundError(str(run_id))

    attempts = list(
        session.scalars(
            select(PolicyExtractionAttempt).where(
                PolicyExtractionAttempt.policy_analysis_run_id == run.id
            )
        )
    )
    clarifications = list(
        session.scalars(
            select(PolicyAnalysisClarification).where(
                PolicyAnalysisClarification.policy_analysis_run_id == run.id
            )
        )
    )
    assessment = session.scalar(
        select(ImpactAssessment).where(ImpactAssessment.policy_analysis_run_id == run.id)
    )
    interpretations = list(
        session.scalars(
            select(PolicyInterpretationAttempt).where(
                PolicyInterpretationAttempt.policy_analysis_run_id == run.id
            )
        )
    )
    change_plans = list(
        session.scalars(
            select(ChangePlan).where(ChangePlan.policy_analysis_run_id == run.id)
        )
    )
    attempt_ids = [attempt.id for attempt in attempts]
    comparisons = (
        list(
            session.scalars(
                select(PolicyComparison).where(
                    (PolicyComparison.baseline_extraction_attempt_id.in_(attempt_ids))
                    | (PolicyComparison.proposed_extraction_attempt_id.in_(attempt_ids))
                )
            )
        )
        if attempt_ids
        else []
    )
    impact_deltas = (
        list(
            session.scalars(
                select(PolicyComparisonImpactDelta).where(
                    (PolicyComparisonImpactDelta.baseline_assessment_id == assessment.id)
                    | (PolicyComparisonImpactDelta.proposed_assessment_id == assessment.id)
                )
            )
        )
        if assessment is not None
        else []
    )
    approval = session.scalar(
        select(ActionApprovalRun).where(ActionApprovalRun.policy_analysis_run_id == run.id)
    )

    reviews: list[ActionReview] = []
    decisions: list[ActionReviewDecision] = []
    commands: list[ExecutionCommand] = []
    results: list[ExecutionResult] = []
    assignments: list[SimulatedLearningAssignment] = []
    jira_issues: list[JiraIssue] = []
    if assessment is not None:
        reviews = list(
            session.scalars(
                select(ActionReview).where(ActionReview.assessment_id == assessment.id)
            )
        )
        review_ids = [review.id for review in reviews]
        if review_ids:
            decisions = list(
                session.scalars(
                    select(ActionReviewDecision).where(
                        ActionReviewDecision.action_review_id.in_(review_ids)
                    )
                )
            )
    if approval is not None:
        commands = list(
            session.scalars(
                select(ExecutionCommand).where(
                    ExecutionCommand.approval_run_id == approval.id
                )
            )
        )
        command_ids = [command.id for command in commands]
        if command_ids:
            results = list(
                session.scalars(
                    select(ExecutionResult).where(
                        ExecutionResult.execution_command_id.in_(command_ids)
                    )
                )
            )
            assignments = list(
                session.scalars(
                    select(SimulatedLearningAssignment).where(
                        SimulatedLearningAssignment.source_execution_command_id.in_(command_ids)
                    )
                )
            )
            jira_issues = list(
                session.scalars(
                    select(JiraIssue).where(JiraIssue.execution_command_id.in_(command_ids))
                )
            )

    run_href = f"/policy-analyses/{run.id}"
    approval_href = f"/approvals/{approval.id}" if approval is not None else None
    entries = map_analysis_run(run, run_href)
    entries.extend(
        map_extraction_attempts(
            attempts,
            run_href,
            linked_attempt_id=run.latest_extraction_attempt_id,
        )
    )
    entries.extend(map_clarifications(clarifications, run_href))
    if assessment is not None:
        entries.extend(map_assessment(assessment, run_href))
    linked_interpretation_attempt_ids = {plan.interpretation_attempt_id for plan in change_plans}
    if not linked_interpretation_attempt_ids and interpretations:
        linked_interpretation_attempt_ids.add(
            max(interpretations, key=lambda item: (item.created_at, item.id)).id
        )
    entries.extend(
        map_interpretation_attempts(
            interpretations,
            run_href,
            linked_attempt_ids=linked_interpretation_attempt_ids,
        )
    )
    entries.extend(map_change_plans(change_plans, run_href))
    entries.extend(map_policy_comparisons(comparisons))
    entries.extend(map_impact_deltas(impact_deltas))
    entries.extend(map_action_reviews(reviews, approval_href))
    entries.extend(map_action_decisions(decisions, reviews, approval_href))
    if approval is not None:
        entries.extend(map_approval_run(approval, approval_href))
    entries.extend(map_execution_commands(commands, approval_href))
    entries.extend(map_execution_results(results, approval_href))
    entries.extend(map_learning_assignments(assignments, approval_href))
    entries.extend(map_jira_issues(jira_issues))
    entries.sort(key=_sort_key)
    return AuditTimelineResponse(
        subject_type="policy_analysis_run",
        subject_id=run.id,
        entries=entries,
    )


def map_analysis_run(run: PolicyAnalysisRun, href: str | None) -> list[AuditTimelineEntry]:
    entries = [
        _entry(
            key=f"policy_analysis_run:{run.id}:requested",
            occurred_at=run.created_at,
            actor=AuditActorCategory.DETERMINISTIC_SYSTEM,
            event=AuditEventType.ANALYSIS_REQUESTED,
            title="Policy analysis requested",
            description=(
                f"ChangeOps stored an analysis journey for policy {run.policy_change_id}."
            ),
            outcome=AuditOutcome.REQUESTED,
            artifact_type="policy_analysis_run",
            artifact_id=run.id,
            href=href,
            metadata={"workflow_version": run.workflow_version},
        )
    ]
    if run.status == "failed":
        entries.append(
            _entry(
                key=f"policy_analysis_run:{run.id}:failed",
                occurred_at=run.completed_at or run.updated_at,
                actor=AuditActorCategory.DETERMINISTIC_SYSTEM,
                event=AuditEventType.ANALYSIS_FAILED,
                title="Policy analysis failed",
                description=run.failure_detail or "The policy analysis could not complete.",
                outcome=AuditOutcome.FAILED,
                artifact_type="policy_analysis_run",
                artifact_id=run.id,
                href=href,
                metadata=_compact_metadata(failure_code=run.failure_code),
            )
        )
    return entries


def map_extraction_attempts(
    attempts: Iterable[PolicyExtractionAttempt],
    run_href: str | None,
    *,
    linked_attempt_id: uuid.UUID | None = None,
) -> list[AuditTimelineEntry]:
    entries: list[AuditTimelineEntry] = []
    for attempt in attempts:
        href = (
            _anchor(run_href, "extraction-heading")
            if linked_attempt_id == attempt.id
            else None
        )
        metadata = _compact_metadata(
            model_provider=attempt.model_provider,
            model_identifier=attempt.model_identifier,
            prompt_version=attempt.prompt_version,
            retry_reason=attempt.retry_reason,
        )
        entries.append(
            _entry(
                key=f"policy_extraction_attempt:{attempt.id}:attempted",
                occurred_at=attempt.created_at,
                actor=AuditActorCategory.AI_ASSISTED,
                event=AuditEventType.EXTRACTION_ATTEMPTED,
                title="Policy meaning extraction attempted",
                description="An AI-assisted extractor proposed structured policy rules.",
                outcome=AuditOutcome.COMPLETED,
                artifact_type="policy_extraction_attempt",
                artifact_id=attempt.id,
                href=href,
                metadata=metadata,
            )
        )
        accepted = attempt.validation_outcome == "accepted"
        entries.append(
            _entry(
                key=f"policy_extraction_attempt:{attempt.id}:validation",
                occurred_at=attempt.created_at,
                actor=AuditActorCategory.DETERMINISTIC_SYSTEM,
                event=(
                    AuditEventType.EXTRACTION_ACCEPTED
                    if accepted
                    else AuditEventType.EXTRACTION_REJECTED
                ),
                title="Extraction accepted" if accepted else "Extraction rejected",
                description=(
                    "Deterministic validation accepted the proposed policy rules."
                    if accepted
                    else "Deterministic validation did not accept the proposed policy rules."
                ),
                outcome=AuditOutcome.SUCCEEDED if accepted else AuditOutcome.REJECTED,
                artifact_type="policy_extraction_attempt",
                artifact_id=attempt.id,
                href=href,
                metadata=_compact_metadata(
                    validation_outcome=attempt.validation_outcome,
                    support_status=attempt.support_status,
                    validation_error_count=len(attempt.validation_errors),
                ),
            )
        )
    return entries


def map_clarifications(
    clarifications: Iterable[PolicyAnalysisClarification],
    run_href: str | None,
) -> list[AuditTimelineEntry]:
    entries: list[AuditTimelineEntry] = []
    for clarification in clarifications:
        href = _anchor(run_href, "clarification-heading")
        entries.append(
            _entry(
                key=f"policy_analysis_clarification:{clarification.id}:requested",
                occurred_at=clarification.created_at,
                actor=AuditActorCategory.DETERMINISTIC_SYSTEM,
                event=AuditEventType.CLARIFICATION_REQUESTED,
                title="Clarification requested",
                description=clarification.question_text,
                outcome=AuditOutcome.REQUESTED,
                artifact_type="policy_analysis_clarification",
                artifact_id=clarification.id,
                href=href,
                metadata={"question_code": clarification.question_code},
            )
        )
        if clarification.answered_at is not None:
            entries.append(
                _entry(
                    key=f"policy_analysis_clarification:{clarification.id}:answered",
                    occurred_at=clarification.answered_at,
                    actor=AuditActorCategory.HUMAN,
                    actor_identity=clarification.responder_identity,
                    event=AuditEventType.CLARIFICATION_ANSWERED,
                    title="Clarification answered",
                    description="A trusted responder supplied the requested policy clarification.",
                    outcome=AuditOutcome.RECORDED,
                    artifact_type="policy_analysis_clarification",
                    artifact_id=clarification.id,
                    href=href,
                    metadata={"question_code": clarification.question_code},
                )
            )
    return entries


def map_assessment(
    assessment: ImpactAssessment,
    run_href: str | None,
) -> list[AuditTimelineEntry]:
    href = _anchor(run_href, "assessment-heading")
    artifact = {
        "artifact_type": "impact_assessment",
        "artifact_id": assessment.id,
        "href": href,
    }
    return [
        _entry(
            key=f"impact_assessment:{assessment.id}:created",
            occurred_at=assessment.created_at,
            actor=AuditActorCategory.DETERMINISTIC_SYSTEM,
            event=AuditEventType.ASSESSMENT_CREATED,
            title="Impact assessment created",
            description="ChangeOps created the immutable assessment record.",
            outcome=AuditOutcome.RECORDED,
            metadata={"analyzer_version": assessment.analyzer_version},
            **artifact,
        ),
        _entry(
            key=f"impact_assessment:{assessment.id}:completed",
            occurred_at=assessment.completed_at,
            actor=AuditActorCategory.DETERMINISTIC_SYSTEM,
            event=AuditEventType.IMPACT_ASSESSMENT_COMPLETED,
            title="Deterministic impact assessment completed",
            description=(
                "Deterministic rules calculated affected people, enterprise impacts, "
                "evidence, and proposed actions."
            ),
            outcome=AuditOutcome.COMPLETED,
            metadata={"analyzer_version": assessment.analyzer_version},
            **artifact,
        ),
    ]


def map_interpretation_attempts(
    attempts: Iterable[PolicyInterpretationAttempt],
    run_href: str | None,
    *,
    linked_attempt_ids: set[uuid.UUID] | None = None,
) -> list[AuditTimelineEntry]:
    entries: list[AuditTimelineEntry] = []
    linked_ids = linked_attempt_ids or set()
    for attempt in attempts:
        href = (
            _anchor(run_href, "interpretation-heading")
            if attempt.id in linked_ids
            else None
        )
        entries.append(
            _entry(
                key=f"policy_interpretation_attempt:{attempt.id}:attempted",
                occurred_at=attempt.created_at,
                actor=AuditActorCategory.AI_ASSISTED,
                event=AuditEventType.INTERPRETATION_ATTEMPTED,
                title="Grounded interpretation attempted",
                description="An AI-assisted interpreter analyzed the persisted assessment.",
                outcome=AuditOutcome.COMPLETED,
                artifact_type="policy_interpretation_attempt",
                artifact_id=attempt.id,
                href=href,
                metadata=_compact_metadata(
                    model_provider=attempt.model_provider,
                    model_identifier=attempt.model_identifier,
                    prompt_version=attempt.prompt_version,
                ),
            )
        )
        accepted = attempt.status == "accepted"
        entries.append(
            _entry(
                key=f"policy_interpretation_attempt:{attempt.id}:outcome",
                occurred_at=attempt.completed_at,
                actor=AuditActorCategory.DETERMINISTIC_SYSTEM,
                event=(
                    AuditEventType.INTERPRETATION_ACCEPTED
                    if accepted
                    else AuditEventType.INTERPRETATION_FAILED
                ),
                title="Interpretation accepted" if accepted else "Interpretation failed",
                description=(
                    "Deterministic grounding validation accepted the interpretation."
                    if accepted
                    else (
                        attempt.failure_message
                        or "The interpretation attempt did not produce an accepted change plan."
                    )
                ),
                outcome=AuditOutcome.SUCCEEDED if accepted else AuditOutcome.FAILED,
                artifact_type="policy_interpretation_attempt",
                artifact_id=attempt.id,
                href=href,
                metadata=_compact_metadata(
                    status=attempt.status,
                    failure_code=attempt.failure_code,
                    validation_error_count=len(attempt.validation_errors),
                ),
            )
        )
    return entries


def map_change_plans(
    plans: Iterable[ChangePlan],
    run_href: str | None,
) -> list[AuditTimelineEntry]:
    return [
        _entry(
            key=f"change_plan:{plan.id}:created",
            occurred_at=plan.created_at,
            actor=AuditActorCategory.AI_ASSISTED,
            event=AuditEventType.CHANGE_PLAN_CREATED,
            title="Change plan created",
            description="The accepted grounded interpretation was persisted as a change plan.",
            outcome=AuditOutcome.RECORDED,
            artifact_type="change_plan",
            artifact_id=plan.id,
            href=_anchor(run_href, "interpretation-heading"),
            metadata={"schema_version": plan.schema_version},
        )
        for plan in plans
    ]


def map_policy_comparisons(
    comparisons: Iterable[PolicyComparison],
) -> list[AuditTimelineEntry]:
    return [
        _entry(
            key=f"policy_comparison:{comparison.id}:created",
            occurred_at=comparison.created_at,
            actor=AuditActorCategory.DETERMINISTIC_SYSTEM,
            actor_identity=comparison.created_by,
            event=AuditEventType.COMPARISON_CREATED,
            title="Policy comparison created",
            description=(
                "Deterministic comparison recorded the material differences between "
                "accepted policy versions."
            ),
            outcome=AuditOutcome.COMPLETED,
            artifact_type="policy_comparison",
            artifact_id=comparison.id,
            href=f"/policy-comparisons/{comparison.id}",
            metadata={
                "baseline_policy_change_id": comparison.baseline_policy_change_id,
                "proposed_policy_change_id": comparison.proposed_policy_change_id,
                "difference_count": len(comparison.differences),
            },
        )
        for comparison in comparisons
    ]


def map_impact_deltas(
    deltas: Iterable[PolicyComparisonImpactDelta],
) -> list[AuditTimelineEntry]:
    return [
        _entry(
            key=f"policy_comparison_impact_delta:{delta.id}:created",
            occurred_at=delta.created_at,
            actor=AuditActorCategory.DETERMINISTIC_SYSTEM,
            actor_identity=delta.created_by,
            event=AuditEventType.IMPACT_DELTA_CREATED,
            title="Enterprise impact delta created",
            description=(
                "Deterministic comparison recorded how persisted enterprise impacts changed."
            ),
            outcome=AuditOutcome.COMPLETED,
            artifact_type="policy_comparison_impact_delta",
            artifact_id=delta.id,
            href=f"/policy-comparisons/{delta.policy_comparison_id}",
            metadata={
                "baseline_assessment_id": str(delta.baseline_assessment_id),
                "proposed_assessment_id": str(delta.proposed_assessment_id),
                "item_count": len(delta.items),
            },
        )
        for delta in deltas
    ]


def map_action_reviews(
    reviews: Iterable[ActionReview],
    approval_href: str | None,
) -> list[AuditTimelineEntry]:
    return [
        _entry(
            key=f"action_review:{review.id}:created",
            occurred_at=review.created_at,
            actor=AuditActorCategory.DETERMINISTIC_SYSTEM,
            event=AuditEventType.ACTION_REVIEW_CREATED,
            title="Action review created",
            description="ChangeOps snapshotted a proposed action for human review.",
            outcome=AuditOutcome.REQUESTED,
            artifact_type="action_review",
            artifact_id=review.id,
            href=approval_href,
            metadata={"proposed_action_id": str(review.proposed_action_id)},
        )
        for review in reviews
    ]


def map_action_decisions(
    decisions: Iterable[ActionReviewDecision],
    reviews: Iterable[ActionReview],
    approval_href: str | None,
) -> list[AuditTimelineEntry]:
    review_by_id = {review.id: review for review in reviews}
    entries: list[AuditTimelineEntry] = []
    for decision in decisions:
        review = review_by_id[decision.action_review_id]
        entries.append(
            _entry(
                key=f"action_review_decision:{decision.id}:recorded",
                occurred_at=decision.created_at,
                actor=AuditActorCategory.HUMAN,
                actor_identity=decision.reviewer_identity,
                event=AuditEventType.HUMAN_ACTION_DECISION_RECORDED,
                title=f"Action {decision.decision.replace('_', ' ')}",
                description=decision.rationale,
                outcome={
                    "approved": AuditOutcome.SUCCEEDED,
                    "rejected": AuditOutcome.REJECTED,
                    "deferred": AuditOutcome.RECORDED,
                    "revision_requested": AuditOutcome.REQUESTED,
                }[decision.decision],
                artifact_type="action_review_decision",
                artifact_id=decision.id,
                href=approval_href,
                metadata={
                    "action_review_id": str(review.id),
                    "decision": decision.decision,
                    "reviewer_role": decision.reviewer_role,
                },
            )
        )
    return entries


def map_approval_run(
    approval: ActionApprovalRun,
    approval_href: str | None,
) -> list[AuditTimelineEntry]:
    if approval.status not in {"completed", "failed"}:
        return []
    failed = approval.status == "failed"
    return [
        _entry(
            key=f"action_approval_run:{approval.id}:{approval.status}",
            occurred_at=approval.completed_at or approval.updated_at,
            actor=AuditActorCategory.DETERMINISTIC_SYSTEM,
            event=(
                AuditEventType.APPROVAL_FAILED if failed else AuditEventType.APPROVAL_COMPLETED
            ),
            title="Approval failed" if failed else "Approval completed",
            description=(
                approval.failure_message
                if failed and approval.failure_message
                else "ChangeOps calculated the final state after all item-level decisions."
            ),
            outcome=AuditOutcome.FAILED if failed else AuditOutcome.COMPLETED,
            artifact_type="action_approval_run",
            artifact_id=approval.id,
            href=approval_href,
            metadata=_compact_metadata(
                approved_count=approval.approved_count,
                rejected_count=approval.rejected_count,
                deferred_count=approval.deferred_count,
                revision_requested_count=approval.revision_requested_count,
                failure_code=approval.failure_code,
            ),
        )
    ]


def map_execution_commands(
    commands: Iterable[ExecutionCommand],
    approval_href: str | None,
) -> list[AuditTimelineEntry]:
    return [
        _entry(
            key=f"execution_command:{command.id}:prepared",
            occurred_at=command.created_at,
            actor=AuditActorCategory.DETERMINISTIC_SYSTEM,
            actor_identity=command.prepared_by,
            event=AuditEventType.EXECUTION_COMMAND_PREPARED,
            title="Immutable execution command prepared",
            description=(
                f"ChangeOps prepared {command.system}.{command.operation} for "
                f"{command.target_identifier}."
            ),
            outcome=AuditOutcome.RECORDED,
            artifact_type="execution_command",
            artifact_id=command.id,
            href=_anchor(approval_href, "execution"),
            metadata={
                "system": command.system,
                "operation": command.operation,
                "idempotency_key": command.idempotency_key,
            },
        )
        for command in commands
    ]


def map_execution_results(
    results: Iterable[ExecutionResult],
    approval_href: str | None,
) -> list[AuditTimelineEntry]:
    entries: list[AuditTimelineEntry] = []
    for result in results:
        href = _anchor(approval_href, "execution")
        artifact = {
            "artifact_type": "execution_result",
            "artifact_id": result.id,
            "href": href,
        }
        entries.append(
            _entry(
                key=f"execution_result:{result.id}:requested",
                occurred_at=result.created_at,
                actor=AuditActorCategory.HUMAN,
                actor_identity=result.attempted_by,
                event=AuditEventType.EXECUTION_REQUESTED,
                title="Execution explicitly requested",
                description="An authorized administrator requested execution of the command.",
                outcome=AuditOutcome.REQUESTED,
                metadata={"attempted_role": result.attempted_role},
                **artifact,
            )
        )
        if result.status == "already_applied":
            event = AuditEventType.EXECUTION_REPLAY_PREVENTED
            title = "Execution replay prevented"
            outcome = AuditOutcome.PREVENTED
        elif result.status == "succeeded":
            event = AuditEventType.EXECUTION_SUCCEEDED
            title = "Execution completed"
            outcome = AuditOutcome.SUCCEEDED
        else:
            event = AuditEventType.EXECUTION_FAILED
            title = "Execution failed"
            outcome = (
                AuditOutcome.REJECTED
                if result.status in {"rejected_unsupported", "failed_validation"}
                else AuditOutcome.FAILED
            )
        entries.append(
            _entry(
                key=f"execution_result:{result.id}:outcome",
                occurred_at=result.created_at,
                actor=AuditActorCategory.DETERMINISTIC_SYSTEM,
                event=event,
                title=title,
                description=result.message,
                outcome=outcome,
                metadata={
                    "status": result.status,
                    "outcome_code": result.outcome_code,
                    "command_idempotency_key": result.command_idempotency_key,
                },
                **artifact,
            )
        )
    return entries


def map_learning_assignments(
    assignments: Iterable[SimulatedLearningAssignment],
    approval_href: str | None,
) -> list[AuditTimelineEntry]:
    return [
        _entry(
            key=f"simulated_learning_assignment:{assignment.id}:created",
            occurred_at=assignment.created_at,
            actor=AuditActorCategory.EXTERNAL_SYSTEM,
            actor_identity="simulated_learning",
            event=AuditEventType.SIMULATED_SIDE_EFFECT_CREATED,
            title="Simulated learning assignment created",
            description=(
                f"The simulated learning system assigned {assignment.training_course_id} "
                f"to {assignment.worker_id}."
            ),
            outcome=AuditOutcome.SUCCEEDED,
            artifact_type="simulated_learning_assignment",
            artifact_id=assignment.id,
            href=_anchor(approval_href, "execution"),
            metadata={
                "worker_id": assignment.worker_id,
                "training_course_id": assignment.training_course_id,
            },
        )
        for assignment in assignments
    ]


def map_jira_issues(issues: Iterable[JiraIssue]) -> list[AuditTimelineEntry]:
    return [
        _entry(
            key=f"jira_issue:{issue.id}:created",
            occurred_at=issue.created_at,
            actor=AuditActorCategory.EXTERNAL_SYSTEM,
            actor_identity="jira",
            event=AuditEventType.JIRA_ISSUE_CREATED,
            title="Jira issue created",
            description=f"Jira created issue {issue.issue_key}.",
            outcome=AuditOutcome.SUCCEEDED,
            artifact_type="jira_issue",
            artifact_id=issue.id,
            href=issue.browse_url,
            metadata={
                "issue_key": issue.issue_key,
                "project_id_or_key": issue.project_id_or_key,
            },
        )
        for issue in issues
    ]


def _entry(
    *,
    key: str,
    occurred_at: Any,
    actor: AuditActorCategory,
    event: AuditEventType,
    title: str,
    description: str,
    outcome: AuditOutcome,
    artifact_type: str,
    artifact_id: Any,
    href: str | None,
    actor_identity: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditTimelineEntry:
    return AuditTimelineEntry(
        entry_key=key,
        occurred_at=occurred_at,
        actor_category=actor,
        actor_identity=actor_identity,
        event_type=event,
        title=title,
        description=description,
        outcome=outcome,
        artifact=AuditArtifactReference(
            artifact_type=artifact_type,
            artifact_id=str(artifact_id),
            href=href,
        ),
        metadata=metadata or {},
    )


def _sort_key(entry: AuditTimelineEntry) -> tuple[Any, int, str, str, str]:
    return (
        entry.occurred_at,
        EVENT_PRECEDENCE[entry.event_type],
        entry.artifact.artifact_type,
        entry.artifact.artifact_id,
        entry.entry_key,
    )


def _anchor(href: str | None, fragment: str) -> str | None:
    return f"{href}#{fragment}" if href else None


def _compact_metadata(**values: Any) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}
