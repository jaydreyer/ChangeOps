import json
import uuid

from fastapi.testclient import TestClient

from changeops.db.models import PolicyChange
from changeops.db.session import SessionLocal
from changeops.services.seed_service import POLICY_CHANGE_ID


def test_create_and_retrieve_golden_assessment(client: TestClient) -> None:
    create_response = client.post(f"/api/v1/policy-changes/{POLICY_CHANGE_ID}/impact-assessments")

    assert create_response.status_code == 201
    body = create_response.json()
    assert create_response.headers["location"] == (f"/api/v1/impact-assessments/{body['id']}")
    assert body["summary"] == {
        "affected_workers": 3,
        "unaffected_workers": 3,
        "manager_approvals_required": 2,
        "training_assignments_required": 2,
    }
    assert len(body["worker_results"]) == 6
    assert len(body["findings"]) == 6
    assert len(body["evidence"]) == 15
    assert len(body["proposed_actions"]) == 4
    assert len(body["unresolved_questions"]) == 8
    assert "approval_status" not in json.dumps(body)

    affected_workers = {
        result["worker"]["id"]
        for result in body["worker_results"]
        if result["classification"] == "affected"
    }
    assert affected_workers == {
        "worker-sarah-johnson",
        "worker-marcus-lee",
        "worker-david-miller",
    }
    exclusion_reasons = {
        result["worker"]["id"]: result["reason_codes"]
        for result in body["worker_results"]
        if result["classification"] == "unaffected"
    }
    assert exclusion_reasons == {
        "worker-elena-garcia": ["WORK_COUNTRY_OUT_OF_SCOPE"],
        "worker-priya-shah": ["DESTINATION_EXCLUDED"],
        "worker-thomas-green": ["DEPARTURE_BEFORE_EFFECTIVE_DATE"],
    }

    evidence_ids = {item["id"] for item in body["evidence"]}
    for finding in body["findings"]:
        assert finding["evidence_ids"]
        assert set(finding["evidence_ids"]) <= evidence_ids
    assert all(action["execution_status"] == "not_executed" for action in body["proposed_actions"])

    retrieve_response = client.get(create_response.headers["location"])
    assert retrieve_response.status_code == 200
    assert retrieve_response.json() == body


def test_missing_resources_return_stable_errors(client: TestClient) -> None:
    missing_policy = client.post("/api/v1/policy-changes/missing-policy/impact-assessments")
    assert missing_policy.status_code == 404
    assert missing_policy.json() == {
        "detail": {
            "code": "policy_change_not_found",
            "message": "Policy change was not found.",
        }
    }

    missing_assessment = client.get(f"/api/v1/impact-assessments/{uuid.uuid4()}")
    assert missing_assessment.status_code == 404
    assert missing_assessment.json() == {
        "detail": {
            "code": "impact_assessment_not_found",
            "message": "Impact assessment was not found.",
        }
    }


def test_invalid_structured_rules_are_rejected_without_an_assessment(
    client: TestClient,
) -> None:
    with SessionLocal.begin() as session:
        policy = session.get(PolicyChange, POLICY_CHANGE_ID)
        assert policy is not None
        policy.structured_rules = {"kind": "unsupported"}

    response = client.post(f"/api/v1/policy-changes/{POLICY_CHANGE_ID}/impact-assessments")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "policy_not_analyzable"
