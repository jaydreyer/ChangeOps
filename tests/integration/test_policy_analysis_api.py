import uuid
from copy import deepcopy
from typing import Any

from langchain_core.runnables import RunnableLambda
from sqlalchemy import func, select

from changeops.ai.policy_extractor import ConfiguredExtractionModel
from changeops.api.policy_extractions import extraction_model_dependency
from changeops.db.models import (
    ImpactAssessment,
    PolicyAnalysisClarification,
    PolicyAnalysisRun,
    PolicyChange,
    PolicyExtractionAttempt,
)
from changeops.db.session import SessionLocal
from changeops.services.seed_service import POLICY_CHANGE_ID, STRUCTURED_RULES
from changeops.workflows.policy_analysis import execute_policy_analysis
from tests.integration.test_policy_extraction_api import configured_fixture_model
from tests.policy_extraction_fixtures import accepted_model_response, canonical_proposal_payload


class TransientThenSuccessfulModel:
    def __init__(self) -> None:
        self.invocations = 0

    def with_structured_output(self, schema, *, include_raw: bool) -> RunnableLambda:
        def respond(_: Any) -> dict[str, Any]:
            self.invocations += 1
            if self.invocations == 1:
                raise TimeoutError("fixture transient failure")
            return accepted_model_response(canonical_proposal_payload())

        return RunnableLambda(respond)


