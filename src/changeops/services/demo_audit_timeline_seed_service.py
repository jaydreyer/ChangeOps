import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from changeops.db.models import (
    ActionApprovalRunItem,
    ActionReview,
    ActionReviewDecision,
    ExecutionCommand,
    ExecutionResult,
    JiraExecutionDelivery,
    JiraIssue,
    ProposedAction,
)
from changeops.domain.action_review import ReviewActor, ReviewDecisionInput
from changeops.services.action_approval_service import create_action_approval_run_record
from changeops.services.action_review_service import submit_action_review_decision
from changeops.services.demo_assessment_seed_service import (
    DEMO_ASSESSMENT_ID,
    DEMO_PROPOSED_ASSESSMENT_ID,
    seed_demo_assessment,
    seed_demo_proposed_assessment,
)
from changeops.services.policy_comparison_service import create_policy_comparison
from changeops.services.seed_service import POLICY_CHANGE_ID, PROPOSED_POLICY_CHANGE_ID
from changeops.workflows.action_approval import execute_action_approval

DEMO_EXECUTION_COMMAND_ID = uuid.UUID("8f4f647d-7f2d-4da8-8e02-77d5301f2021")
DEMO_JIRA_ISSUE_ID = uuid.UUID("8f4f647d-7f2d-4da8-8e02-77d5301f2022")
DEMO_EXECUTION_RESULT_ID = uuid.UUID("8f4f647d-7f2d-4da8-8e02-77d5301f2023")
DEMO_REPLAY_RESULT_ID = uuid.UUID("8f4f647d-7f2d-4da8-8e02-77d5301f2024")


def seed_demo_audit_timeline(session: Session) -> uuid.UUID:
    seed_demo_assessment(session)
    seed_demo_proposed_assessment(session)
    comparison, _ = create_policy_comparison(
        session,
        baseline_policy_change_id=POLICY_CHANGE_ID,
        proposed_policy_change_id=PROPOSED_POLICY_CHANGE_ID,
        created_by="demo.reviewer@example.com",
    )
    comparison_id = comparison.id
    delta = comparison.impact_delta
    if delta is None:
        raise RuntimeError("Seeded comparison did not create an impact delta.")
    delta_id = delta.id
    session.rollback()

    approval, created = create_action_approval_run_record(
        session,
        DEMO_PROPOSED_ASSESSMENT_ID,
    )
    approval_id = approval.id
    session.rollback()
    if created:
        execute_action_approval(session, approval_id, trigger_type="run_created")

    items = list(
        session.scalars(
            select(ActionApprovalRunItem).where(
                ActionApprovalRunItem.approval_run_id == approval_id
            )
        )
    )
    decisions_to_record: list[tuple[uuid.UUID, str]] = []
    for item in items:
        review = session.get(ActionReview, item.action_review_id)
        action = session.get(ProposedAction, item.proposed_action_id)
        if review is None or action is None:
            raise RuntimeError("Seeded approval membership is inconsistent.")
        if review.status == "pending":
            decisions_to_record.append(
                (
                    review.id,
                    "approved" if action.action_type == "operational_remediation" else "deferred",
                )
            )
    session.rollback()

    actor = ReviewActor(identity="demo.reviewer@example.com", role="reviewer")
    for review_id, decision in decisions_to_record:
        decided = submit_action_review_decision(
            session,
            review_id,
            ReviewDecisionInput(
                decision=decision,
                rationale=(
                    "Approved for the deterministic Jira demonstration."
                    if decision == "approved"
                    else "Deferred outside the focused demonstration action."
                ),
            ),
            actor,
        )
        decision_id = decided.decisions[-1].id
        session.rollback()
        execute_action_approval(
            session,
            approval_id,
            trigger_type="decision_recorded",
            trigger_reference=str(decision_id),
            actor_identity=actor.identity,
        )

    existing_command = session.get(ExecutionCommand, DEMO_EXECUTION_COMMAND_ID)
    session.rollback()
    if existing_command is None:
        _seed_jira_execution(
            session,
            approval_id=approval_id,
            comparison_id=comparison_id,
            delta_id=delta_id,
        )
    return approval_id


