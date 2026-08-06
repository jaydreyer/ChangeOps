import uuid
from copy import deepcopy
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session

from changeops.api.policy_extractions import extraction_model_dependency
from changeops.db.models import (
    CommitmentAssignment,
    CustomerCommitment,
    EnterpriseDocument,
    EnterpriseSystem,
    Organization,
    PolicyAnalysisClarification,
    PolicyAnalysisRun,
    PolicyChange,
    PolicyComparison,
    PolicyComparisonDifference,
    PolicyComparisonImpactDelta,
    PolicyComparisonImpactDeltaItem,
    PolicyDocumentDependency,
    PolicyExtractionAttempt,
    PolicySystemDependency,
    PolicyTrainingDependency,
    Team,
    TrainingCourse,
    TrainingRecord,
    Trip,
    Worker,
    WorkerTeamMembership,
)
from changeops.db.session import SessionLocal
from changeops.services import policy_comparison_service
from changeops.services.demo_reset_service import reset_demo_workflows
from changeops.services.enterprise_impact_delta_service import EnterpriseImpactDeltaIntegrityError
from changeops.services.seed_service import POLICY_CHANGE_ID, PROPOSED_POLICY_CHANGE_ID
from tests.integration.test_policy_extraction_api import configured_fixture_model
from tests.policy_extraction_fixtures import accepted_model_response, proposed_revision_payload

ACTOR_HEADERS = {"X-ChangeOps-Actor": "portfolio-reviewer"}

ENTERPRISE_CATALOG_MODELS = (
    Worker,
    Team,
    WorkerTeamMembership,
    Trip,
    EnterpriseSystem,
    EnterpriseDocument,
    TrainingCourse,
    TrainingRecord,
    CustomerCommitment,
    CommitmentAssignment,
)


def _shared_enterprise_catalog_state(
    session: Session,
) -> dict[str, tuple[tuple[object, ...], ...]]:
    state = {}
    for model in ENTERPRISE_CATALOG_MODELS:
        table = model.__table__
        rows = session.execute(select(*table.columns).order_by(*table.primary_key.columns)).all()
        state[table.name] = tuple(tuple(row) for row in rows)
    return state


def _policy_dependency_business_state(
    session: Session,
    policy_change_id: str,
) -> dict[str, tuple[tuple[object, ...], ...]]:
    dependency_contracts = (
        (
            PolicySystemDependency,
            ("rule_code", "system_id", "relationship_type", "explanation"),
        ),
        (
            PolicyDocumentDependency,
            (
                "rule_code",
                "document_id",
                "relationship_type",
                "impact_classification",
                "explanation",
            ),
        ),
        (
            PolicyTrainingDependency,
            ("rule_code", "course_id", "relationship_type", "explanation"),
        ),
    )
    state = {}
    for model, field_names in dependency_contracts:
        fields = tuple(getattr(model, field_name) for field_name in field_names)
        rows = session.execute(
            select(*fields).where(model.policy_change_id == policy_change_id).order_by(*fields)
        ).all()
        state[model.__tablename__] = tuple(tuple(row) for row in rows)
    return state


def _complete_both_policy_analyses(client) -> tuple[dict, dict]:
    client.app.dependency_overrides[extraction_model_dependency] = lambda: (
        configured_fixture_model()
    )
    baseline = client.post(
        "/api/v1/policy-analysis-runs",
        json={"policy_change_id": POLICY_CHANGE_ID},
    )
    assert baseline.status_code == 201

    client.app.dependency_overrides[extraction_model_dependency] = lambda: configured_fixture_model(
        accepted_model_response(proposed_revision_payload())
    )
    proposed = client.post(
        "/api/v1/policy-analysis-runs",
        json={"policy_change_id": PROPOSED_POLICY_CHANGE_ID},
    )
    assert proposed.status_code == 201
    return baseline.json(), proposed.json()


