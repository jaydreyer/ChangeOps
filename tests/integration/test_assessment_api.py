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
        "enterprise_impacts": 18,
        "impacts_by_domain": {
            "people": 6,
            "teams": 3,
            "systems": 2,
            "documents": 3,
            "training": 3,
            "customer_commitments": 1,
        },
    }
    assert len(body["worker_results"]) == 6
    assert len(body["findings"]) == 6
    assert len(body["evidence"]) >= 15
    assert len(body["proposed_actions"]) == 13
    assert len(body["unresolved_questions"]) == 8
    assert len(body["input_fingerprint"]) == 64
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
    assert all(action["enterprise_impact_id"] is not None for action in body["proposed_actions"])

    impacts = [
        impact
        for domain_impacts in body["enterprise_impacts"].values()
        for impact in domain_impacts
    ]
    assert len(impacts) == body["summary"]["enterprise_impacts"]
    for domain, domain_impacts in body["enterprise_impacts"].items():
        assert len(domain_impacts) == body["summary"]["impacts_by_domain"][domain]
        assert [item["sort_key"] for item in domain_impacts] == sorted(
            item["sort_key"] for item in domain_impacts
        )
    for impact in impacts:
        assert impact["evidence_ids"]
        assert [element["sequence"] for element in impact["relationship_path"]] == list(
            range(len(impact["relationship_path"]))
        )
        assert impact["relationship_path"][-1]["relationship_to_next"] is None

    impacted_source_keys = {item["source_key"] for item in impacts}
    assert {
        "system-travel-request",
        "system-learning-management",
        "document-international-travel-policy",
        "kb-international-travel-booking",
        "international-travel-security",
        "commitment-northwind-onsite",
    } <= impacted_source_keys
    assert {
        "team-domestic-operations",
        "system-expense-management",
        "document-expense-submission-guide",
        "commitment-contoso-launch",
    }.isdisjoint(impacted_source_keys)
    manager_impacts = body["enterprise_impacts"]["people"]
    assert {
        "worker-manager-mike-wilson",
        "worker-manager-anita-patel",
        "worker-manager-jennifer-brooks",
    } <= {item["source_key"] for item in manager_impacts if item["object_type"] == "manager"}

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
