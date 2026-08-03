import uuid
from copy import deepcopy
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from changeops.api.policy_extractions import extraction_model_dependency
from changeops.api.policy_interpretation import interpretation_model_dependency
from changeops.db.models import (
    AssessmentEnterpriseImpact,
    ImpactAssessment,
    PolicyAnalysisRun,
    PolicyChange,
)
from changeops.db.session import SessionLocal
from changeops.services.policy_analysis_journey_service import (
    PolicyAnalysisJourneyIntegrityError,
    _resolve_change_plan_references,
)
from changeops.services.seed_service import (
    POLICY_CHANGE_ID,
    POLICY_TEXT,
    PROPOSED_POLICY_CHANGE_ID,
)
from tests.integration.test_execution_commands_api import ADMIN_HEADERS, _complete_run
from tests.integration.test_policy_extraction_api import configured_fixture_model
from tests.integration.test_policy_interpretation_api import configured_interpreter
from tests.policy_extraction_fixtures import accepted_model_response, canonical_proposal_payload


def test_entry_returns_seeded_policy_and_recent_analysis(client) -> None:
    client.app.dependency_overrides[extraction_model_dependency] = lambda: (
        configured_fixture_model()
    )
    created = client.post(
        "/api/v1/policy-analysis-runs", json={"policy_change_id": POLICY_CHANGE_ID}
    )

    response = client.get("/api/v1/policy-analysis-entry")

    assert response.status_code == 200
    body = response.json()
    policy = next(item for item in body["policies"] if item["id"] == POLICY_CHANGE_ID)
    proposed = next(item for item in body["policies"] if item["id"] == PROPOSED_POLICY_CHANGE_ID)
    assert policy["policy_text"] == POLICY_TEXT
    assert policy["organization_name"] == "Acme Global Manufacturing"
    assert policy["comparison_readiness"]["ready"] is True
    assert proposed["comparison_readiness"] == {
        "ready": False,
        "status": "policy_not_ready",
        "accepted_extraction_attempt_id": None,
    }
    assert body["recent_comparisons"] == []
    assert body["recent_runs"][0]["id"] == created.json()["id"]


def test_completed_journey_preserves_lineage_and_omits_legacy_questions(client) -> None:
    client.app.dependency_overrides[extraction_model_dependency] = lambda: (
        configured_fixture_model()
    )
    created = client.post(
        "/api/v1/policy-analysis-runs", json={"policy_change_id": POLICY_CHANGE_ID}
    ).json()

    before = _domain_counts()
    response = client.get(f"/api/v1/policy-analysis-runs/{created['id']}/journey")
    after = _domain_counts()

    assert response.status_code == 200
    body = response.json()
    assert body["policy"]["id"] == POLICY_CHANGE_ID
    assert body["run"]["id"] == created["id"]
    assert body["extraction"]["id"] == created["latest_extraction_attempt_id"]
    assert body["extraction"]["validation_outcome"] == "accepted"
    assert body["extraction"]["provenance"]
    assert "raw_output" not in body["extraction"]
    assert body["uncertainty"] == {
        "extraction_findings": [],
        "clarifications": [],
        "legacy_assessment_questions": "omitted_schema_v1_fixture",
    }
    assert body["assessment"]["id"] == created["assessment_id"]
    assert "unresolved_questions" not in body["assessment"]
    assert body["interpretation"]["status"] == "not_created"
    assert body["interpretation"]["resolved_references"] == []
    assert body["approval_run"] is None
    assert body["execution"] == {
        "status": "unavailable",
        "command_count": 0,
        "executed_command_count": 0,
        "result_count": 0,
        "replay_count": 0,
    }
    assert before == after


def test_journey_returns_the_policy_text_snapshot_analyzed_by_the_run(client) -> None:
    client.app.dependency_overrides[extraction_model_dependency] = lambda: (
        configured_fixture_model()
    )
    run = client.post(
        "/api/v1/policy-analysis-runs", json={"policy_change_id": POLICY_CHANGE_ID}
    ).json()
    with SessionLocal.begin() as session:
        session.get(PolicyChange, POLICY_CHANGE_ID).policy_text = "Later source text."

    body = client.get(f"/api/v1/policy-analysis-runs/{run['id']}/journey").json()

    assert body["policy"]["policy_text"] == POLICY_TEXT