def test_seeded_comparison_uses_same_enterprise_catalog_state_for_both_assessments(
    client,
) -> None:
    with SessionLocal() as session:
        initial_catalog = _shared_enterprise_catalog_state(session)
        assert _policy_dependency_business_state(
            session, POLICY_CHANGE_ID
        ) == _policy_dependency_business_state(session, PROPOSED_POLICY_CHANGE_ID)

    client.app.dependency_overrides[extraction_model_dependency] = lambda: (
        configured_fixture_model()
    )
    baseline = client.post(
        "/api/v1/policy-analysis-runs",
        json={"policy_change_id": POLICY_CHANGE_ID},
    )
    assert baseline.status_code == 201
    with SessionLocal() as session:
        after_baseline = _shared_enterprise_catalog_state(session)

    client.app.dependency_overrides[extraction_model_dependency] = lambda: configured_fixture_model(
        accepted_model_response(proposed_revision_payload())
    )
    proposed = client.post(
        "/api/v1/policy-analysis-runs",
        json={"policy_change_id": PROPOSED_POLICY_CHANGE_ID},
    )
    assert proposed.status_code == 201
    with SessionLocal() as session:
        after_proposed = _shared_enterprise_catalog_state(session)
        assert _policy_dependency_business_state(
            session, POLICY_CHANGE_ID
        ) == _policy_dependency_business_state(session, PROPOSED_POLICY_CHANGE_ID)

    assert initial_catalog == after_baseline == after_proposed


def _create_comparison(client):
    return client.post(
        "/api/v1/policy-comparisons",
        headers=ACTOR_HEADERS,
        json={
            "baseline_policy_change_id": POLICY_CHANGE_ID,
            "proposed_policy_change_id": PROPOSED_POLICY_CHANGE_ID,
        },
    )


def test_create_retrieve_and_idempotently_reuse_policy_comparison(client) -> None:
    baseline_run, proposed_run = _complete_both_policy_analyses(client)

    created = _create_comparison(client)
    repeated = _create_comparison(client)
    retrieved = client.get(created.headers["Location"])

    assert created.status_code == 201
    assert repeated.status_code == 200
    assert retrieved.status_code == 200
    assert repeated.json() == retrieved.json() == created.json()
    body = created.json()
    assert (
        body["baseline"]["accepted_extraction_attempt_id"]
        == baseline_run["latest_extraction_attempt_id"]
    )
    assert (
        body["proposed"]["accepted_extraction_attempt_id"]
        == proposed_run["latest_extraction_attempt_id"]
    )
    assert body["difference_count"] == 3
    assert [
        (item["sequence"], item["reason_code"], item["change_type"]) for item in body["differences"]
    ] == [
        (1, "POLICY_EFFECTIVE_DATE_MODIFIED", "modified"),
        (2, "WORKER_TYPE_REMOVED", "removed"),
        (3, "EXCLUDED_DESTINATION_ADDED", "added"),
    ]
    assert body["differences"][0]["baseline_provenance"]["quote"] == ("Effective September 1, 2026")
    assert body["differences"][0]["proposed_provenance"]["quote"] == ("Effective October 1, 2026")
    assert body["differences"][1]["proposed_provenance"] is None
    assert body["differences"][2]["baseline_provenance"] is None
    assert all(item["material"] is True for item in body["differences"])
    impact_delta = body["impact_delta"]
    assert impact_delta["summary"] == {
        "workers_became_affected": 0,
        "workers_no_longer_affected": 3,
        "workers_remained_affected": 0,
        "findings_introduced": 0,
        "findings_disappeared": 6,
        "enterprise_impacts_introduced": 0,
        "enterprise_impacts_removed": 14,
    }
    assert [item["baseline"]["display_name"] for item in impact_delta["worker_deltas"]] == [
        "David Miller",
        "Marcus Lee",
        "Sarah Johnson",
    ]
    assert all(
        item["change_type"] == "no_longer_affected" for item in impact_delta["worker_deltas"]
    )
    assert all(item["baseline"]["evidence"] for item in impact_delta["worker_deltas"])
    assert all(item["change_type"] == "disappeared" for item in impact_delta["finding_deltas"])
    assert all(
        item["change_type"] == "removed" for item in impact_delta["enterprise_impact_deltas"]
    )
    assert all(
        item["baseline"]["evidence"] and item["baseline"]["relationship_path"]
        for item in impact_delta["enterprise_impact_deltas"]
    )
    retained_source_keys = {
        "document-international-travel-policy",
        "kb-international-travel-booking",
        "document-manager-travel-approval-guide",
        "international-travel-security",
    }
    assert retained_source_keys.isdisjoint(
        {item["baseline"]["source_key"] for item in impact_delta["enterprise_impact_deltas"]}
    )
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(PolicyComparison)) == 1
        assert session.scalar(select(func.count()).select_from(PolicyComparisonDifference)) == 3
        assert session.scalar(select(func.count()).select_from(PolicyComparisonImpactDelta)) == 1
        assert (
            session.scalar(select(func.count()).select_from(PolicyComparisonImpactDeltaItem)) == 23
        )


