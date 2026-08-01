import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from changeops.ai.model_factory import InterpretationProviderConfigurationError
from changeops.ai.policy_interpreter import ConfiguredInterpretationModel
from changeops.api.policy_extractions import extraction_model_dependency
from changeops.api.policy_interpretation import interpretation_model_dependency
from changeops.db.models import (
    ChangePlan,
    PolicyAnalysisRun,
)
from changeops.db.session import SessionLocal
from changeops.domain.policy_interpretation import CandidateChangePlan
from changeops.services.seed_service import POLICY_CHANGE_ID, POLICY_TEXT
from tests.integration.test_policy_extraction_api import configured_fixture_model


class FixtureInterpretationModel:
    def __init__(self, candidate: dict[str, Any] | None = None, *, fail: bool = False) -> None:
        self.candidate = candidate
        self.fail = fail

    def with_structured_output(self, schema, *, include_raw: bool) -> RunnableLambda:
        def respond(_: Any) -> dict[str, Any]:
            if self.fail:
                raise TimeoutError("sensitive provider detail")
            return {
                "raw": AIMessage(content="fixture interpretation"),
                "parsed": CandidateChangePlan.model_validate(self.candidate),
                "parsing_error": None,
            }

        return RunnableLambda(respond)


def configured_interpreter(
    candidate: dict[str, Any] | None = None, *, fail: bool = False
) -> ConfiguredInterpretationModel:
    if candidate is None:
        quote = "U.S.-based"
        start = POLICY_TEXT.index(quote)
        candidate = {
            "summary": "One grounded review concern.",
            "coverage_gaps": [
                {
                    "finding_key": "review-scope-definition",
                    "title": "Review scope definition",
                    "observed_limitation": "The persisted artifacts do not define U.S.-based.",
                    "why_it_matters": "Scope interpretation may require human review.",
                    "recommended_review_action": (
                        "Review the scope definition with the policy owner."
                    ),
                    "policy_spans": [
                        {
                            "policy_change_id": POLICY_CHANGE_ID,
                            "start": start,
                            "end": start + len(quote),
                            "quote": quote,
                        }
                    ],
                }
            ],
        }
    return ConfiguredInterpretationModel(
        model=FixtureInterpretationModel(candidate, fail=fail),
        provider="fixture",
        identifier="interpretation-v1",
    )


def completed_assessment(client) -> tuple[str, str]:
    client.app.dependency_overrides[extraction_model_dependency] = lambda: (
        configured_fixture_model()
    )
    response = client.post(
        "/api/v1/policy-analysis-runs", json={"policy_change_id": POLICY_CHANGE_ID}
    )
    assert response.status_code == 201
    assert response.json()["status"] == "completed", response.json()
    return response.json()["id"], response.json()["assessment_id"]


def test_completed_assessment_produces_one_separate_idempotent_plan(client) -> None:
    run_id, assessment_id = completed_assessment(client)
    before = client.get(f"/api/v1/impact-assessments/{assessment_id}").json()
    client.app.dependency_overrides[interpretation_model_dependency] = lambda: (
        configured_interpreter
    )

    created = client.post(f"/api/v1/impact-assessments/{assessment_id}/change-plans")

    def unavailable_provider() -> ConfiguredInterpretationModel:
        raise InterpretationProviderConfigurationError("provider disabled after creation")

    client.app.dependency_overrides[interpretation_model_dependency] = lambda: unavailable_provider
    repeated = client.post(f"/api/v1/impact-assessments/{assessment_id}/change-plans")

    assert created.status_code == 201, created.text
    assert repeated.status_code == 200
    assert repeated.json() == created.json()
    assert created.json()["policy_analysis_run_id"] == run_id
    assert created.json()["change_plan"]["coverage_gaps"][0]["conclusion_type"] == "review_concern"
    assert client.get(created.headers["Location"]).json() == created.json()
    lookup = client.get(f"/api/v1/impact-assessments/{assessment_id}/change-plan")
    assert lookup.json() == created.json()
    assert client.get(f"/api/v1/impact-assessments/{assessment_id}").json() == before
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(ChangePlan)) == 1
        run = session.get(PolicyAnalysisRun, uuid.UUID(run_id))
        assert run is not None and run.status == "completed"


