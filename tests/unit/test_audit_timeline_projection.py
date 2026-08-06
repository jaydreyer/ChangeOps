import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from changeops.schemas.audit_timeline import (
    AuditActorCategory,
    AuditEventType,
    AuditOutcome,
)
from changeops.services.audit_timeline_projection_service import (
    _sort_key,
    map_action_decisions,
    map_action_reviews,
    map_analysis_run,
    map_approval_run,
    map_assessment,
    map_change_plans,
    map_clarifications,
    map_execution_commands,
    map_execution_results,
    map_extraction_attempts,
    map_impact_deltas,
    map_interpretation_attempts,
    map_jira_issues,
    map_learning_assignments,
    map_policy_comparisons,
)

NOW = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)


def record(**values):
    return SimpleNamespace(**values)


def test_analysis_extraction_and_assessment_mappings_separate_ai_from_determinism() -> None:
    run = record(
        id=uuid.uuid4(),
        policy_change_id="policy-1",
        created_at=NOW,
        status="completed",
        completed_at=NOW,
        updated_at=NOW,
        workflow_version="workflow-v1",
        failure_code=None,
        failure_detail=None,
    )
    attempt = record(
        id=uuid.uuid4(),
        created_at=NOW,
        model_provider="fixture",
        model_identifier="extractor-v1",
        prompt_version="prompt-v1",
        retry_reason=None,
        validation_outcome="accepted",
        support_status="supported",
        validation_errors=[],
    )
    assessment = record(
        id=uuid.uuid4(),
        created_at=NOW,
        completed_at=NOW,
        analyzer_version="analyzer-v1",
    )

    entries = (
        map_analysis_run(run, "/policy-analyses/run")
        + map_extraction_attempts(
            [attempt],
            "/policy-analyses/run",
            linked_attempt_id=attempt.id,
        )
        + map_assessment(assessment, "/policy-analyses/run")
    )

    by_type = {entry.event_type: entry for entry in entries}
    assert by_type[AuditEventType.EXTRACTION_ATTEMPTED].actor_category == (
        AuditActorCategory.AI_ASSISTED
    )
    assert by_type[AuditEventType.EXTRACTION_ACCEPTED].actor_category == (
        AuditActorCategory.DETERMINISTIC_SYSTEM
    )
    assert by_type[AuditEventType.EXTRACTION_ACCEPTED].outcome == AuditOutcome.SUCCEEDED
    assert by_type[AuditEventType.IMPACT_ASSESSMENT_COMPLETED].artifact.artifact_id == str(
        assessment.id
    )
    assert by_type[AuditEventType.ANALYSIS_REQUESTED].artifact.href == "/policy-analyses/run"


def test_rejected_extraction_and_failed_analysis_remain_visible() -> None:
    run = record(
        id=uuid.uuid4(),
        policy_change_id="policy-1",
        created_at=NOW,
        status="failed",
        completed_at=NOW,
        updated_at=NOW,
        workflow_version="workflow-v1",
        failure_code="retry_limit_exhausted",
        failure_detail="No accepted extraction was produced.",
    )
    attempt = record(
        id=uuid.uuid4(),
        created_at=NOW,
        model_provider="fixture",
        model_identifier="extractor-v1",
        prompt_version="prompt-v1",
        retry_reason="validation_failed",
        validation_outcome="validation_failed",
        support_status=None,
        validation_errors=[{"code": "bad_quote"}],
    )

    entries = map_analysis_run(run, None) + map_extraction_attempts([attempt], None)

    by_type = {entry.event_type: entry for entry in entries}
    assert by_type[AuditEventType.EXTRACTION_REJECTED].outcome == AuditOutcome.REJECTED
    assert by_type[AuditEventType.EXTRACTION_REJECTED].artifact.href is None
    assert by_type[AuditEventType.ANALYSIS_FAILED].metadata["failure_code"] == (
        "retry_limit_exhausted"
    )