def test_accepted_policy_completes_with_one_assessment_and_no_policy_mutation(client) -> None:
    client.app.dependency_overrides[extraction_model_dependency] = lambda: (
        configured_fixture_model()
    )

    response = client.post(
        "/api/v1/policy-analysis-runs",
        json={"policy_change_id": POLICY_CHANGE_ID},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed", body["failure_detail"]
    assert body["assessment_id"] is not None
    assert body["latest_extraction_attempt_id"] is not None
    assert body["clarifications"] == []
    assert all(item["source"] == "policy_text" for item in body["accepted_rule_provenance"])

    retrieved = client.get(response.headers["Location"])
    assert retrieved.status_code == 200
    assert retrieved.json() == body

    with SessionLocal() as session:
        run = session.get(PolicyAnalysisRun, uuid.UUID(body["id"]))
        policy = session.get(PolicyChange, POLICY_CHANGE_ID)
        assessment_count = session.scalar(
            select(func.count())
            .select_from(ImpactAssessment)
            .where(ImpactAssessment.policy_analysis_run_id == run.id)
        )
        assert policy is not None and policy.structured_rules == STRUCTURED_RULES
        assert assessment_count == 1


def test_material_clarification_pauses_and_human_answer_resumes_once(client) -> None:
    payload = canonical_proposal_payload()
    payload["candidate_rules"]["manager_approval"]["booking_before_effective_date_is_exempt"] = (
        False
    )
    client.app.dependency_overrides[extraction_model_dependency] = lambda: configured_fixture_model(
        accepted_model_response(payload)
    )

    create = client.post(
        "/api/v1/policy-analysis-runs",
        json={"policy_change_id": POLICY_CHANGE_ID},
    )

    assert create.status_code == 201
    paused = create.json()
    assert paused["status"] == "awaiting_clarification", paused["failure_detail"]
    assert paused["assessment_id"] is None
    assert len(paused["clarifications"]) == 1
    clarification = paused["clarifications"][0]
    assert clarification["status"] == "pending"
    assert clarification["expected_answer_contract"] == {
        "type": "literal",
        "allowed_values": [True],
    }
    assert client.get(create.headers["Location"]).json() == paused

    answer_url = (
        f"/api/v1/policy-analysis-runs/{paused['id']}/clarifications/{clarification['id']}/answer"
    )
    rejected = client.post(
        answer_url,
        json={"value": False, "responder_identity": "human-reviewer@example.test"},
    )
    assert rejected.status_code == 422
    still_paused = client.get(create.headers["Location"]).json()
    assert still_paused["status"] == "awaiting_clarification"
    assert still_paused["clarifications"][0]["status"] == "pending"

    answered = client.post(
        answer_url,
        json={"value": True, "responder_identity": "human-reviewer@example.test"},
    )

    assert answered.status_code == 200
    completed = answered.json()
    assert completed["status"] == "completed"
    assert completed["assessment_id"] is not None
    human = next(
        item for item in completed["accepted_rule_provenance"] if item["source"] == "human"
    )
    assert human["clarification_id"] == clarification["id"]
    assert human["responder_identity"] == "human-reviewer@example.test"

    duplicate = client.post(
        answer_url,
        json={"value": True, "responder_identity": "human-reviewer@example.test"},
    )
    assert duplicate.status_code == 409

    with SessionLocal() as session:
        run_id = uuid.UUID(paused["id"])
        attempt_count = session.scalar(
            select(func.count())
            .select_from(PolicyExtractionAttempt)
            .where(PolicyExtractionAttempt.policy_analysis_run_id == run_id)
        )
        clarification_count = session.scalar(
            select(func.count())
            .select_from(PolicyAnalysisClarification)
            .where(PolicyAnalysisClarification.policy_analysis_run_id == run_id)
        )
        assessment_count = session.scalar(
            select(func.count())
            .select_from(ImpactAssessment)
            .where(ImpactAssessment.policy_analysis_run_id == run_id)
        )
        assert attempt_count == 2
        assert clarification_count == 1
        assert assessment_count == 1


def test_malformed_output_exhausts_one_retry_with_append_only_attempts(client) -> None:
    malformed = {
        "raw": {"content": "{bad-json"},
        "parsed": None,
        "parsing_error": ValueError("invalid JSON"),
    }
    client.app.dependency_overrides[extraction_model_dependency] = lambda: configured_fixture_model(
        malformed
    )

    response = client.post(
        "/api/v1/policy-analysis-runs",
        json={"policy_change_id": POLICY_CHANGE_ID},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["failure_code"] == "retry_limit_exhausted", body
    assert body["retry_count"] == 1
    with SessionLocal() as session:
        run_id = uuid.UUID(body["id"])
        attempts = list(
            session.scalars(
                select(PolicyExtractionAttempt)
                .where(PolicyExtractionAttempt.policy_analysis_run_id == run_id)
                .order_by(PolicyExtractionAttempt.created_at)
            )
        )
        assert len(attempts) == 2
        assert attempts[0].id != attempts[1].id


def test_unsupported_policy_terminates_without_retry_clarification_or_assessment(client) -> None:
    payload = deepcopy(canonical_proposal_payload())
    payload["policy_family"] = "domestic_expense"
    payload["support_status"] = "unsupported"
    payload["candidate_rules"] = None
    payload["provenance"] = [
        item for item in payload["provenance"] if item["field_path"] == "policy_family"
    ]
    payload["findings"] = [
        {
            "kind": "unsupported",
            "code": "unsupported_policy_family",
            "message": "This policy family is unsupported.",
            "field_path": "policy_family",
            "provenance": {
                **payload["provenance"][0],
                "field_path": "finding.unsupported_policy_family",
            },
        }
    ]
    client.app.dependency_overrides[extraction_model_dependency] = lambda: configured_fixture_model(
        accepted_model_response(payload)
    )

    response = client.post(
        "/api/v1/policy-analysis-runs",
        json={"policy_change_id": POLICY_CHANGE_ID},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "unsupported"
    assert body["retry_count"] == 0
    assert body["clarifications"] == []
    assert body["assessment_id"] is None


def test_transient_provider_failure_recovers_with_one_fresh_attempt(client) -> None:
    model = TransientThenSuccessfulModel()
    client.app.dependency_overrides[extraction_model_dependency] = lambda: (
        ConfiguredExtractionModel(model=model, provider="fixture", identifier="transient-v1")
    )

    response = client.post(
        "/api/v1/policy-analysis-runs",
        json={"policy_change_id": POLICY_CHANGE_ID},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["retry_count"] == 1
    assert model.invocations == 2
    with SessionLocal() as session:
        attempts = list(
            session.scalars(
                select(PolicyExtractionAttempt)
                .where(PolicyExtractionAttempt.policy_analysis_run_id == uuid.UUID(body["id"]))
                .order_by(PolicyExtractionAttempt.created_at)
            )
        )
        assert len(attempts) == 2
        assert attempts[1].retry_reason == "provider_invocation_failed"


def test_unresolved_enterprise_course_fails_without_retry_or_assessment(client) -> None:
    payload = canonical_proposal_payload()
    payload["candidate_rules"]["security_training"]["course_name"] = "Uncatalogued Course"
    client.app.dependency_overrides[extraction_model_dependency] = lambda: configured_fixture_model(
        accepted_model_response(payload)
    )

    response = client.post(
        "/api/v1/policy-analysis-runs",
        json={"policy_change_id": POLICY_CHANGE_ID},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["failure_code"] == "enterprise_reference_unresolved"
    assert body["retry_count"] == 0
    assert body["assessment_id"] is None


def test_assessment_commit_is_recovered_after_run_association_crash(client) -> None:
    client.app.dependency_overrides[extraction_model_dependency] = lambda: (
        configured_fixture_model()
    )
    created = client.post(
        "/api/v1/policy-analysis-runs",
        json={"policy_change_id": POLICY_CHANGE_ID},
    ).json()
    run_id = uuid.UUID(created["id"])
    assessment_id = uuid.UUID(created["assessment_id"])

    with SessionLocal.begin() as session:
        run = session.get(PolicyAnalysisRun, run_id)
        assessment = session.get(ImpactAssessment, assessment_id)
        assert run is not None and assessment is not None
        assert assessment.policy_analysis_run_id == run.id
        run.status = "running"
        run.current_step = "create_assessment"
        run.assessment_id = None
        run.completed_at = None

    with SessionLocal() as fresh_session:
        execute_policy_analysis(fresh_session, run_id, configured_fixture_model())

    with SessionLocal() as verification_session:
        recovered = verification_session.get(PolicyAnalysisRun, run_id)
        assessment_count = verification_session.scalar(
            select(func.count())
            .select_from(ImpactAssessment)
            .where(ImpactAssessment.policy_analysis_run_id == run_id)
        )
        assert recovered is not None
        assert recovered.status == "completed"
        assert recovered.current_step == "terminal"
        assert recovered.assessment_id == assessment_id
        assert assessment_count == 1