def _seed_jira_execution(
    session: Session,
    *,
    approval_id: uuid.UUID,
    comparison_id: uuid.UUID,
    delta_id: uuid.UUID,
) -> None:
    item = session.scalar(
        select(ActionApprovalRunItem)
        .join(ActionReview, ActionReview.id == ActionApprovalRunItem.action_review_id)
        .join(ProposedAction, ProposedAction.id == ActionApprovalRunItem.proposed_action_id)
        .where(
            ActionApprovalRunItem.approval_run_id == approval_id,
            ActionReview.status == "approved",
            ProposedAction.action_type == "operational_remediation",
        )
    )
    if item is None:
        raise RuntimeError("Seeded Jira execution requires one approved remediation action.")
    review = session.get(ActionReview, item.action_review_id)
    action = session.get(ProposedAction, item.proposed_action_id)
    decision = session.scalar(
        select(ActionReviewDecision).where(
            ActionReviewDecision.action_review_id == item.action_review_id
        )
    )
    if review is None or action is None or decision is None:
        raise RuntimeError("Seeded Jira execution lineage is incomplete.")
    review_id = review.id
    decision_id = decision.id
    action_id = action.id
    assessment_id = action.assessment_id
    target_type = action.target_type
    target_identifier = action.target_identifier
    original = dict(review.original_action_snapshot)
    effective = {
        **original,
        "schema_version": "effective-approved-action-v1",
    }
    parameters = {
        "project_id_or_key": "ECM",
        "issue_type_id": "10001",
        "summary": "Update International Business Travel Policy",
        "description": (
            "Seeded fictional Jira task backed by the approved policy comparison and impact delta."
        ),
        "execution_command_id": str(DEMO_EXECUTION_COMMAND_ID),
        "comparison_id": str(comparison_id),
        "baseline_assessment_id": str(DEMO_ASSESSMENT_ID),
        "proposed_assessment_id": str(DEMO_PROPOSED_ASSESSMENT_ID),
        "target_identifier": target_identifier,
        "impact_delta_id": str(delta_id),
    }
    idempotency_key = hashlib.sha256(
        json.dumps(
            {
                "decision_id": str(decision_id),
                "parameters": parameters,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    created_at = datetime.now(UTC)
    result_created_at = created_at + timedelta(seconds=1)
    issue_created_at = result_created_at
    replay_created_at = result_created_at + timedelta(seconds=1)
    session.rollback()

    with session.begin():
        session.add(
            ExecutionCommand(
                id=DEMO_EXECUTION_COMMAND_ID,
                approval_run_id=approval_id,
                action_review_id=review_id,
                action_review_decision_id=decision_id,
                proposed_action_id=action_id,
                assessment_id=assessment_id,
                schema_version="execution-command-v1",
                system="jira",
                operation="create_issue",
                target_type=target_type,
                target_identifier=target_identifier,
                parameters_snapshot=parameters,
                effective_action_snapshot=effective,
                idempotency_key=idempotency_key,
                status="pending_execution",
                prepared_by="demo.operator@example.com",
                prepared_role="admin",
                created_at=created_at,
            )
        )
        session.flush()
        session.add(
            JiraExecutionDelivery(
                execution_command_id=DEMO_EXECUTION_COMMAND_ID,
                state="succeeded",
                attempt_count=1,
                created_at=created_at,
                updated_at=result_created_at,
            )
        )
        session.add(
            JiraIssue(
                id=DEMO_JIRA_ISSUE_ID,
                execution_command_id=DEMO_EXECUTION_COMMAND_ID,
                issue_id="10042",
                issue_key="ECM-42",
                api_url="https://jira.example.test/rest/api/3/issue/10042",
                browse_url="https://jira.example.test/browse/ECM-42",
                project_id_or_key="ECM",
                created_at=issue_created_at,
            )
        )
        session.flush()
        session.add_all(
            [
                ExecutionResult(
                    id=DEMO_EXECUTION_RESULT_ID,
                    execution_command_id=DEMO_EXECUTION_COMMAND_ID,
                    simulated_learning_assignment_id=None,
                    jira_issue_id=DEMO_JIRA_ISSUE_ID,
                    status="succeeded",
                    outcome_code="jira_issue_created",
                    message="Jira issue ECM-42 was created.",
                    command_idempotency_key=idempotency_key,
                    attempted_by="demo.operator@example.com",
                    attempted_role="admin",
                    created_at=result_created_at,
                ),
                ExecutionResult(
                    id=DEMO_REPLAY_RESULT_ID,
                    execution_command_id=DEMO_EXECUTION_COMMAND_ID,
                    simulated_learning_assignment_id=None,
                    jira_issue_id=DEMO_JIRA_ISSUE_ID,
                    status="already_applied",
                    outcome_code="execution_replay_prevented",
                    message="The command was already applied; no duplicate Jira issue was created.",
                    command_idempotency_key=idempotency_key,
                    attempted_by="demo.operator@example.com",
                    attempted_role="admin",
                    created_at=replay_created_at,
                ),
            ]
        )
