"""Manually invoked, sanitized end-to-end smoke test for configured live AI providers."""

import argparse
import json
import os
import re
import sys
import time
import uuid
from contextlib import suppress
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

POLICY_CHANGE_ID = "policy-international-travel-2026-09"


class SmokeFailure(Exception):
    """A live-smoke failure safe to report by stable code only."""

    def __init__(self, code: str, *, interpretation_attempt_id: str | None = None) -> None:
        self.code = code
        self.interpretation_attempt_id = interpretation_attempt_id
        super().__init__(code)


@dataclass
class SmokeSummary:
    provider: str
    extraction_model: str
    interpretation_model: str
    elapsed_seconds: float = 0.0
    run_id: str | None = None
    assessment_id: str | None = None
    interpretation_attempt_id: str | None = None
    change_plan_id: str | None = None
    terminal_outcome: str = "not_started"
    failure_code: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "extraction_model": self.extraction_model,
            "interpretation_model": self.interpretation_model,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "run_id": self.run_id,
            "assessment_id": self.assessment_id,
            "interpretation_attempt_id": self.interpretation_attempt_id,
            "change_plan_id": self.change_plan_id,
            "terminal_outcome": self.terminal_outcome,
            "failure_code": self.failure_code,
        }


class ApiClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        expected_statuses: tuple[int, ...] = (200,),
    ) -> tuple[int, dict[str, Any]]:
        body = None if payload is None else json.dumps(payload).encode()
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"} if body is not None else {},
            method=method,
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                status = response.status
                response_payload = json.load(response)
        except HTTPError as error:
            code, attempt_id = _safe_http_failure(error)
            raise SmokeFailure(code, interpretation_attempt_id=attempt_id) from None
        except (URLError, TimeoutError):
            raise SmokeFailure("api_unavailable") from None

        if status not in expected_statuses:
            raise SmokeFailure(f"unexpected_http_status_{status}")
        if not isinstance(response_payload, dict):
            raise SmokeFailure("invalid_api_response")
        return status, response_payload


def _safe_http_failure_code(error: HTTPError) -> str:
    code, _ = _safe_http_failure(error)
    return code


def _safe_http_failure(error: HTTPError) -> tuple[str, str | None]:
    try:
        payload = json.load(error)
        detail = payload.get("detail", {})
        code = detail.get("code")
        attempt_id = detail.get("attempt_id")
        safe_code = (
            code
            if isinstance(code, str) and re.fullmatch(r"[a-z0-9_]{1,100}", code)
            else f"api_http_{error.code}"
        )
        safe_attempt_id = None
        if isinstance(attempt_id, str):
            with suppress(ValueError):
                safe_attempt_id = str(uuid.UUID(attempt_id))
        return safe_code, safe_attempt_id
    except (AttributeError, json.JSONDecodeError, OSError, TypeError, ValueError):
        pass
    return f"api_http_{error.code}", None


def _wait_until_healthy(client: ApiClient, wait_seconds: float = 30.0) -> None:
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        try:
            _, payload = client.request("GET", "/healthz")
            if payload == {"status": "ok"}:
                return
        except SmokeFailure:
            pass
        time.sleep(1)
    raise SmokeFailure("api_health_timeout")


def _assert_assessment_invariants(assessment: dict[str, Any]) -> None:
    summary = assessment.get("summary", {})
    impacts = assessment.get("enterprise_impacts", {})
    impact_count = sum(len(items) for items in impacts.values() if isinstance(items, list))
    actions = assessment.get("proposed_actions", [])

    if summary.get("affected_workers") != 3 or summary.get("unaffected_workers") != 3:
        raise SmokeFailure("assessment_worker_counts_regressed")
    if len(assessment.get("findings", [])) != 6:
        raise SmokeFailure("assessment_finding_count_regressed")
    if summary.get("enterprise_impacts") != 18 or impact_count != 18:
        raise SmokeFailure("assessment_impact_count_regressed")
    if len(actions) != 13 or any(
        action.get("execution_status") != "not_executed" for action in actions
    ):
        raise SmokeFailure("assessment_action_invariants_regressed")
    if len(assessment.get("unresolved_questions", [])) != 8:
        raise SmokeFailure("assessment_question_count_regressed")


