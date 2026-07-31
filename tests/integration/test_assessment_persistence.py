import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from changeops.db.models import (
    AssessmentEnterpriseImpact,
    AssessmentImpactPathElement,
    AssessmentWorkerResult,
    EnterpriseSystem,
    ImpactAssessment,
    Trip,
)
from changeops.db.session import SessionLocal, engine
from changeops.main import create_app
from changeops.services import assessment_service
from changeops.services.assessment_service import get_impact_assessment
from changeops.services.seed_service import POLICY_CHANGE_ID


def create_assessment(client: TestClient) -> uuid.UUID:
    response = client.post(f"/api/v1/policy-changes/{POLICY_CHANGE_ID}/impact-assessments")
    assert response.status_code == 201
    return uuid.UUID(response.json()["id"])


def normalize_persisted_assessment(assessment: ImpactAssessment) -> dict[str, Any]:
    worker_results = sorted(
        assessment.worker_results,
        key=lambda item: (item.worker_id, item.trip_id),
    )
    findings = sorted(
        assessment.findings,
        key=lambda item: (
            item.worker_result.worker_id,
            item.rule_code,
            item.finding_type,
        ),
    )
    evidence = sorted(assessment.evidence, key=lambda item: item.evidence_key)
    actions = sorted(
        assessment.proposed_actions,
        key=lambda item: (
            item.worker_id or "",
            item.action_type,
            item.target_identifier,
        ),
    )
    questions = sorted(
        assessment.unresolved_questions,
        key=lambda item: item.sequence,
    )
    impacts = sorted(assessment.enterprise_impacts, key=lambda item: item.sort_key)
    return {
        "policy_change_id": assessment.policy_change_id,
        "status": assessment.status,
        "analyzer_version": assessment.analyzer_version,
        "input_fingerprint": assessment.input_fingerprint,
        "worker_results": [
            {
                "worker_id": item.worker_id,
                "trip_id": item.trip_id,
                "classification": item.classification,
                "explanation": item.explanation,
                "reason_codes": tuple(item.reason_codes),
            }
            for item in worker_results
        ],
        "findings": [
            {
                "worker_id": item.worker_result.worker_id,
                "finding_type": item.finding_type,
                "severity": item.severity,
                "rule_code": item.rule_code,
                "explanation": item.explanation,
                "evidence_keys": tuple(
                    evidence_item.evidence_key
                    for evidence_item in sorted(
                        item.evidence,
                        key=lambda evidence_item: evidence_item.evidence_key,
                    )
                ),
            }
            for item in findings
        ],
        "evidence": [
            {
                "evidence_key": item.evidence_key,
                "evidence_type": item.evidence_type,
                "source_type": item.source_type,
                "source_id": item.source_id,
                "label": item.label,
                "snapshot": item.snapshot,
            }
            for item in evidence
        ],
        "enterprise_impacts": [
            {
                "domain": item.domain,
                "object_type": item.object_type,
                "source_key": item.source_key,
                "display_name": item.display_name,
                "classification": item.classification,
                "explanation": item.explanation,
                "reason_code": item.reason_code,
                "sort_key": item.sort_key,
                "evidence_keys": tuple(
                    evidence_item.evidence_key
                    for evidence_item in sorted(
                        item.evidence,
                        key=lambda evidence_item: evidence_item.evidence_key,
                    )
                ),
                "relationship_path": tuple(
                    (
                        element.sequence,
                        element.object_type,
                        element.stable_key,
                        element.display_label,
                        element.relationship_to_next,
                    )
                    for element in sorted(
                        item.path_elements,
                        key=lambda element: element.sequence,
                    )
                ),
            }
            for item in impacts
        ],
        "proposed_actions": [
            {
                "finding": (
                    {
                        "worker_id": item.finding.worker_result.worker_id,
                        "rule_code": item.finding.rule_code,
                    }
                    if item.finding is not None
                    else None
                ),
                "enterprise_impact": (
                    {
                        "source_key": item.enterprise_impact.source_key,
                        "reason_code": item.enterprise_impact.reason_code,
                    }
                    if item.enterprise_impact is not None
                    else None
                ),
                "worker_id": item.worker_id,
                "action_type": item.action_type,
                "target_type": item.target_type,
                "target_identifier": item.target_identifier,
                "description": item.description,
                "due_date": item.due_date.isoformat() if item.due_date else None,
                "execution_status": item.execution_status,
            }
            for item in actions
        ],
        "unresolved_questions": [
            {
                "source_question_id": item.source_question_id,
                "sequence": item.sequence,
                "question": item.question,
            }
            for item in questions
        ],
    }


def load_normalized(assessment_id: uuid.UUID) -> dict[str, Any]:
    with SessionLocal() as session:
        assessment = get_impact_assessment(session, assessment_id)
        return normalize_persisted_assessment(assessment)


def test_equivalent_inputs_produce_equivalent_persisted_results(
    client: TestClient,
) -> None:
    first_id = create_assessment(client)
    second_id = create_assessment(client)

    assert first_id != second_id
    assert load_normalized(first_id) == load_normalized(second_id)


def test_later_assessment_does_not_modify_prior_snapshot(
    client: TestClient,
) -> None:
    first_id = create_assessment(client)
    first_before = load_normalized(first_id)

    with SessionLocal.begin() as session:
        trip = session.get(Trip, "trip-sarah-france")
        assert trip is not None
        trip.destination_country = "CA"

    second_id = create_assessment(client)
    first_after = load_normalized(first_id)
    second = load_normalized(second_id)

    assert first_after == first_before
    assert second != first_before
    assert second["input_fingerprint"] != first_before["input_fingerprint"]


def test_assessment_survives_new_app_and_database_connections() -> None:
    with TestClient(create_app()) as first_client:
        assessment_id = create_assessment(first_client)

    engine.dispose()

    with TestClient(create_app()) as restarted_client:
        response = restarted_client.get(f"/api/v1/impact-assessments/{assessment_id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(assessment_id)


def test_relevant_enterprise_source_change_updates_only_later_assessment(
    client: TestClient,
) -> None:
    first_id = create_assessment(client)
    first_before = load_normalized(first_id)

    with SessionLocal.begin() as session:
        system = session.get(EnterpriseSystem, "system-travel-request")
        assert system is not None
        system.name = "Acme Travel Approval"

    second_id = create_assessment(client)
    first_after = load_normalized(first_id)
    second = load_normalized(second_id)

    assert first_after == first_before
    assert second["input_fingerprint"] != first_before["input_fingerprint"]
    assert any(
        item["display_name"] == "Acme Travel Approval" for item in second["enterprise_impacts"]
    )


def test_failure_after_partial_flush_rolls_back_complete_assessment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_evidence_persistence(**_: Any) -> dict[str, Any]:
        raise RuntimeError("simulated evidence failure")

    monkeypatch.setattr(
        assessment_service,
        "_persist_evidence",
        fail_evidence_persistence,
    )

    with TestClient(create_app(), raise_server_exceptions=False) as failing_client:
        response = failing_client.post(
            f"/api/v1/policy-changes/{POLICY_CHANGE_ID}/impact-assessments"
        )

    assert response.status_code == 500
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(ImpactAssessment)) == 0
        assert session.scalar(select(func.count()).select_from(AssessmentWorkerResult)) == 0
        assert session.scalar(select(func.count()).select_from(AssessmentEnterpriseImpact)) == 0
        assert session.scalar(select(func.count()).select_from(AssessmentImpactPathElement)) == 0
