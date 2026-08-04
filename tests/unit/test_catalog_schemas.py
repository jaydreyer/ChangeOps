from copy import deepcopy

import pytest
from pydantic import ValidationError

from changeops.schemas.catalog import CatalogObjectDetailResponse


def catalog_detail_payload() -> dict:
    return {
        "object": {
            "object_type": "enterprise_document",
            "object_id": "document-guide",
            "organization_id": "org-acme",
            "display_name": "Manager guide",
            "description": None,
            "owner": None,
            "source_system": "Acme Knowledge",
            "status": {"value": "published", "basis": "stored"},
            "metadata": {"document_type": "guide", "version": "2"},
            "relationship_count": 1,
            "record_provenance": {
                "classification": "not_recorded",
                "catalog_context": "seeded_demonstration",
            },
        },
        "relationships": [
            {
                "relationship_id": "dependency-guide",
                "relationship_source_type": "policy_document_dependency",
                "relationship_type": "instructs_manager",
                "explanation": "The guide documents approval responsibilities.",
                "impact_classification": "review_required",
                "policy": {
                    "id": "policy-travel",
                    "title": "Travel policy",
                    "version": "1",
                },
                "source": {
                    "object_type": "policy_rule_reference",
                    "stable_key": "policy-travel:MANAGER_APPROVAL_REQUIRED",
                    "display_name": "MANAGER_APPROVAL_REQUIRED",
                    "href": "/api/v1/policy-changes/policy-travel/rule-references/"
                    "MANAGER_APPROVAL_REQUIRED",
                },
                "target": {
                    "object_type": "enterprise_document",
                    "stable_key": "document-guide",
                    "display_name": "Manager guide",
                    "href": "/catalog/enterprise_document/document-guide",
                },
                "trust": {
                    "state": "persisted_typed_relationship",
                    "integrity": [
                        "policy_change_foreign_key",
                        "enterprise_document_foreign_key",
                        "semantic_uniqueness",
                    ],
                    "used_deterministically": True,
                },
                "provenance": {
                    "classification": "not_recorded",
                    "creator": None,
                    "owning_authority": None,
                    "recorded_at": None,
                    "approval": None,
                },
            }
        ],
        "assessment_usage": {
            "statement": "Used deterministically.",
            "changes_assessment_behavior": False,
        },
    }


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("object", "object_type"), "worker"),
        (("object", "record_provenance", "classification"), "seeded"),
        (("relationships", 0, "trust", "state"), "human_approved"),
        (("relationships", 0, "provenance", "classification"), "human_curated"),
    ],
)
def test_catalog_contract_rejects_unsupported_authority_claims(path, value) -> None:
    payload = deepcopy(catalog_detail_payload())
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    with pytest.raises(ValidationError):
        CatalogObjectDetailResponse.model_validate(payload)


def test_catalog_contract_rejects_extra_fields() -> None:
    payload = catalog_detail_payload()
    payload["object"]["owner_basis"] = "inferred"

    with pytest.raises(ValidationError):
        CatalogObjectDetailResponse.model_validate(payload)