def test_impact_delta_failure_rolls_back_the_complete_comparison(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _complete_both_policy_analyses(client)

    def fail_delta(*args, **kwargs):
        raise EnterpriseImpactDeltaIntegrityError("simulated delta failure")

    monkeypatch.setattr(
        policy_comparison_service,
        "create_policy_comparison_impact_delta",
        fail_delta,
    )

    response = _create_comparison(client)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == (
        "policy_comparison_impact_delta_lineage_inconsistent"
    )
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(PolicyComparison)) == 0
        assert session.scalar(select(func.count()).select_from(PolicyComparisonImpactDelta)) == 0


@pytest.mark.parametrize(
    ("payload", "expected_status", "expected_code"),
    [
        (
            {
                "baseline_policy_change_id": POLICY_CHANGE_ID,
                "proposed_policy_change_id": POLICY_CHANGE_ID,
            },
            422,
            "policy_comparison_same_policy",
        ),
        (
            {
                "baseline_policy_change_id": "missing",
                "proposed_policy_change_id": PROPOSED_POLICY_CHANGE_ID,
            },
            404,
            "baseline_policy_not_found",
        ),
        (
            {
                "baseline_policy_change_id": POLICY_CHANGE_ID,
                "proposed_policy_change_id": PROPOSED_POLICY_CHANGE_ID,
            },
            409,
            "baseline_policy_not_ready",
        ),
    ],
)
def test_comparison_creation_fails_closed_with_stable_errors(
    client,
    payload: dict,
    expected_status: int,
    expected_code: str,
) -> None:
    response = client.post(
        "/api/v1/policy-comparisons",
        headers=ACTOR_HEADERS,
        json=payload,
    )

    assert response.status_code == expected_status
    assert response.json()["detail"]["code"] == expected_code
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(PolicyComparison)) == 0


def test_proposed_policy_not_ready_is_distinct_from_baseline_not_ready(client) -> None:
    client.app.dependency_overrides[extraction_model_dependency] = lambda: (
        configured_fixture_model()
    )
    client.post(
        "/api/v1/policy-analysis-runs",
        json={"policy_change_id": POLICY_CHANGE_ID},
    )

    response = _create_comparison(client)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "proposed_policy_not_ready"


def test_cross_organization_comparison_is_rejected(client) -> None:
    _complete_both_policy_analyses(client)
    with SessionLocal.begin() as session:
        session.add(
            Organization(
                id="org-other",
                name="Other Organization",
                industry="Testing",
                headquarters=None,
            )
        )
        session.get(PolicyChange, PROPOSED_POLICY_CHANGE_ID).organization_id = "org-other"

    response = _create_comparison(client)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "policy_comparison_organization_mismatch"
    with SessionLocal.begin() as session:
        session.get(
            PolicyChange, PROPOSED_POLICY_CHANGE_ID
        ).organization_id = "org-acme-global-manufacturing"
        session.delete(session.get(Organization, "org-other"))


