from sqlalchemy import func, select

from changeops.db.models import (
    ActionApprovalRun,
    AssessmentEnterpriseImpact,
    EnterpriseSystem,
    Evidence,
    ExecutionCommand,
    ExecutionResult,
    Finding,
    ImpactAssessment,
    Organization,
    PolicyAnalysisRun,
    PolicySystemDependency,
    ProposedAction,
)
from changeops.db.session import SessionLocal
from changeops.services.demo_reset_service import reset_demo_workflows
from changeops.services.seed_service import (
    ORGANIZATION_ID,
    POLICY_CHANGE_ID,
    RELATIONSHIP_PROVENANCE,
)

CATALOG_URL = f"/api/v1/catalog-objects?organization_id={ORGANIZATION_ID}"
MANAGER_GUIDE_URL = (
    "/api/v1/catalog-objects/enterprise_document/document-manager-travel-approval-guide"
)
MANAGER_RULE_URL = (
    f"/api/v1/policy-changes/{POLICY_CHANGE_ID}/rule-references/MANAGER_APPROVAL_REQUIRED"
)


def test_catalog_browse_returns_exact_primary_and_context_counts(client) -> None:
    response = client.get(CATALOG_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["organization"] == {
        "id": ORGANIZATION_ID,
        "name": "Acme Global Manufacturing",
    }
    assert body["catalog_context"] == {
        "kind": "seeded_demonstration",
        "label": "Seeded demonstration catalog",
        "record_level_origin": "not_recorded",
    }
    assert body["catalog_counts"] == {
        "enterprise_document": 4,
        "enterprise_system": 3,
        "training_course": 1,
    }
    assert body["assessment_context_counts"] == {
        "worker": 12,
        "team": 4,
        "customer_commitment": 2,
    }
    identities = [(item["object_type"], item["object_id"]) for item in body["objects"]]
    assert identities == sorted(
        identities,
        key=lambda item: (
            ("enterprise_document", "enterprise_system", "training_course").index(item[0]),
            item[1],
        ),
    )


def test_catalog_list_filters_only_the_closed_primary_categories(client) -> None:
    response = client.get(f"{CATALOG_URL}&object_type=enterprise_system")

    assert response.status_code == 200
    assert len(response.json()["objects"]) == 3
    assert {item["object_type"] for item in response.json()["objects"]} == {"enterprise_system"}

    unsupported = client.get(f"{CATALOG_URL}&object_type=worker")
    assert unsupported.status_code == 422
    assert unsupported.json()["detail"]["code"] == "unsupported_catalog_object_type"


def test_document_detail_preserves_flagship_metadata_and_policy_lineage(client) -> None:
    response = client.get(MANAGER_GUIDE_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["object"] == {
        "object_type": "enterprise_document",
        "object_id": "document-manager-travel-approval-guide",
        "organization_id": ORGANIZATION_ID,
        "display_name": "Manager Travel Approval Guide",
        "description": None,
        "owner": None,
        "source_system": "Acme Knowledge",
        "status": {"value": "published", "basis": "stored"},
        "metadata": {"document_type": "guide", "version": "2"},
        "relationship_count": 2,
        "record_provenance": {
            "classification": "not_recorded",
            "catalog_context": "seeded_demonstration",
        },
    }
    assert [item["relationship_id"] for item in body["relationships"]] == [
        "dependency-policy-manager-guide",
        "dependency-policy-manager-guide-proposed",
    ]
    baseline, proposed = body["relationships"]
    assert baseline["relationship_type"] == proposed["relationship_type"] == "instructs_manager"
    assert baseline["impact_classification"] == "review_required"
    assert baseline["explanation"] == ("The manager guide documents approval responsibilities.")
    assert baseline["source"]["stable_key"] == (f"{POLICY_CHANGE_ID}:MANAGER_APPROVAL_REQUIRED")
    assert proposed["source"]["stable_key"] == (
        "policy-international-travel-proposed-2026-10:MANAGER_APPROVAL_REQUIRED"
    )
    assert baseline["trust"] == {
        "level": "trusted",
        "state": "persisted_typed_relationship",
        "basis": "deterministic_enterprise_relationship",
        "integrity": [
            "policy_change_foreign_key",
            "enterprise_document_foreign_key",
            "semantic_uniqueness",
        ],
        "used_deterministically": True,
    }
    assert baseline["provenance"] == {
        "classification": "seeded_demonstration",
        "source_label": "Seeded demonstration data",
        "creator": None,
        "owning_authority": "ChangeOps demonstration seed",
        "reference": "changeops.seed.relationships.v1",
        "recorded_at": "2026-08-06T00:00:00Z",
        "approval": None,
        "ai_involvement": "none",
    }
    assert body["assessment_usage"]["changes_assessment_behavior"] is False
    assert "deterministic enterprise analyzer" in body["assessment_usage"]["statement"]


def test_system_and_training_details_normalize_status_without_inventing_metadata(client) -> None:
    system_detail = client.get(
        "/api/v1/catalog-objects/enterprise_system/system-travel-request"
    ).json()
    course_detail = client.get(
        "/api/v1/catalog-objects/training_course/international-travel-security"
    ).json()
    system = system_detail["object"]
    course = course_detail["object"]

    assert system["status"] == {"value": "active", "basis": "normalized"}
    assert system["description"] == "Collects travel requests and manager approvals."
    assert system["owner"] is None
    assert system["source_system"] is None
    assert system["metadata"] == {"system_type": "travel_workflow"}
    assert course["status"] == {"value": "active", "basis": "normalized"}
    assert course["description"] is None
    assert course["owner"] is None
    assert course["source_system"] is None
    assert course["metadata"] == {
        "course_code": "ITS-100",
        "completion_record_count": 6,
    }
    assert system["relationship_count"] == 2
    assert {
        relationship["provenance"]["classification"]
        for relationship in system_detail["relationships"] + course_detail["relationships"]
    } == {"seeded_demonstration"}
    assert {
        relationship["provenance"]["ai_involvement"]
        for relationship in system_detail["relationships"] + course_detail["relationships"]
    } == {"none"}
    assert course["relationship_count"] == 2


def test_policy_scoped_rule_reference_resolves_typed_dependency_rows(client) -> None:
    response = client.get(MANAGER_RULE_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["stable_key"] == f"{POLICY_CHANGE_ID}:MANAGER_APPROVAL_REQUIRED"
    assert body["structured_rule_reference"] == {
        "field_path": "manager_approval",
        "label": "Manager approval rule",
        "mapping_status": "supported",
    }
    assert [item["relationship_id"] for item in body["relationships"]] == [
        "dependency-policy-booking-article",
        "dependency-policy-manager-guide",
        "dependency-policy-travel-request",
    ]
    assert body["authority_boundary"] == {
        "is_standalone_persisted_rule": False,
        "relationship_source": "persisted_dependency_rows",
        "assessment_use": "deterministic",
    }


def test_unknown_persisted_rule_code_stays_visible_without_guessing(client) -> None:
    with SessionLocal.begin() as session:
        session.add(
            PolicySystemDependency(
                id="dependency-policy-unknown-code",
                policy_change_id=POLICY_CHANGE_ID,
                rule_code="FUTURE_RULE_CODE",
                system_id="system-expense-management",
                relationship_type="future_mapping",
                explanation="A controlled fixture for an unknown mapping.",
                **RELATIONSHIP_PROVENANCE,
            )
        )

    try:
        response = client.get(
            f"/api/v1/policy-changes/{POLICY_CHANGE_ID}/rule-references/FUTURE_RULE_CODE"
        )

        assert response.status_code == 200
        assert response.json()["structured_rule_reference"] == {
            "field_path": None,
            "label": None,
            "mapping_status": "unknown",
        }
        assert response.json()["relationships"][0]["relationship_id"] == (
            "dependency-policy-unknown-code"
        )
    finally:
        with SessionLocal.begin() as session:
            fixture = session.get(PolicySystemDependency, "dependency-policy-unknown-code")
            if fixture is not None:
                session.delete(fixture)


def test_catalog_errors_are_stable_and_detail_routing_reuses_source_identity(client) -> None:
    missing_org = client.get("/api/v1/catalog-objects?organization_id=missing-organization")
    unsupported = client.get("/api/v1/catalog-objects/worker/worker-sarah-johnson")
    missing = client.get("/api/v1/catalog-objects/enterprise_document/missing-document")
    cross_org = client.get(f"{MANAGER_GUIDE_URL}?organization_id=missing-organization")
    missing_policy = client.get(
        "/api/v1/policy-changes/missing-policy/rule-references/MANAGER_APPROVAL_REQUIRED"
    )
    missing_rule = client.get(
        f"/api/v1/policy-changes/{POLICY_CHANGE_ID}/rule-references/MISSING_RULE"
    )

    assert (missing_org.status_code, missing_org.json()["detail"]["code"]) == (
        404,
        "organization_not_found",
    )
    assert (unsupported.status_code, unsupported.json()["detail"]["code"]) == (
        422,
        "unsupported_catalog_object_type",
    )
    assert (missing.status_code, missing.json()["detail"]["code"]) == (
        404,
        "catalog_object_not_found",
    )
    assert cross_org.status_code == 404
    assert missing_policy.json()["detail"]["code"] == "policy_change_not_found"
    assert missing_rule.json()["detail"]["code"] == "policy_rule_reference_not_found"


def test_catalog_fails_closed_on_cross_organization_relationship_endpoint(client) -> None:
    with SessionLocal.begin() as session:
        session.add(
            Organization(
                id="org-controlled-integrity-fixture",
                name="Controlled integrity fixture",
                industry=None,
                headquarters=None,
            )
        )
        session.flush()
        session.add(
            EnterpriseSystem(
                id="system-controlled-integrity-fixture",
                organization_id="org-controlled-integrity-fixture",
                name="Controlled integrity fixture",
                system_type="fixture",
                description="Exists only to verify fail-closed organization resolution.",
                active=True,
            )
        )
        session.flush()
        session.add(
            PolicySystemDependency(
                id="dependency-controlled-integrity-fixture",
                policy_change_id=POLICY_CHANGE_ID,
                rule_code="MANAGER_APPROVAL_REQUIRED",
                system_id="system-controlled-integrity-fixture",
                relationship_type="fixture_relationship",
                explanation="Exists only to verify fail-closed organization resolution.",
                **RELATIONSHIP_PROVENANCE,
            )
        )

    try:
        response = client.get(
            "/api/v1/catalog-objects/enterprise_system/system-controlled-integrity-fixture"
        )
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "catalog_projection_inconsistent"
    finally:
        with SessionLocal.begin() as session:
            dependency = session.get(
                PolicySystemDependency, "dependency-controlled-integrity-fixture"
            )
            system = session.get(EnterpriseSystem, "system-controlled-integrity-fixture")
            organization = session.get(Organization, "org-controlled-integrity-fixture")
            if dependency is not None:
                session.delete(dependency)
                session.flush()
            if system is not None:
                session.delete(system)
                session.flush()
            if organization is not None:
                session.delete(organization)


def test_catalog_gets_create_no_assessment_or_workflow_artifacts(client) -> None:
    before = _artifact_counts()

    client.get(CATALOG_URL)
    client.get(MANAGER_GUIDE_URL)
    client.get(MANAGER_RULE_URL)

    assert _artifact_counts() == before


def test_demo_reset_preserves_the_same_catalog_projection(client) -> None:
    before = client.get(CATALOG_URL).json()
    before_detail = client.get(MANAGER_GUIDE_URL).json()

    with SessionLocal.begin() as session:
        reset_demo_workflows(session)

    assert client.get(CATALOG_URL).json() == before
    assert client.get(MANAGER_GUIDE_URL).json() == before_detail


def test_only_get_catalog_routes_are_registered(client) -> None:
    assert client.post("/api/v1/catalog-objects", json={}).status_code == 405
    assert client.put(MANAGER_GUIDE_URL, json={}).status_code == 405
    assert client.delete(MANAGER_RULE_URL).status_code == 405
    assert (
        client.post(
            "/api/v1/catalog-objects/enterprise_document/missing/confluence-refresh"
        ).status_code
        == 404
    )


def _artifact_counts() -> dict[str, int]:
    models = (
        PolicyAnalysisRun,
        ImpactAssessment,
        Finding,
        Evidence,
        AssessmentEnterpriseImpact,
        ProposedAction,
        ActionApprovalRun,
        ExecutionCommand,
        ExecutionResult,
    )
    with SessionLocal() as session:
        return {
            model.__tablename__: session.scalar(select(func.count()).select_from(model)) or 0
            for model in models
        }