def test_provider_failure_is_auditable_and_does_not_change_completed_run(client) -> None:
    run_id, assessment_id = completed_assessment(client)
    client.app.dependency_overrides[interpretation_model_dependency] = lambda: (
        lambda: configured_interpreter(fail=True)
    )
    response = client.post(f"/api/v1/impact-assessments/{assessment_id}/change-plans")
    assert response.status_code == 502, response.text
    attempt_id = response.json()["detail"]["attempt_id"]
    attempt = client.get(f"/api/v1/policy-interpretation-attempts/{attempt_id}")
    assert attempt.status_code == 200
    assert attempt.json()["status"] == "provider_failed"
    assert attempt.json()["failure_code"] == "interpretation_provider_error"
    assert "sensitive provider detail" not in attempt.json()["failure_message"]
    with SessionLocal() as session:
        assert session.get(PolicyAnalysisRun, uuid.UUID(run_id)).status == "completed"
        assert session.scalar(select(func.count()).select_from(ChangePlan)) == 0


def test_invalid_reference_persists_attempt_without_plan(client) -> None:
    _, assessment_id = completed_assessment(client)
    candidate = configured_interpreter().model.candidate
    candidate["coverage_gaps"][0]["impact_references"] = [
        {"assessment_id": assessment_id, "impact_id": str(uuid.uuid4())}
    ]
    client.app.dependency_overrides[interpretation_model_dependency] = lambda: (
        lambda: configured_interpreter(candidate)
    )
    response = client.post(f"/api/v1/impact-assessments/{assessment_id}/change-plans")
    assert response.status_code == 422
    attempt = client.get(
        f"/api/v1/policy-interpretation-attempts/{response.json()['detail']['attempt_id']}"
    ).json()
    assert attempt["status"] == "invalid"
    assert attempt["failure_code"] == "interpretation_invalid_reference"


def test_interpretation_attempts_reject_update_and_delete(client) -> None:
    _, assessment_id = completed_assessment(client)
    client.app.dependency_overrides[interpretation_model_dependency] = lambda: (
        lambda: configured_interpreter(fail=True)
    )
    response = client.post(f"/api/v1/impact-assessments/{assessment_id}/change-plans")
    attempt_id = response.json()["detail"]["attempt_id"]
    with pytest.raises(DBAPIError), SessionLocal.begin() as session:
        session.execute(
            text(
                "UPDATE policy_interpretation_attempts "
                "SET failure_message = 'changed' WHERE id = :id"
            ),
            {"id": attempt_id},
        )


def test_direct_assessment_without_completed_run_cannot_be_interpreted(client) -> None:
    assessment = client.post(f"/api/v1/policy-changes/{POLICY_CHANGE_ID}/impact-assessments").json()
    client.app.dependency_overrides[interpretation_model_dependency] = lambda: (
        configured_interpreter
    )
    response = client.post(f"/api/v1/impact-assessments/{assessment['id']}/change-plans")
    assert response.status_code == 422


def test_database_rejects_change_plan_lifecycle_mismatches(client) -> None:
    run_1, assessment_1 = completed_assessment(client)
    run_2, assessment_2 = completed_assessment(client)
    client.app.dependency_overrides[interpretation_model_dependency] = lambda: (
        configured_interpreter
    )
    accepted = client.post(f"/api/v1/impact-assessments/{assessment_1}/change-plans")
    assert accepted.status_code == 201
    attempt_id = accepted.json()["interpretation_attempt_id"]

    mismatches = (
        (run_1, assessment_2),
        (run_2, assessment_2),
    )
    for run_id, assessment_id in mismatches:
        with pytest.raises(IntegrityError), SessionLocal.begin() as session:
            session.add(
                ChangePlan(
                    id=uuid.uuid4(),
                    policy_analysis_run_id=uuid.UUID(run_id),
                    impact_assessment_id=uuid.UUID(assessment_id),
                    interpretation_attempt_id=uuid.UUID(attempt_id),
                    schema_version="policy-interpretation-v1",
                    validated_plan={
                        "summary": "Invalid lifecycle fixture.",
                        "coverage_gaps": [],
                        "schema_version": "policy-interpretation-v1",
                    },
                    created_at=datetime.now(UTC),
                )
            )
