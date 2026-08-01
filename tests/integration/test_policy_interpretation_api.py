import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from changeops.ai.model_factory import InterpretationProviderConfigurationError
from changeops.ai.policy_interpreter import SYSTEM_PROMPT, ConfiguredInterpretationModel
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
        self.schema: type[CandidateChangePlan] | None = None
        self.method: str | None = None
        self.include_raw: bool | None = None
        self.inputs: list[Any] = []

    def with_structured_output(
        self,
        schema: type[CandidateChangePlan],
        *,
        method: Literal["function_calling"],
        include_raw: bool,
    ) -> RunnableLambda:
        self.schema = schema
        self.method = method
        self.include_raw = include_raw

        def respond(value: Any) -> dict[str, Any]:
            self.inputs.append(value)
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
    configured_model = configured_interpreter()
    client.app.dependency_overrides[interpretation_model_dependency] = lambda: (
        lambda: configured_model
    )

    created = client.post(f"/api/v1/impact-assessments/{assessment_id}/change-plans")

    def unavailable_provider() -> ConfiguredInterpretationModel:
        raise InterpretationProviderConfigurationError("provider disabled after creation")

    client.app.dependency_overrides[interpretation_model_dependency] = lambda: unavailable_provider
    repeated = client.post(f"/api/v1/impact-assessments/{assessment_id}/change-plans")

    assert created.status_code == 201, created.text
    assert isinstance(configured_model.model, FixtureInterpretationModel)
    assert configured_model.model.schema is CandidateChangePlan
    assert configured_model.model.method == "function_calling"
    assert configured_model.model.include_raw is True
    assert "top-level object has exactly summary and coverage_gaps" in SYSTEM_PROMPT
    assert "absence of effective_date\ninside accepted_rules is not a coverage gap" in SYSTEM_PROMPT
    assert "exactly one owner" in SYSTEM_PROMPT
    assert "either\nimpact_id or finding_id, never both" in SYSTEM_PROMPT
    rendered_prompt = "\n".join(
        str(message.content) for message in configured_model.model.inputs[0].to_messages()
    )
    assert '"policy_effective_date":"2026-09-01"' in rendered_prompt
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


def test_interpretation_resolves_exact_quote_with_incorrect_offsets(client) -> None:
    _, assessment_id = completed_assessment(client)
    candidate = configured_interpreter().model.candidate
    span = candidate["coverage_gaps"][0]["policy_spans"][0]
    expected_start = POLICY_TEXT.index(span["quote"])
    span["start"] = expected_start + 9
    span["end"] = span["start"] + len(span["quote"])
    client.app.dependency_overrides[interpretation_model_dependency] = lambda: (
        lambda: configured_interpreter(candidate)
    )

    response = client.post(f"/api/v1/impact-assessments/{assessment_id}/change-plans")

    assert response.status_code == 201, response.text
    resolved = response.json()["change_plan"]["coverage_gaps"][0]["policy_spans"][0]
    assert resolved["start"] == expected_start
    assert resolved["end"] == expected_start + len(resolved["quote"])
    assert POLICY_TEXT[resolved["start"] : resolved["end"]] == resolved["quote"]


def test_interpretation_rejects_quote_absent_from_policy(client) -> None:
    _, assessment_id = completed_assessment(client)
    candidate = configured_interpreter().model.candidate
    span = candidate["coverage_gaps"][0]["policy_spans"][0]
    span["quote"] = "invented policy language"
    span["end"] = span["start"] + len(span["quote"])
    client.app.dependency_overrides[interpretation_model_dependency] = lambda: (
        lambda: configured_interpreter(candidate)
    )

    response = client.post(f"/api/v1/impact-assessments/{assessment_id}/change-plans")

    assert response.status_code == 422
    attempt = client.get(
        f"/api/v1/policy-interpretation-attempts/{response.json()['detail']['attempt_id']}"
    ).json()
    assert attempt["failure_code"] == "interpretation_invalid_reference"
    assert {error["code"] for error in attempt["validation_errors"]} == {"policy_quote_mismatch"}


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