def run_smoke(client: ApiClient, summary: SmokeSummary) -> None:
    _wait_until_healthy(client)

    _, run = client.request(
        "POST",
        "/api/v1/policy-analysis-runs",
        payload={"policy_change_id": POLICY_CHANGE_ID},
        expected_statuses=(201,),
    )
    summary.run_id = str(run.get("id")) if run.get("id") else None
    summary.terminal_outcome = str(run.get("status", "unknown"))
    if run.get("status") != "completed":
        failure_code = run.get("failure_code")
        raise SmokeFailure(
            failure_code if isinstance(failure_code, str) else "policy_analysis_not_completed"
        )
    if not run.get("assessment_id") or not run.get("latest_extraction_attempt_id"):
        raise SmokeFailure("completed_run_missing_artifacts")

    summary.assessment_id = str(run["assessment_id"])
    _, extraction = client.request(
        "GET",
        f"/api/v1/policy-extraction-attempts/{run['latest_extraction_attempt_id']}",
    )
    if extraction.get("validation_outcome") != "accepted" or not extraction.get("accepted_rules"):
        raise SmokeFailure("extraction_not_accepted")

    _, assessment_before = client.request(
        "GET", f"/api/v1/impact-assessments/{summary.assessment_id}"
    )
    _assert_assessment_invariants(assessment_before)

    first_status, first_plan = client.request(
        "POST",
        f"/api/v1/impact-assessments/{summary.assessment_id}/change-plans",
        expected_statuses=(201,),
    )
    if first_status != 201:
        raise SmokeFailure("change_plan_not_created")
    summary.change_plan_id = str(first_plan.get("id")) if first_plan.get("id") else None
    summary.interpretation_attempt_id = (
        str(first_plan.get("interpretation_attempt_id"))
        if first_plan.get("interpretation_attempt_id")
        else None
    )
    if not summary.change_plan_id or not summary.interpretation_attempt_id:
        raise SmokeFailure("change_plan_missing_artifacts")

    _, attempt = client.request(
        "GET",
        f"/api/v1/policy-interpretation-attempts/{summary.interpretation_attempt_id}",
    )
    if attempt.get("status") != "accepted" or attempt.get("validation_errors"):
        raise SmokeFailure("interpretation_not_accepted")

    _, plan_by_id = client.request("GET", f"/api/v1/change-plans/{summary.change_plan_id}")
    _, plan_by_assessment = client.request(
        "GET", f"/api/v1/impact-assessments/{summary.assessment_id}/change-plan"
    )
    if plan_by_id != first_plan or plan_by_assessment != first_plan:
        raise SmokeFailure("accepted_change_plan_retrieval_mismatch")

    second_status, second_plan = client.request(
        "POST",
        f"/api/v1/impact-assessments/{summary.assessment_id}/change-plans",
        expected_statuses=(200,),
    )
    if second_status != 200 or second_plan.get("id") != summary.change_plan_id:
        raise SmokeFailure("change_plan_idempotency_failed")

    _, assessment_after = client.request(
        "GET", f"/api/v1/impact-assessments/{summary.assessment_id}"
    )
    if assessment_after != assessment_before:
        raise SmokeFailure("assessment_changed_after_interpretation")

    summary.terminal_outcome = "completed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout-seconds", type=float, default=300.0)
    args = parser.parse_args()

    extraction_provider = os.environ.get("EXTRACTION_MODEL_PROVIDER", "openai")
    interpretation_provider = os.environ.get("INTERPRETATION_MODEL_PROVIDER", "openai")
    provider = (
        extraction_provider
        if extraction_provider == interpretation_provider
        else f"{extraction_provider}/{interpretation_provider}"
    )
    summary = SmokeSummary(
        provider=provider,
        extraction_model=os.environ.get("EXTRACTION_MODEL", "gpt-5.6-luna"),
        interpretation_model=os.environ.get("INTERPRETATION_MODEL", "gpt-5.6-luna"),
    )
    started_at = time.monotonic()

    try:
        run_smoke(ApiClient(args.base_url, args.timeout_seconds), summary)
    except SmokeFailure as error:
        summary.failure_code = error.code
        if error.interpretation_attempt_id:
            summary.interpretation_attempt_id = error.interpretation_attempt_id
        summary.terminal_outcome = (
            summary.terminal_outcome if summary.terminal_outcome != "not_started" else "failed"
        )
        exit_code = 1
    except Exception:
        summary.failure_code = "smoke_internal_error"
        summary.terminal_outcome = "failed"
        exit_code = 1
    else:
        exit_code = 0
    finally:
        summary.elapsed_seconds = time.monotonic() - started_at
        print(json.dumps(summary.as_dict(), sort_keys=True))

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