def test_journey_derives_affected_and_cleared_enterprise_coverage(client) -> None:
    client.app.dependency_overrides[extraction_model_dependency] = lambda: (
        configured_fixture_model()
    )
    run = client.post(
        "/api/v1/policy-analysis-runs", json={"policy_change_id": POLICY_CHANGE_ID}
    ).json()

    body = client.get(f"/api/v1/policy-analysis-runs/{run['id']}/journey").json()
    coverage = {item["domain"]: item for item in body["enterprise_coverage"]}

    assert (coverage["systems"]["considered"], coverage["systems"]["affected"]) == (3, 2)
    assert (coverage["documents"]["considered"], coverage["documents"]["affected"]) == (4, 3)
    assert (coverage["teams"]["considered"], coverage["teams"]["affected"]) == (4, 3)
    assert (
        coverage["customer_commitments"]["considered"],
        coverage["customer_commitments"]["affected"],
    ) == (2, 1)
    assert any(
        item["id"] == "system-expense-management" and item["classification"] == "cleared"
        for item in coverage["systems"]["objects"]
    )
    with SessionLocal() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(AssessmentEnterpriseImpact)
                .where(AssessmentEnterpriseImpact.assessment_id == run["assessment_id"])
            )
            == 18
        )


def test_pending_clarification_uses_authoritative_record_without_assessment(client) -> None:
    payload = deepcopy(canonical_proposal_payload())
    payload["candidate_rules"]["manager_approval"]["booking_before_effective_date_is_exempt"] = (
        False
    )
    client.app.dependency_overrides[extraction_model_dependency] = lambda: configured_fixture_model(
        accepted_model_response(payload)
    )
    run = client.post(
        "/api/v1/policy-analysis-runs", json={"policy_change_id": POLICY_CHANGE_ID}
    ).json()

    response = client.get(f"/api/v1/policy-analysis-runs/{run['id']}/journey")

    assert response.status_code == 200
    body = response.json()
    assert body["run"]["status"] == "awaiting_clarification"
    assert body["assessment"] is None
    assert body["enterprise_coverage"] == []
    assert body["uncertainty"]["clarifications"][0]["status"] == "pending"
    assert body["uncertainty"]["extraction_findings"] == []
    assert body["uncertainty"]["clarifications"][0]["affected_fields"] == [
        "candidate_rules.manager_approval.booking_before_effective_date_is_exempt"
    ]
    assert body["interpretation"]["status"] == "not_available"


def test_unsupported_and_failed_runs_remain_inspectable(client) -> None:
    unsupported = deepcopy(canonical_proposal_payload())
    unsupported["policy_family"] = "domestic_expense"
    unsupported["support_status"] = "unsupported"
    unsupported["candidate_rules"] = None
    unsupported["provenance"] = [
        item for item in unsupported["provenance"] if item["field_path"] == "policy_family"
    ]
    client.app.dependency_overrides[extraction_model_dependency] = lambda: configured_fixture_model(
        accepted_model_response(unsupported)
    )
    unsupported_run = client.post(
        "/api/v1/policy-analysis-runs", json={"policy_change_id": POLICY_CHANGE_ID}
    ).json()

    unsupported_journey = client.get(
        f"/api/v1/policy-analysis-runs/{unsupported_run['id']}/journey"
    ).json()

    assert unsupported_journey["run"]["status"] == "unsupported"
    assert unsupported_journey["extraction"]["validation_outcome"] == "unsupported"
    assert unsupported_journey["assessment"] is None

    malformed = {
        "raw": {"content": "{bad-json"},
        "parsed": None,
        "parsing_error": ValueError("invalid JSON"),
    }
    client.app.dependency_overrides[extraction_model_dependency] = lambda: configured_fixture_model(
        malformed
    )
    failed_run = client.post(
        "/api/v1/policy-analysis-runs", json={"policy_change_id": POLICY_CHANGE_ID}
    ).json()

    failed_journey = client.get(f"/api/v1/policy-analysis-runs/{failed_run['id']}/journey").json()

    assert failed_journey["run"]["status"] == "failed"
    assert failed_journey["run"]["failure_code"] == "retry_limit_exhausted"
    assert failed_journey["assessment"] is None


def test_journey_resolves_change_plan_and_approval_from_same_lineage(client) -> None:
    client.app.dependency_overrides[extraction_model_dependency] = lambda: (
        configured_fixture_model()
    )
    run = client.post(
        "/api/v1/policy-analysis-runs", json={"policy_change_id": POLICY_CHANGE_ID}
    ).json()
    client.app.dependency_overrides[interpretation_model_dependency] = lambda: (
        lambda: configured_interpreter()
    )
    plan = client.post(f"/api/v1/impact-assessments/{run['assessment_id']}/change-plans").json()
    approval = client.post(f"/api/v1/impact-assessments/{run['assessment_id']}/approval-run").json()

    body = client.get(f"/api/v1/policy-analysis-runs/{run['id']}/journey").json()

    assert body["interpretation"]["status"] == "available"
    assert body["interpretation"]["change_plan"]["id"] == plan["id"]
    assert body["interpretation"]["change_plan"]["policy_analysis_run_id"] == run["id"]
    assert body["interpretation"]["change_plan"]["impact_assessment_id"] == run["assessment_id"]
    span = body["interpretation"]["resolved_references"][0]["policy_spans"][0]
    assert span["quote"] == "U.S.-based"
    assert span["validated_against_policy_snapshot"] is True
    assert body["approval_run"] == {"id": approval["id"], "status": approval["status"]}


