import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DatabaseError

from changeops.ai.policy_extractor import ConfiguredExtractionModel
from changeops.api.policy_extractions import extraction_model_dependency
from changeops.db.models import PolicyChange, PolicyExtractionAttempt
from changeops.db.session import SessionLocal
from changeops.services.seed_service import POLICY_CHANGE_ID, STRUCTURED_RULES
from tests.policy_extraction_fixtures import (
    FixtureStructuredOutputModel,
    accepted_model_response,
    canonical_proposal_payload,
)


def configured_fixture_model(
    response: dict | None = None,
) -> ConfiguredExtractionModel:
    return ConfiguredExtractionModel(
        model=FixtureStructuredOutputModel(
            response or accepted_model_response(canonical_proposal_payload())
        ),
        provider="fixture",
        identifier="golden-v1",
    )


def test_create_and_retrieve_accepted_extraction_attempt(client) -> None:
    client.app.dependency_overrides[extraction_model_dependency] = configured_fixture_model

    create_response = client.post(f"/api/v1/policy-changes/{POLICY_CHANGE_ID}/extraction-attempts")

    assert create_response.status_code == 201
    body = create_response.json()
    assert body["validation_outcome"] == "accepted"
    assert body["support_status"] == "supported"
    assert body["accepted_rules"] == STRUCTURED_RULES
    assert body["candidate_rules"]["security_training"] == {
        "course_name": "International Travel Security"
    }
    assert body["metadata"] == {
        "model_provider": "fixture",
        "model_identifier": "golden-v1",
        "prompt_version": "international-travel-extraction-v1",
        "schema_version": "policy-extraction-v1",
    }

    location = create_response.headers["Location"]
    retrieve_response = client.get(location)
    assert retrieve_response.status_code == 200
    assert retrieve_response.json() == body

    with SessionLocal() as session:
        policy = session.get(PolicyChange, POLICY_CHANGE_ID)
        assert policy is not None
        assert policy.structured_rules == STRUCTURED_RULES


def test_reextraction_creates_a_new_attempt(client) -> None:
    client.app.dependency_overrides[extraction_model_dependency] = configured_fixture_model

    first = client.post(f"/api/v1/policy-changes/{POLICY_CHANGE_ID}/extraction-attempts")
    second = client.post(f"/api/v1/policy-changes/{POLICY_CHANGE_ID}/extraction-attempts")

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    with SessionLocal() as session:
        count = session.scalar(select(func.count()).select_from(PolicyExtractionAttempt))
    assert count == 2


def test_structured_output_failure_is_persisted_and_inspectable(client) -> None:
    response = {
        "raw": {"content": "{bad-json"},
        "parsed": None,
        "parsing_error": ValueError("invalid JSON"),
    }
    client.app.dependency_overrides[extraction_model_dependency] = lambda: configured_fixture_model(
        response
    )

    create_response = client.post(f"/api/v1/policy-changes/{POLICY_CHANGE_ID}/extraction-attempts")

    assert create_response.status_code == 201
    body = create_response.json()
    assert body["validation_outcome"] == "validation_failed"
    assert body["support_status"] is None
    assert body["accepted_rules"] is None
    assert body["raw_output"] == {"content": "{bad-json"}
    assert body["validation_errors"][0]["code"] == "structured_output_failure"
    retrieve_response = client.get(create_response.headers["Location"])
    assert retrieve_response.json() == body


def test_attempt_rows_reject_update_and_delete(client) -> None:
    client.app.dependency_overrides[extraction_model_dependency] = configured_fixture_model
    response = client.post(f"/api/v1/policy-changes/{POLICY_CHANGE_ID}/extraction-attempts")
    attempt_id = response.json()["id"]

    with SessionLocal() as session:
        with pytest.raises(DatabaseError, match="append-only"):
            session.execute(
                text(
                    "UPDATE policy_extraction_attempts "
                    "SET model_identifier = 'mutated' WHERE id = :attempt_id"
                ),
                {"attempt_id": attempt_id},
            )
            session.commit()
        session.rollback()

        with pytest.raises(DatabaseError, match="append-only"):
            session.execute(
                text("DELETE FROM policy_extraction_attempts WHERE id = :attempt_id"),
                {"attempt_id": attempt_id},
            )
            session.commit()
        session.rollback()


def test_extraction_endpoint_reports_missing_provider_configuration(client) -> None:
    response = client.post(f"/api/v1/policy-changes/{POLICY_CHANGE_ID}/extraction-attempts")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "extraction_provider_not_configured"
