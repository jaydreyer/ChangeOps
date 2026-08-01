import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from changeops.db.models import ActionReview, ActionReviewDecision, ProposedAction
from changeops.db.session import SessionLocal
from changeops.domain.action_review import (
    ReviewActor,
    ReviewDecisionInput,
    ReviewValidationError,
)
from changeops.main import create_app
from changeops.services.action_review_service import (
    create_or_get_action_review,
    submit_action_review_decision,
)
from changeops.services.seed_service import POLICY_CHANGE_ID

REVIEWER_HEADERS = {
    "X-ChangeOps-Actor": "reviewer@example.com",
    "X-ChangeOps-Role": "reviewer",
}


def _assessment_and_action(client: TestClient) -> tuple[dict, dict]:
    assessment = client.post(f"/api/v1/policy-changes/{POLICY_CHANGE_ID}/impact-assessments").json()
    return assessment, assessment["proposed_actions"][0]


def _create_review(client: TestClient) -> tuple[dict, dict, dict]:
    assessment, action = _assessment_and_action(client)
    response = client.post(f"/api/v1/proposed-actions/{action['id']}/review")
    assert response.status_code == 201, response.text
    return assessment, action, response.json()


def test_review_creation_is_idempotent_and_snapshots_action_context(
    client: TestClient,
) -> None:
    assessment, action = _assessment_and_action(client)
    before = client.get(f"/api/v1/impact-assessments/{assessment['id']}").json()

    created = client.post(f"/api/v1/proposed-actions/{action['id']}/review")
    repeated = client.post(f"/api/v1/proposed-actions/{action['id']}/review")

    assert created.status_code == 201
    assert repeated.status_code == 200
    assert repeated.json() == created.json()
    assert created.headers["Location"] == (f"/api/v1/action-reviews/{created.json()['id']}")
    body = created.json()
    assert body["status"] == "pending"
    assert body["assessment_id"] == assessment["id"]
    assert body["proposed_action_id"] == action["id"]
    assert body["original_action"]["description"] == action["description"]
    assert body["original_action"]["target_identifier"] == action["target"]["identifier"]
    assert body["original_action"]["execution_status"] == "not_executed"
    assert body["review_context"]["enterprise_impact_id"] == action["enterprise_impact_id"]
    assert body["review_context"]["reason_code"]
    assert body["review_context"]["evidence_keys"]
    assert client.get(created.headers["Location"]).json() == body
    assert client.get(f"/api/v1/proposed-actions/{action['id']}/review").json() == body
    assert client.get(f"/api/v1/impact-assessments/{assessment['id']}").json() == before

    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(ActionReview)) == 1
        persisted_action = session.get(ProposedAction, uuid.UUID(action["id"]))
        assert persisted_action is not None
        assert persisted_action.execution_status == "not_executed"


def test_review_retrieval_survives_new_api_process(client: TestClient) -> None:
    _, _, review = _create_review(client)
    with TestClient(create_app()) as restarted_client:
        response = restarted_client.get(f"/api/v1/action-reviews/{review['id']}")
    assert response.status_code == 200
    assert response.json() == review


def test_concurrent_review_creation_produces_one_review(client: TestClient) -> None:
    _, action = _assessment_and_action(client)
    action_id = uuid.UUID(action["id"])
    barrier = Barrier(2)

    def create() -> bool:
        barrier.wait()
        with SessionLocal() as session:
            _, created = create_or_get_action_review(session, action_id)
            return created

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _: create(), range(2)))

    assert sorted(outcomes) == [False, True]
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(ActionReview)) == 1