def test_clarification_interpretation_and_change_plan_mappings_preserve_attempts() -> None:
    clarification = record(
        id=uuid.uuid4(),
        created_at=NOW,
        answered_at=NOW,
        question_text="Does the exemption apply?",
        question_code="booking_exemption",
        responder_identity="reviewer@example.com",
    )
    accepted = record(
        id=uuid.uuid4(),
        created_at=NOW,
        completed_at=NOW,
        status="accepted",
        model_provider="fixture",
        model_identifier="interpreter-v1",
        prompt_version="prompt-v1",
        failure_message=None,
        failure_code=None,
        validation_errors=[],
    )
    failed = record(
        **{
            **accepted.__dict__,
            "id": uuid.uuid4(),
            "status": "provider_failed",
            "failure_code": "provider_unavailable",
            "failure_message": "The provider was unavailable.",
        }
    )
    plan = record(id=uuid.uuid4(), created_at=NOW, schema_version="plan-v1")

    entries = (
        map_clarifications([clarification], "/policy-analyses/run")
        + map_interpretation_attempts(
            [accepted, failed],
            "/policy-analyses/run",
            linked_attempt_ids={accepted.id},
        )
        + map_change_plans([plan], "/policy-analyses/run")
    )

    by_key = {entry.entry_key: entry for entry in entries}
    answered = by_key[f"policy_analysis_clarification:{clarification.id}:answered"]
    assert answered.actor_identity == "reviewer@example.com"
    assert answered.actor_category == AuditActorCategory.HUMAN
    assert any(entry.event_type == AuditEventType.INTERPRETATION_FAILED for entry in entries)
    assert any(entry.event_type == AuditEventType.CHANGE_PLAN_CREATED for entry in entries)
    failed_entries = [
        entry for entry in entries if entry.artifact.artifact_id == str(failed.id)
    ]
    assert all(entry.artifact.href is None for entry in failed_entries)


def test_review_approval_command_execution_and_side_effect_mappings_are_attributable() -> None:
    review = record(
        id=uuid.uuid4(),
        proposed_action_id=uuid.uuid4(),
        created_at=NOW,
    )
    decision = record(
        id=uuid.uuid4(),
        action_review_id=review.id,
        created_at=NOW,
        decision="approved",
        reviewer_identity="reviewer@example.com",
        reviewer_role="reviewer",
        rationale="Approved with evidence.",
    )
    approval = record(
        id=uuid.uuid4(),
        status="completed",
        completed_at=NOW,
        updated_at=NOW,
        failure_message=None,
        failure_code=None,
        approved_count=1,
        rejected_count=0,
        deferred_count=0,
        revision_requested_count=0,
    )
    command = record(
        id=uuid.uuid4(),
        created_at=NOW,
        prepared_by="operator@example.com",
        system="learning",
        operation="assign_training",
        target_identifier="worker-1",
        idempotency_key="a" * 64,
    )
    succeeded = record(
        id=uuid.uuid4(),
        created_at=NOW,
        attempted_by="operator@example.com",
        attempted_role="admin",
        status="succeeded",
        message="Training assigned.",
        outcome_code="learning_assignment_created",
        command_idempotency_key=command.idempotency_key,
    )
    replay = record(
        **{
            **succeeded.__dict__,
            "id": uuid.uuid4(),
            "status": "already_applied",
            "message": "The command was already applied.",
            "outcome_code": "execution_replay_prevented",
        }
    )
    failure = record(
        **{
            **succeeded.__dict__,
            "id": uuid.uuid4(),
            "status": "failed_unavailable",
            "message": "The target was unavailable.",
            "outcome_code": "target_unavailable",
        }
    )
    assignment = record(
        id=uuid.uuid4(),
        created_at=NOW,
        worker_id="worker-1",
        training_course_id="course-1",
    )
    issue = record(
        id=uuid.uuid4(),
        created_at=NOW,
        issue_key="ECM-42",
        browse_url="https://jira.example/browse/ECM-42",
        project_id_or_key="ECM",
    )

    entries = (
        map_action_reviews([review], "/approvals/run")
        + map_action_decisions([decision], [review], "/approvals/run")
        + map_approval_run(approval, "/approvals/run")
        + map_execution_commands([command], "/approvals/run")
        + map_execution_results([succeeded, replay, failure], "/approvals/run")
        + map_learning_assignments([assignment], "/approvals/run")
        + map_jira_issues([issue])
    )

    by_type = {entry.event_type: entry for entry in entries}
    assert by_type[AuditEventType.HUMAN_ACTION_DECISION_RECORDED].actor_identity == (
        "reviewer@example.com"
    )
    assert by_type[AuditEventType.EXECUTION_COMMAND_PREPARED].actor_category == (
        AuditActorCategory.DETERMINISTIC_SYSTEM
    )
    assert by_type[AuditEventType.EXECUTION_REPLAY_PREVENTED].outcome == (
        AuditOutcome.PREVENTED
    )
    assert by_type[AuditEventType.EXECUTION_FAILED].outcome == AuditOutcome.FAILED
    assert by_type[AuditEventType.SIMULATED_SIDE_EFFECT_CREATED].actor_category == (
        AuditActorCategory.EXTERNAL_SYSTEM
    )
    assert by_type[AuditEventType.JIRA_ISSUE_CREATED].artifact.href == issue.browse_url


