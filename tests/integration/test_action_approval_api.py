import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from changeops.api.policy_extractions import extraction_model_dependency
from changeops.db.models import (
    ActionApprovalRun,
    ActionApprovalRunItem,
    ActionApprovalRunTransition,
    ActionReview,
    PolicyAnalysisRun,
    ProposedAction,
)
from changeops.db.session import SessionLocal
from changeops.domain.action_review import ReviewActor, ReviewDecisionInput
from changeops.services.action_approval_service import create_action_approval_run_record
from changeops.services.action_review_service import submit_action_review_decision
from changeops.services.seed_service import POLICY_CHANGE_ID
from tests.integration.test_policy_extraction_api import configured_fixture_model

REVIEWER_HEADERS = {
    "X-ChangeOps-Actor": "reviewer@example.com",
    "X-ChangeOps-Role": "reviewer",
}


def _workflow_assessment(client) -> dict:
    client.app.dependency_overrides[extraction_model_dependency] = lambda: (
        configured_fixture_model()
    )
    response = client.post(
        "/api/v1/policy-analysis-runs",
        json={"policy_change_id": POLICY_CHANGE_ID},
    )
    assert response.status_code == 201, response.text
    run = response.json()
    assert run["status"] == "completed", run.get("failure_detail")
    assessment = client.get(f"/api/v1/impact-assessments/{run['assessment_id']}")
    assert assessment.status_code == 200
    return assessment.json()


def _create_run(client) -> tuple[dict, dict]:
    assessment = _workflow_assessment(client)
    response = client.post(f"/api/v1/impact-assessments/{assessment['id']}/approval-run")
    assert response.status_code == 201, response.text
    return assessment, response.json()


def test_create_run_initializes_all_golden_actions_and_waits_durably(client) -> None:
    assessment, run = _create_run(client)

    assert len(assessment["proposed_actions"]) == 13
    assert run["status"] == "awaiting_decisions"
    assert run["current_step"] == "await_decisions"
    assert run["summary"] == {
        "total": 13,
        "pending": 13,
        "approved": 0,
        "rejected": 0,
        "deferred": 0,
        "revision_requested": 0,
    }
    assert [item["sequence"] for item in run["items"]] == list(range(13))
    assert all(item["review_status"] == "pending" for item in run["items"])
    assert [item["trigger_type"] for item in run["transitions"]] == [
        "run_created",
        "initialized",
        "initialized",
    ]

    repeated = client.post(f"/api/v1/impact-assessments/{assessment['id']}/approval-run")
    assert repeated.status_code == 200
    assert repeated.json() == run
    assert client.get(repeated.headers["Location"]).json() == run
    assert client.get(f"/api/v1/impact-assessments/{assessment['id']}/approval-run").json() == run

    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(ActionApprovalRun)) == 1
        assert session.scalar(select(func.count()).select_from(ActionApprovalRunItem)) == 13
        assert session.scalar(select(func.count()).select_from(ActionReview)) == 13


def test_existing_reviews_and_terminal_decisions_are_reused(client) -> None:
    assessment = _workflow_assessment(client)
    first_action = assessment["proposed_actions"][0]
    review = client.post(f"/api/v1/proposed-actions/{first_action['id']}/review").json()
    decision = client.post(
        f"/api/v1/action-reviews/{review['id']}/decisions",
        headers=REVIEWER_HEADERS,
        json={"decision": "rejected", "rationale": "Not appropriate."},
    )
    assert decision.status_code == 201

    created = client.post(f"/api/v1/impact-assessments/{assessment['id']}/approval-run")

    assert created.status_code == 201
    run = created.json()
    assert run["summary"]["rejected"] == 1
    assert run["summary"]["pending"] == 12
    item = next(item for item in run["items"] if item["proposed_action_id"] == first_action["id"])
    assert item["review_id"] == review["id"]
    assert item["review_status"] == "rejected"


def test_fully_predecided_assessment_completes_on_creation(client) -> None:
    assessment = _workflow_assessment(client)
    for index, action in enumerate(assessment["proposed_actions"]):
        review = client.post(f"/api/v1/proposed-actions/{action['id']}/review").json()
        response = client.post(
            f"/api/v1/action-reviews/{review['id']}/decisions",
            headers=REVIEWER_HEADERS,
            json={
                "decision": "approved" if index < 8 else "deferred",
                "rationale": f"Preexisting decision {index}.",
            },
        )
        assert response.status_code == 201

    created = client.post(f"/api/v1/impact-assessments/{assessment['id']}/approval-run")

    assert created.status_code == 201
    assert created.json()["status"] == "completed"
    assert created.json()["summary"] == {
        "total": 13,
        "pending": 0,
        "approved": 8,
        "rejected": 0,
        "deferred": 5,
        "revision_requested": 0,
    }


