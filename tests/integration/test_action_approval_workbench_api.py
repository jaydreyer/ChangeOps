import uuid

from sqlalchemy import func, select, text

from changeops.db.models import (
    ActionApprovalRun,
    ActionApprovalRunItem,
    ActionApprovalRunTransition,
    ActionReview,
    ActionReviewDecision,
    ProposedAction,
)
from changeops.db.session import SessionLocal
from tests.integration.test_action_approval_api import REVIEWER_HEADERS, _create_run


def _counts() -> tuple[int, ...]:
    models = (
        ActionApprovalRun,
        ActionApprovalRunItem,
        ActionApprovalRunTransition,
        ActionReview,
        ActionReviewDecision,
        ProposedAction,
    )
    with SessionLocal() as session:
        return tuple(
            session.scalar(select(func.count()).select_from(model)) or 0 for model in models
        )


def test_workbench_resolves_ordered_golden_review_context_without_mutation(client) -> None:
    assessment, run = _create_run(client)
    before = _counts()

    response = client.get(f"/api/v1/action-approval-runs/{run['id']}/workbench")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["run"] == run
    assert body["assessment"] == {
        "id": assessment["id"],
        "policy_change_id": assessment["policy_change_id"],
        "completed_at": assessment["completed_at"],
        "affected_worker_count": assessment["summary"]["affected_workers"],
        "enterprise_impact_count": assessment["summary"]["enterprise_impacts"],
        "proposed_action_count": len(assessment["proposed_actions"]),
    }
    assert [item["sequence"] for item in body["items"]] == list(range(13))
    assert all(
        item["review"]["original_action"]["execution_status"] == "not_executed"
        for item in body["items"]
    )
    assert all(item["review"]["review_context"]["reason_code"] for item in body["items"])
    assert all(item["evidence"] for item in body["items"])
    assert any(item["finding"] is not None for item in body["items"])
    assert any(item["enterprise_impact"] is not None for item in body["items"])
    impact_item = next(item for item in body["items"] if item["enterprise_impact"] is not None)
    path = impact_item["enterprise_impact"]["relationship_path"]
    assert [element["sequence"] for element in path] == list(range(len(path)))
    assert any(
        evidence["source_type"] == "relationship_path" for evidence in impact_item["evidence"]
    )
    assert _counts() == before


def test_workbench_returns_mixed_decisions_and_effective_approved_edit(client) -> None:
    _, run = _create_run(client)
    first, second = run["items"][:2]
    approved = client.post(
        f"/api/v1/action-reviews/{first['review_id']}/decisions",
        headers=REVIEWER_HEADERS,
        json={
            "decision": "approved",
            "rationale": "Approve with a clearer owner-facing description.",
            "edited_action": {
                "description": "Coordinate the required action with the responsible owner.",
                "due_date": "2026-08-20",
            },
        },
    )
    rejected = client.post(
        f"/api/v1/action-reviews/{second['review_id']}/decisions",
        headers=REVIEWER_HEADERS,
        json={"decision": "rejected", "rationale": "The proposed action is not required."},
    )
    assert approved.status_code == 201
    assert rejected.status_code == 201

    body = client.get(f"/api/v1/action-approval-runs/{run['id']}/workbench").json()

    assert body["run"]["summary"]["approved"] == 1
    assert body["run"]["summary"]["rejected"] == 1
    approved_item = body["items"][0]["review"]
    assert (
        approved_item["original_action"]["description"]
        != (approved_item["effective_approved_action"]["description"])
    )
    assert approved_item["effective_approved_action"]["due_date"] == "2026-08-20"
    assert approved_item["effective_approved_action"]["execution_status"] == "not_executed"
    assert body["items"][1]["review"]["current_decision"]["decision"] == "rejected"


def test_workbench_unknown_run_and_missing_evidence_are_stable_errors(client) -> None:
    unknown = client.get(f"/api/v1/action-approval-runs/{uuid.uuid4()}/workbench")
    assert unknown.status_code == 404
    assert unknown.json()["detail"]["code"] == "action_approval_run_not_found"

    _, run = _create_run(client)
    review_id = run["items"][0]["review_id"]
    with SessionLocal.begin() as session:
        session.execute(text("ALTER TABLE action_reviews DISABLE TRIGGER action_reviews_immutable"))
        session.execute(
            text(
                "UPDATE action_reviews "
                "SET review_context_snapshot = jsonb_set("
                "review_context_snapshot, '{evidence_keys}', "
                "'[\"missing:persisted-reference\"]'::jsonb) "
                "WHERE id = :review_id"
            ),
            {"review_id": review_id},
        )
        session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        session.execute(text("ALTER TABLE action_reviews ENABLE TRIGGER action_reviews_immutable"))

    inconsistent = client.get(f"/api/v1/action-approval-runs/{run['id']}/workbench")
    assert inconsistent.status_code == 409
    assert inconsistent.json()["detail"] == {
        "code": "approval_workbench_inconsistent",
        "message": ("Review evidence reference cannot be resolved: missing:persisted-reference."),
    }
