import uuid

import pytest
from pydantic import ValidationError

from changeops.schemas.assessments import EnterpriseImpactResponse


def impact_payload() -> dict:
    return {
        "id": uuid.uuid4(),
        "domain": "documents",
        "object_type": "enterprise_document",
        "source_key": "document-travel",
        "display_name": "Travel Guide",
        "classification": "update_required",
        "explanation": "The guide explains a changed process.",
        "reason_code": "DOCUMENT_REFERENCES_CHANGED_POLICY",
        "evidence_ids": [uuid.uuid4()],
        "relationship_path": [
            {
                "sequence": 0,
                "object_type": "policy_change",
                "stable_key": "policy-travel",
                "display_label": "Travel Policy",
                "relationship_to_next": "affects",
            },
            {
                "sequence": 1,
                "object_type": "enterprise_document",
                "stable_key": "document-travel",
                "display_label": "Travel Guide",
                "relationship_to_next": None,
            },
        ],
        "proposed_action_ids": [],
        "sort_key": "04:enterprise_document:document-travel",
    }


def test_enterprise_impact_rejects_unknown_domain() -> None:
    payload = impact_payload()
    payload["domain"] = "unknown"

    with pytest.raises(ValidationError):
        EnterpriseImpactResponse.model_validate(payload)


def test_enterprise_impact_rejects_invalid_domain_classification_pair() -> None:
    payload = impact_payload()
    payload["classification"] = "directly_affected"

    with pytest.raises(ValidationError):
        EnterpriseImpactResponse.model_validate(payload)


def test_enterprise_impact_requires_evidence_and_relationship_path() -> None:
    payload = impact_payload()
    payload["evidence_ids"] = []
    payload["relationship_path"] = []

    with pytest.raises(ValidationError):
        EnterpriseImpactResponse.model_validate(payload)