def test_journey_enriches_impact_and_owned_evidence_without_changing_plan(client) -> None:
    client.app.dependency_overrides[extraction_model_dependency] = lambda: (
        configured_fixture_model()
    )
    run = client.post(
        "/api/v1/policy-analysis-runs", json={"policy_change_id": POLICY_CHANGE_ID}
    ).json()
    with SessionLocal() as session:
        assessment = session.get(ImpactAssessment, run["assessment_id"])
        impact = assessment.enterprise_impacts[0]
        evidence = impact.evidence[0]
        impact_id = impact.id
        evidence_key = evidence.evidence_key
        expected = {
            "display_name": impact.display_name,
            "domain": impact.domain,
            "classification": impact.classification,
            "reason_code": impact.reason_code,
            "label": evidence.label,
            "evidence_type": evidence.evidence_type,
            "source_type": evidence.source_type,
            "source_id": evidence.source_id,
        }
    proposal = configured_interpreter().model.candidate
    proposal["coverage_gaps"][0]["impact_ids"] = [str(impact_id)]
    proposal["coverage_gaps"][0]["evidence_keys"] = [evidence_key]
    client.app.dependency_overrides[interpretation_model_dependency] = lambda: (
        lambda: configured_interpreter(proposal)
    )
    client.post(f"/api/v1/impact-assessments/{run['assessment_id']}/change-plans")

    body = client.get(f"/api/v1/policy-analysis-runs/{run['id']}/journey").json()
    references = body["interpretation"]["resolved_references"][0]

    assert references["impacts"] == [
        {
            "impact_id": str(impact_id),
            "display_name": expected["display_name"],
            "domain": expected["domain"],
            "classification": expected["classification"],
            "reason_code": expected["reason_code"],
        }
    ]
    assert references["evidence"] == [
        {
            "evidence_key": evidence_key,
            "label": expected["label"],
            "evidence_type": expected["evidence_type"],
            "source_type": expected["source_type"],
            "source_id": expected["source_id"],
        }
    ]


def test_journey_fails_closed_when_lineage_uses_another_assessment(client) -> None:
    client.app.dependency_overrides[extraction_model_dependency] = lambda: (
        configured_fixture_model()
    )
    run = client.post(
        "/api/v1/policy-analysis-runs", json={"policy_change_id": POLICY_CHANGE_ID}
    ).json()
    client.app.dependency_overrides[interpretation_model_dependency] = lambda: (
        lambda: configured_interpreter()
    )
    plan_body = client.post(
        f"/api/v1/impact-assessments/{run['assessment_id']}/change-plans"
    ).json()["change_plan"]
    plan_body["coverage_gaps"][0]["impact_references"] = [
        {
            "assessment_id": str(uuid.uuid4()),
            "impact_id": str(uuid.uuid4()),
        }
    ]
    with SessionLocal() as session:
        assessment = session.get(ImpactAssessment, run["assessment_id"])
        analysis_run = session.get(PolicyAnalysisRun, run["id"])
        with pytest.raises(PolicyAnalysisJourneyIntegrityError):
            _resolve_change_plan_references(
                analysis_run,
                assessment,
                SimpleNamespace(validated_plan=plan_body),
            )


def test_journey_execution_summary_distinguishes_eligibility_preparation_and_replay(client) -> None:
    _, approval = _complete_run(client, approve_training_only=True)
    journey_url = f"/api/v1/policy-analysis-runs/{approval['policy_analysis_run_id']}/journey"

    eligible = client.get(journey_url).json()
    assert eligible["approval_run"]["status"] == "completed"
    assert eligible["execution"]["status"] == "eligible"

    prepared = client.post(
        f"/api/v1/action-approval-runs/{approval['id']}/execution-commands",
        headers=ADMIN_HEADERS,
    ).json()
    assert client.get(journey_url).json()["execution"]["status"] == "command_prepared"

    command_id = prepared["commands"][0]["id"]
    client.post(
        f"/api/v1/execution-commands/{command_id}/execute",
        headers=ADMIN_HEADERS,
    )
    client.post(
        f"/api/v1/execution-commands/{command_id}/execute",
        headers=ADMIN_HEADERS,
    )
    executed = client.get(journey_url).json()["execution"]
    assert executed["status"] == "executed"
    assert executed["command_count"] == 2
    assert executed["executed_command_count"] == 1
    assert executed["result_count"] == 2
    assert executed["replay_count"] == 1


def test_missing_journey_returns_stable_error(client) -> None:
    response = client.get(
        "/api/v1/policy-analysis-runs/00000000-0000-0000-0000-000000000000/journey"
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "policy_analysis_journey_not_found"


def _domain_counts() -> tuple[int, int]:
    with SessionLocal() as session:
        return (
            session.scalar(select(func.count()).select_from(ImpactAssessment)),
            session.scalar(select(func.count()).select_from(AssessmentEnterpriseImpact)),
        )