@pytest.mark.parametrize(
    ("accepted_rules_update", "expected_code"),
    [
        ({"kind": "domestic_expense"}, "policy_comparison_family_mismatch"),
        ({"schema_version": 2}, "policy_comparison_schema_mismatch"),
    ],
)
def test_incompatible_accepted_rule_contracts_are_rejected(
    client,
    accepted_rules_update: dict,
    expected_code: str,
) -> None:
    _, proposed_run = _complete_both_policy_analyses(client)
    with SessionLocal.begin() as session:
        run = session.get(PolicyAnalysisRun, proposed_run["id"])
        original = session.get(
            PolicyExtractionAttempt,
            proposed_run["latest_extraction_attempt_id"],
        )
        accepted_rules = deepcopy(original.accepted_rules)
        accepted_rules.update(accepted_rules_update)
        tampered = PolicyExtractionAttempt(
            policy_analysis_run_id=run.id,
            retry_reason="provider-free-contract-fixture",
            policy_change_id=PROPOSED_POLICY_CHANGE_ID,
            policy_text_snapshot=original.policy_text_snapshot,
            support_status="supported",
            validation_outcome="accepted",
            model_provider="fixture",
            model_identifier="incompatible-contract",
            prompt_version=original.prompt_version,
            schema_version=original.schema_version,
            raw_output=None,
            parsed_output=original.parsed_output,
            candidate_rules=original.candidate_rules,
            accepted_rules=accepted_rules,
            provenance=original.provenance,
            findings=[],
            validation_errors=[],
            created_at=datetime.now(UTC),
        )
        session.add(tampered)
        session.flush()
        run.latest_extraction_attempt_id = tampered.id

    response = _create_comparison(client)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == expected_code


def test_pending_clarification_blocks_comparison(client) -> None:
    _, proposed_run = _complete_both_policy_analyses(client)
    with SessionLocal.begin() as session:
        session.add(
            PolicyAnalysisClarification(
                policy_analysis_run_id=uuid.UUID(proposed_run["id"]),
                question_code="comparison-fixture-pending",
                question_text="Resolve the proposed policy exception.",
                expected_answer_contract={"type": "literal", "allowed_values": [True]},
                affected_fields=[
                    "candidate_rules.manager_approval.booking_before_effective_date_is_exempt"
                ],
                status="pending",
                answer=None,
                responder_identity=None,
                answer_provenance=None,
                created_at=datetime.now(UTC),
                answered_at=None,
            )
        )

    response = _create_comparison(client)
    entry = client.get("/api/v1/policy-analysis-entry")

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "proposed_policy_not_ready",
        "message": "The proposed policy has a pending clarification.",
    }
    assert entry.status_code == 200
    proposed = next(
        policy for policy in entry.json()["policies"] if policy["id"] == PROPOSED_POLICY_CHANGE_ID
    )
    assert proposed["comparison_readiness"] == {
        "ready": False,
        "status": "policy_not_ready",
        "accepted_extraction_attempt_id": None,
    }


def test_cross_owned_extraction_attempt_is_rejected(client) -> None:
    baseline_run, proposed_run = _complete_both_policy_analyses(client)
    with SessionLocal.begin() as session:
        proposed = session.get(PolicyAnalysisRun, proposed_run["id"])
        proposed.latest_extraction_attempt_id = uuid.UUID(
            baseline_run["latest_extraction_attempt_id"]
        )

    response = _create_comparison(client)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "policy_comparison_lineage_inconsistent"


def test_request_cannot_inject_authoritative_comparison_values(client) -> None:
    response = client.post(
        "/api/v1/policy-comparisons",
        headers=ACTOR_HEADERS,
        json={
            "baseline_policy_change_id": POLICY_CHANGE_ID,
            "proposed_policy_change_id": PROPOSED_POLICY_CHANGE_ID,
            "differences": [],
            "impact_delta": {"worker_deltas": []},
            "comparison_fingerprint": "attacker-controlled",
        },
    )

    assert response.status_code == 422