def test_decision_outcomes_distinguish_rejection_deferral_and_revision_request() -> None:
    reviews = [
        record(id=uuid.uuid4(), proposed_action_id=uuid.uuid4(), created_at=NOW)
        for _ in range(4)
    ]
    decisions = [
        record(
            id=uuid.uuid4(),
            action_review_id=review.id,
            created_at=NOW,
            decision=decision,
            reviewer_identity="reviewer@example.com",
            reviewer_role="reviewer",
            rationale=f"{decision} with evidence.",
        )
        for review, decision in zip(
            reviews,
            ("approved", "rejected", "deferred", "revision_requested"),
            strict=True,
        )
    ]

    entries = map_action_decisions(decisions, reviews, "/approvals/run")

    assert {entry.metadata["decision"]: entry.outcome for entry in entries} == {
        "approved": AuditOutcome.SUCCEEDED,
        "rejected": AuditOutcome.REJECTED,
        "deferred": AuditOutcome.RECORDED,
        "revision_requested": AuditOutcome.REQUESTED,
    }


def test_comparison_and_delta_mappings_use_authoritative_lineage_and_detail_route() -> None:
    comparison = record(
        id=uuid.uuid4(),
        created_at=NOW,
        created_by="reviewer@example.com",
        baseline_policy_change_id="baseline",
        proposed_policy_change_id="proposed",
        differences=[record(id=uuid.uuid4())],
    )
    delta = record(
        id=uuid.uuid4(),
        policy_comparison_id=comparison.id,
        created_at=NOW,
        created_by="reviewer@example.com",
        baseline_assessment_id=uuid.uuid4(),
        proposed_assessment_id=uuid.uuid4(),
        items=[record(id=uuid.uuid4())],
    )

    entries = map_policy_comparisons([comparison]) + map_impact_deltas([delta])

    assert [entry.event_type for entry in entries] == [
        AuditEventType.COMPARISON_CREATED,
        AuditEventType.IMPACT_DELTA_CREATED,
    ]
    assert all(
        entry.artifact.href == f"/policy-comparisons/{comparison.id}" for entry in entries
    )


def test_equal_timestamp_order_uses_causal_precedence_then_artifact_identity() -> None:
    attempt = record(
        id=uuid.UUID(int=2),
        created_at=NOW,
        model_provider="fixture",
        model_identifier="extractor-v1",
        prompt_version="prompt-v1",
        retry_reason=None,
        validation_outcome="accepted",
        support_status="supported",
        validation_errors=[],
    )
    entries = map_extraction_attempts(
        [attempt],
        "/policy-analyses/run",
        linked_attempt_id=attempt.id,
    )

    first = sorted(reversed(entries), key=_sort_key)
    second = sorted(entries, key=_sort_key)

    assert [entry.entry_key for entry in first] == [entry.entry_key for entry in second]
    assert [entry.event_type for entry in first] == [
        AuditEventType.EXTRACTION_ATTEMPTED,
        AuditEventType.EXTRACTION_ACCEPTED,
    ]