def test_each_decision_resumes_same_run_and_final_decision_completes(client) -> None:
    assessment, created = _create_run(client)
    run_id = created["id"]
    original_assessment = client.get(f"/api/v1/impact-assessments/{assessment['id']}").json()

    decisions = ["approved", "rejected", "deferred", "revision_requested"]
    for index, item in enumerate(created["items"]):
        decision = decisions[index % len(decisions)]
        response = client.post(
            f"/api/v1/action-reviews/{item['review_id']}/decisions",
            headers=REVIEWER_HEADERS,
            json={"decision": decision, "rationale": f"Decision {index}."},
        )
        assert response.status_code == 201, response.text
        current = client.get(f"/api/v1/action-approval-runs/{run_id}").json()
        assert current["summary"]["pending"] == 12 - index
        if index < 12:
            assert current["status"] == "awaiting_decisions"

    completed = client.get(f"/api/v1/action-approval-runs/{run_id}").json()
    assert completed["status"] == "completed"
    assert completed["current_step"] == "finalize"
    assert completed["summary"] == {
        "total": 13,
        "pending": 0,
        "approved": 4,
        "rejected": 3,
        "deferred": 3,
        "revision_requested": 3,
    }
    assert completed["completed_at"] is not None
    assert (
        client.post(
            f"/api/v1/action-approval-runs/{run_id}/resume",
            headers=REVIEWER_HEADERS,
        ).json()
        == completed
    )

    assert (
        client.get(f"/api/v1/impact-assessments/{assessment['id']}").json() == original_assessment
    )
    with SessionLocal() as session:
        analysis = session.get(
            PolicyAnalysisRun,
            uuid.UUID(completed["policy_analysis_run_id"]),
        )
        actions = list(
            session.scalars(
                select(ProposedAction).where(
                    ProposedAction.assessment_id == uuid.UUID(assessment["id"])
                )
            )
        )
        assert analysis is not None and analysis.status == "completed"
        assert all(action.execution_status == "not_executed" for action in actions)


def test_explicit_resume_is_authorized_and_idempotent(client) -> None:
    _, run = _create_run(client)
    url = f"/api/v1/action-approval-runs/{run['id']}/resume"

    assert client.post(url).status_code == 403
    resumed = client.post(url, headers=REVIEWER_HEADERS)

    assert resumed.status_code == 200
    assert resumed.json() == run


def test_concurrent_creation_claims_one_run(client) -> None:
    assessment = _workflow_assessment(client)
    assessment_id = uuid.UUID(assessment["id"])
    barrier = Barrier(2)

    def create() -> tuple[uuid.UUID, bool]:
        barrier.wait()
        with SessionLocal() as session:
            run, created = create_action_approval_run_record(session, assessment_id)
            return run.id, created

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: create(), range(2)))

    assert len({run_id for run_id, _ in outcomes}) == 1
    assert sorted(created for _, created in outcomes) == [False, True]


def test_concurrent_decisions_are_reconciled_by_explicit_resume(client) -> None:
    _, run = _create_run(client)
    review_ids = [uuid.UUID(item["review_id"]) for item in run["items"][:2]]
    barrier = Barrier(2)

    def decide(review_id: uuid.UUID) -> None:
        barrier.wait()
        with SessionLocal() as session:
            submit_action_review_decision(
                session,
                review_id,
                ReviewDecisionInput(
                    decision="approved",
                    rationale="Concurrent persisted decision.",
                ),
                ReviewActor(identity=f"{review_id}@example.com", role="reviewer"),
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(decide, review_ids))

    reconciled = client.post(
        f"/api/v1/action-approval-runs/{run['id']}/resume",
        headers=REVIEWER_HEADERS,
    ).json()
    assert reconciled["summary"]["approved"] == 2
    assert reconciled["summary"]["pending"] == 11


def test_direct_assessment_without_completed_analysis_run_is_rejected(client) -> None:
    assessment = client.post(f"/api/v1/policy-changes/{POLICY_CHANGE_ID}/impact-assessments").json()

    response = client.post(f"/api/v1/impact-assessments/{assessment['id']}/approval-run")

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "approval_assessment_not_completed"


def test_database_rejects_run_item_lifecycle_mismatch(client) -> None:
    _, initialized_run = _create_run(client)
    second_assessment = _workflow_assessment(client)
    with SessionLocal() as session:
        second_run, created = create_action_approval_run_record(
            session,
            uuid.UUID(second_assessment["id"]),
        )
        assert created
        second_run_id = second_run.id

    first_item = initialized_run["items"][0]
    with pytest.raises(IntegrityError), SessionLocal.begin() as session:
        session.add(
            ActionApprovalRunItem(
                approval_run_id=second_run_id,
                assessment_id=uuid.UUID(second_assessment["id"]),
                proposed_action_id=uuid.UUID(first_item["proposed_action_id"]),
                action_review_id=uuid.UUID(first_item["review_id"]),
                sequence=0,
                created_at=datetime.now(UTC),
            )
        )


def test_automatic_resume_failure_preserves_decision_for_manual_reconciliation(
    client,
    monkeypatch,
) -> None:
    _, run = _create_run(client)
    first = run["items"][0]

    def fail_unexpectedly(*args, **kwargs) -> None:
        raise RuntimeError("fixture orchestration failure")

    monkeypatch.setattr(
        "changeops.api.action_reviews.execute_action_approval",
        fail_unexpectedly,
    )
    decided = client.post(
        f"/api/v1/action-reviews/{first['review_id']}/decisions",
        headers=REVIEWER_HEADERS,
        json={"decision": "approved", "rationale": "Authoritative decision."},
    )

    assert decided.status_code == 201
    stale = client.get(f"/api/v1/action-approval-runs/{run['id']}").json()
    assert stale["summary"]["pending"] == 13
    reconciled = client.post(
        f"/api/v1/action-approval-runs/{run['id']}/resume",
        headers=REVIEWER_HEADERS,
    ).json()
    assert reconciled["summary"]["approved"] == 1
    assert reconciled["summary"]["pending"] == 12


def test_transition_rows_are_append_only(client) -> None:
    _, run = _create_run(client)
    transition_id = run["transitions"][0]["id"]

    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    with pytest.raises(DBAPIError), SessionLocal.begin() as session:
        session.execute(
            text("DELETE FROM action_approval_run_transitions WHERE id = :id"),
            {"id": transition_id},
        )

    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(ActionApprovalRunTransition)) == 3