@pytest.mark.parametrize(
    "decision",
    ["approved", "rejected", "deferred", "revision_requested"],
)
def test_authorized_reviewer_can_submit_each_terminal_decision(
    client: TestClient,
    decision: str,
) -> None:
    _, _, review = _create_review(client)

    response = client.post(
        f"/api/v1/action-reviews/{review['id']}/decisions",
        headers=REVIEWER_HEADERS,
        json={"decision": decision, "rationale": f"Rationale for {decision}."},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == decision
    assert body["completed_at"] is not None
    assert len(body["decision_history"]) == 1
    persisted = body["current_decision"]
    assert persisted["reviewer_identity"] == "reviewer@example.com"
    assert persisted["reviewer_role"] == "reviewer"
    assert persisted["rationale"] == f"Rationale for {decision}."
    assert persisted["created_at"]
    assert (body["effective_approved_action"] is not None) == (decision == "approved")


def test_approval_with_edits_derives_effective_action_and_preserves_original(
    client: TestClient,
) -> None:
    _, action, review = _create_review(client)
    edited_description = "Assign the updated international travel course."

    response = client.post(
        f"/api/v1/action-reviews/{review['id']}/decisions",
        headers=REVIEWER_HEADERS,
        json={
            "decision": "approved",
            "rationale": "The action is appropriate with a clearer description.",
            "edited_action": {
                "description": edited_description,
                "due_date": "2026-08-20",
            },
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["original_action"]["description"] == action["description"]
    assert body["current_decision"]["edited_action"] == {
        "description": edited_description,
        "due_date": "2026-08-20",
    }
    assert body["effective_approved_action"]["description"] == edited_description
    assert body["effective_approved_action"]["due_date"] == "2026-08-20"
    assert body["effective_approved_action"]["execution_status"] == "not_executed"

    assessment = client.get(f"/api/v1/impact-assessments/{body['assessment_id']}").json()
    persisted_action = next(
        item for item in assessment["proposed_actions"] if item["id"] == action["id"]
    )
    assert persisted_action == action


@pytest.mark.parametrize(
    ("headers", "expected_code"),
    [
        ({}, "reviewer_not_authorized"),
        (
            {
                "X-ChangeOps-Actor": "viewer@example.com",
                "X-ChangeOps-Role": "viewer",
            },
            "reviewer_not_authorized",
        ),
    ],
)
def test_decision_requires_authorized_request_identity(
    client: TestClient,
    headers: dict[str, str],
    expected_code: str,
) -> None:
    _, _, review = _create_review(client)
    response = client.post(
        f"/api/v1/action-reviews/{review['id']}/decisions",
        headers=headers,
        json={"decision": "approved", "rationale": "Looks right."},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == expected_code


@pytest.mark.parametrize(
    "payload",
    [
        {
            "decision": "approved",
            "rationale": "Invalid immutable edit.",
            "edited_action": {"action_type": "update_document"},
        },
        {
            "decision": "rejected",
            "rationale": "Edits do not belong on rejection.",
            "edited_action": {"description": "Changed"},
        },
        {
            "decision": "approved",
            "rationale": "",
        },
    ],
)
def test_invalid_decisions_return_stable_validation_error(
    client: TestClient,
    payload: dict,
) -> None:
    _, _, review = _create_review(client)
    response = client.post(
        f"/api/v1/action-reviews/{review['id']}/decisions",
        headers=REVIEWER_HEADERS,
        json=payload,
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] in {
        "invalid_action_edit",
        "invalid_review_decision",
    }


def test_terminal_review_returns_conflict_on_second_decision(
    client: TestClient,
) -> None:
    _, _, review = _create_review(client)
    url = f"/api/v1/action-reviews/{review['id']}/decisions"
    accepted = client.post(
        url,
        headers=REVIEWER_HEADERS,
        json={"decision": "approved", "rationale": "Accepted."},
    )
    conflict = client.post(
        url,
        headers={
            "X-ChangeOps-Actor": "second-reviewer@example.com",
            "X-ChangeOps-Role": "reviewer",
        },
        json={"decision": "rejected", "rationale": "Too late."},
    )
    assert accepted.status_code == 201
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "action_review_already_decided"
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(ActionReviewDecision)) == 1


def test_concurrent_decisions_accept_exactly_one(client: TestClient) -> None:
    _, _, review = _create_review(client)
    barrier = Barrier(2)

    def decide(decision: str) -> str:
        barrier.wait()
        try:
            with SessionLocal() as session:
                submit_action_review_decision(
                    session,
                    uuid.UUID(review["id"]),
                    ReviewDecisionInput(
                        decision=decision,
                        rationale=f"Concurrent {decision}.",
                    ),
                    ReviewActor(
                        identity=f"{decision}@example.com",
                        role="reviewer",
                    ),
                )
            return "accepted"
        except ReviewValidationError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(decide, ("approved", "rejected")))

    assert sorted(outcomes) == ["accepted", "action_review_already_decided"]
    with SessionLocal() as session:
        persisted_review = session.get(ActionReview, uuid.UUID(review["id"]))
        persisted_decision = session.scalar(
            select(ActionReviewDecision).where(
                ActionReviewDecision.action_review_id == uuid.UUID(review["id"])
            )
        )
        assert persisted_review is not None and persisted_decision is not None
        assert persisted_review.status == persisted_decision.decision


def test_database_enforces_review_and_decision_immutability(
    client: TestClient,
) -> None:
    _, _, review = _create_review(client)
    decided = client.post(
        f"/api/v1/action-reviews/{review['id']}/decisions",
        headers=REVIEWER_HEADERS,
        json={"decision": "approved", "rationale": "Approved."},
    ).json()
    decision_id = decided["current_decision"]["id"]

    statements = [
        (
            "UPDATE action_review_decisions SET rationale = 'changed' WHERE id = :id",
            decision_id,
        ),
        ("DELETE FROM action_review_decisions WHERE id = :id", decision_id),
        (
            "UPDATE action_reviews SET original_action_snapshot = "
            "jsonb_set(original_action_snapshot, '{description}', '\"changed\"') "
            "WHERE id = :id",
            review["id"],
        ),
        ("DELETE FROM action_reviews WHERE id = :id", review["id"]),
    ]
    for statement, identifier in statements:
        with pytest.raises(DBAPIError), SessionLocal.begin() as session:
            session.execute(text(statement), {"id": identifier})


def test_database_rejects_pending_original_snapshot_update(client: TestClient) -> None:
    _, _, review = _create_review(client)
    with pytest.raises(DBAPIError), SessionLocal.begin() as session:
        session.execute(
            text(
                "UPDATE action_reviews SET original_action_snapshot = "
                "jsonb_set(original_action_snapshot, '{description}', '\"changed\"') "
                "WHERE id = :id"
            ),
            {"id": review["id"]},
        )


def test_database_keeps_proposed_action_immutable(client: TestClient) -> None:
    _, action, _ = _create_review(client)
    statements = [
        (
            "UPDATE proposed_actions SET description = 'changed' WHERE id = :id",
            action["id"],
        ),
        ("DELETE FROM proposed_actions WHERE id = :id", action["id"]),
    ]
    for statement, identifier in statements:
        with pytest.raises(DBAPIError), SessionLocal.begin() as session:
            session.execute(text(statement), {"id": identifier})


def test_database_rejects_duplicate_review_and_lifecycle_mismatch(
    client: TestClient,
) -> None:
    assessment_1, action_1, review = _create_review(client)
    assessment_2, action_2 = _assessment_and_action(client)

    with pytest.raises(IntegrityError), SessionLocal.begin() as session:
        session.add(
            ActionReview(
                id=uuid.uuid4(),
                assessment_id=uuid.UUID(assessment_1["id"]),
                proposed_action_id=uuid.UUID(action_1["id"]),
                status="pending",
                original_action_snapshot=review["original_action"],
                review_context_snapshot=review["review_context"],
                created_at=datetime.now(UTC),
                completed_at=None,
            )
        )

    with pytest.raises(IntegrityError), SessionLocal.begin() as session:
        session.add(
            ActionReview(
                id=uuid.uuid4(),
                assessment_id=uuid.UUID(assessment_2["id"]),
                proposed_action_id=uuid.UUID(action_1["id"]),
                status="pending",
                original_action_snapshot={
                    **review["original_action"],
                    "assessment_id": assessment_2["id"],
                },
                review_context_snapshot={
                    **review["review_context"],
                    "enterprise_impact_id": action_2["enterprise_impact_id"],
                },
                created_at=datetime.now(UTC),
                completed_at=None,
            )
        )
