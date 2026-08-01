import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from changeops.evaluation.live_smoke import (
    SmokeFailure,
    SmokeSummary,
    _assert_assessment_invariants,
    _safe_http_failure_code,
)


def _valid_assessment() -> dict:
    return {
        "summary": {
            "affected_workers": 3,
            "unaffected_workers": 3,
            "enterprise_impacts": 18,
        },
        "findings": [{}] * 6,
        "enterprise_impacts": {
            "people": [{}] * 6,
            "teams": [{}] * 2,
            "systems": [{}] * 2,
            "documents": [{}] * 3,
            "training": [{}] * 4,
            "customer_commitments": [{}],
        },
        "proposed_actions": [{"execution_status": "not_executed"}] * 13,
        "unresolved_questions": [{}] * 8,
    }


def test_live_smoke_accepts_canonical_assessment_invariants() -> None:
    _assert_assessment_invariants(_valid_assessment())


def test_live_smoke_reports_stable_assessment_failure_code() -> None:
    assessment = _valid_assessment()
    assessment["summary"]["enterprise_impacts"] = 17

    with pytest.raises(SmokeFailure, match="assessment_impact_count_regressed"):
        _assert_assessment_invariants(assessment)


def test_http_error_uses_only_stable_api_code() -> None:
    response = BytesIO(
        json.dumps(
            {
                "detail": {
                    "code": "interpretation_grounding_invalid",
                    "message": "uncontrolled provider detail",
                }
            }
        ).encode()
    )
    error = HTTPError("https://example.invalid", 422, "error", {}, response)

    assert _safe_http_failure_code(error) == "interpretation_grounding_invalid"


def test_http_error_rejects_uncontrolled_failure_code() -> None:
    response = BytesIO(
        json.dumps({"detail": {"code": "uncontrolled provider detail\nsecret"}}).encode()
    )
    error = HTTPError("https://example.invalid", 502, "error", {}, response)

    assert _safe_http_failure_code(error) == "api_http_502"


def test_live_smoke_summary_contains_no_provider_secret() -> None:
    summary = SmokeSummary(
        provider="openai",
        extraction_model="extract-model",
        interpretation_model="interpret-model",
    )

    assert set(summary.as_dict()) == {
        "provider",
        "extraction_model",
        "interpretation_model",
        "elapsed_seconds",
        "run_id",
        "assessment_id",
        "interpretation_attempt_id",
        "change_plan_id",
        "terminal_outcome",
        "failure_code",
    }