def test_missing_creator_and_missing_comparison_have_stable_behavior(client) -> None:
    missing_creator = client.post(
        "/api/v1/policy-comparisons",
        json={
            "baseline_policy_change_id": POLICY_CHANGE_ID,
            "proposed_policy_change_id": PROPOSED_POLICY_CHANGE_ID,
        },
    )
    missing = client.get(f"/api/v1/policy-comparisons/{uuid.uuid4()}")

    assert missing_creator.status_code == 422
    assert missing_creator.json()["detail"]["code"] == "policy_comparison_creator_required"
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "policy_comparison_not_found"


def test_comparison_is_historical_and_database_immutable(client) -> None:
    _complete_both_policy_analyses(client)
    comparison_id = _create_comparison(client).json()["id"]
    before = client.get(f"/api/v1/policy-comparisons/{comparison_id}").json()

    with SessionLocal.begin() as session:
        session.execute(
            text(
                "UPDATE policy_changes SET title = 'Later title', "
                "effective_date = DATE '2027-01-01', "
                "structured_rules = jsonb_build_object('later', true) "
                "WHERE id = :policy_id"
            ),
            {"policy_id": PROPOSED_POLICY_CHANGE_ID},
        )
    after = client.get(f"/api/v1/policy-comparisons/{comparison_id}").json()

    assert after["differences"] == before["differences"]
    assert after["comparison_fingerprint"] == before["comparison_fingerprint"]
    assert after["proposed"] == before["proposed"]
    assert after["impact_delta"] == before["impact_delta"]

    with SessionLocal() as session:
        with pytest.raises(DatabaseError, match="policy comparisons are immutable"):
            session.execute(
                text(
                    "UPDATE policy_comparisons SET created_by = 'mutated' WHERE id = :comparison_id"
                ),
                {"comparison_id": comparison_id},
            )
            session.commit()
        session.rollback()
        impact_delta_id = session.scalar(
            select(PolicyComparisonImpactDelta.id).where(
                PolicyComparisonImpactDelta.policy_comparison_id == comparison_id
            )
        )
        with pytest.raises(
            DatabaseError,
            match="policy comparison impact deltas are immutable",
        ):
            session.execute(
                text(
                    "UPDATE policy_comparison_impact_deltas SET created_by = 'mutated' "
                    "WHERE id = :impact_delta_id"
                ),
                {"impact_delta_id": impact_delta_id},
            )
            session.commit()
        session.rollback()
        impact_delta_item_id = session.scalar(
            select(PolicyComparisonImpactDeltaItem.id).where(
                PolicyComparisonImpactDeltaItem.impact_delta_id == impact_delta_id
            )
        )
        with pytest.raises(
            DatabaseError,
            match="policy comparison impact deltas are immutable",
        ):
            session.execute(
                text(
                    "DELETE FROM policy_comparison_impact_delta_items "
                    "WHERE id = :impact_delta_item_id"
                ),
                {"impact_delta_item_id": impact_delta_item_id},
            )
            session.commit()
        session.rollback()
        difference_id = session.scalar(
            select(PolicyComparisonDifference.id).where(
                PolicyComparisonDifference.policy_comparison_id == comparison_id
            )
        )
        with pytest.raises(DatabaseError, match="policy comparisons are immutable"):
            session.execute(
                text("DELETE FROM policy_comparison_differences WHERE id = :difference_id"),
                {"difference_id": difference_id},
            )
            session.commit()
        session.rollback()


def test_demo_reset_removes_comparisons_and_preserves_both_sources(client) -> None:
    _complete_both_policy_analyses(client)
    _create_comparison(client)

    with SessionLocal() as session:
        summary = reset_demo_workflows(session)

    assert summary.policy_comparisons == 1
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(PolicyComparisonImpactDelta)) == 1
        source_ids = set(session.scalars(select(text("id")).select_from(text("policy_changes"))))
    assert {POLICY_CHANGE_ID, PROPOSED_POLICY_CHANGE_ID} <= source_ids
