import argparse
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from changeops.ai.policy_extractor import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    StructuredOutputModel,
    invoke_policy_extractor,
)
from changeops.domain.policy_extraction import (
    PolicyExtractionProposal,
    TrainingCourseReference,
)
from changeops.domain.policy_extraction_validation import validate_policy_extraction

COURSES = (
    TrainingCourseReference(
        identifier="international-travel-security",
        name="International Travel Security",
        active=True,
    ),
)


class GoldenFixtureModel(StructuredOutputModel):
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response

    def with_structured_output(
        self,
        schema: type[PolicyExtractionProposal],
        *,
        include_raw: bool,
    ) -> RunnableLambda:
        if schema is not PolicyExtractionProposal or not include_raw:
            raise AssertionError("Evaluation must use the production structured-output contract.")
        return RunnableLambda(lambda _: self.response)


@dataclass
class Counts:
    total_cases: int = 0
    support_correct: int = 0
    support_total: int = 0
    field_correct: int = 0
    field_total: int = 0
    provenance_resolved: int = 0
    provenance_total: int = 0
    fail_closed_correct: int = 0
    fail_closed_total: int = 0
    structured_failures: int = 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the versioned policy extraction evaluation.")
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()

    report, passed = evaluate(args.dataset)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(1)


def evaluate(dataset_path: Path) -> tuple[dict[str, Any], bool]:
    dataset = json.loads(dataset_path.read_text())
    counts = Counts()
    case_results: list[dict[str, Any]] = []

    for case in dataset["cases"]:
        counts.total_cases += 1
        invocation = invoke_policy_extractor(
            GoldenFixtureModel(_fixture_response(case)),
            case["policy_text"],
        )
        if invocation.proposal is None:
            counts.structured_failures += 1
            outcome = "validation_failed"
            accepted_rules = None
        else:
            validation = validate_policy_extraction(
                invocation.proposal,
                policy_text=case["policy_text"],
                policy_effective_date=date.fromisoformat(case["stored_effective_date"]),
                training_courses=COURSES,
            )
            outcome = validation.outcome
            accepted_rules = (
                validation.accepted_rules.model_dump(mode="json")
                if validation.accepted_rules is not None
                else None
            )
            for item in invocation.proposal.provenance:
                counts.provenance_total += 1
                if case["policy_text"][item.start : item.end] == item.quote:
                    counts.provenance_resolved += 1
            for finding in invocation.proposal.findings:
                counts.provenance_total += 1
                item = finding.provenance
                if case["policy_text"][item.start : item.end] == item.quote:
                    counts.provenance_resolved += 1

        expected = case["expected"]
        actual_support = (
            invocation.proposal.support_status if invocation.proposal is not None else None
        )
        counts.support_total += 1
        if actual_support == expected["support_status"]:
            counts.support_correct += 1

        expected_rules = expected["accepted_rules"]
        if expected_rules is not None:
            _compare_fields(expected_rules, accepted_rules, counts)

        if expected["validation_outcome"] != "accepted":
            counts.fail_closed_total += 1
            if outcome != "accepted" and accepted_rules is None:
                counts.fail_closed_correct += 1

        case_passed = (
            actual_support == expected["support_status"]
            and outcome == expected["validation_outcome"]
            and accepted_rules == expected_rules
        )
        case_results.append(
            {
                "id": case["id"],
                "passed": case_passed,
                "support_status": actual_support,
                "validation_outcome": outcome,
            }
        )

    passed = all(item["passed"] for item in case_results)
    report = {
        "dataset_version": dataset["dataset_version"],
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "model_provider": "fixture",
        "model_identifier": dataset["dataset_version"],
        "passed": passed,
        "metrics": {
            "support_status_accuracy": _ratio(
                counts.support_correct,
                counts.support_total,
            ),
            "field_level_correctness": _ratio(counts.field_correct, counts.field_total),
            "provenance_resolution": _ratio(
                counts.provenance_resolved,
                counts.provenance_total,
            ),
            "fail_closed_behavior": _ratio(
                counts.fail_closed_correct,
                counts.fail_closed_total,
            ),
            "structured_output_failure_rate": {
                "failures": counts.structured_failures,
                "total": counts.total_cases,
                "rate": counts.structured_failures / counts.total_cases,
            },
        },
        "cases": case_results,
    }
    return report, passed


def _fixture_response(case: dict[str, Any]) -> dict[str, Any]:
    if "malformed_output" in case:
        return {
            "raw": AIMessage(content=case["malformed_output"]),
            "parsed": None,
            "parsing_error": ValueError("malformed fixture output"),
        }

    output = case["model_output"]
    proposal_payload = {
        key: output[key] for key in ("policy_family", "support_status", "candidate_rules")
    }
    proposal_payload["provenance"] = [
        _span(case["policy_text"], field_path, quote)
        for field_path, quote in output["provenance_quotes"].items()
    ]
    proposal_payload["findings"] = [
        {
            **{key: finding.get(key) for key in ("kind", "code", "message", "field_path")},
            "provenance": _span(
                case["policy_text"],
                f"finding.{finding['code']}",
                finding["quote"],
            ),
        }
        for finding in output["findings"]
    ]
    proposal = PolicyExtractionProposal.model_validate(proposal_payload)
    return {
        "raw": AIMessage(content="golden fixture structured output"),
        "parsed": proposal,
        "parsing_error": None,
    }


def _span(policy_text: str, field_path: str, quote: str) -> dict[str, Any]:
    start = policy_text.index(quote)
    return {
        "field_path": field_path,
        "start": start,
        "end": start + len(quote),
        "quote": quote,
    }


def _compare_fields(
    expected: Any,
    actual: Any,
    counts: Counts,
) -> None:
    if isinstance(expected, dict):
        actual_mapping = actual if isinstance(actual, dict) else {}
        for key, value in expected.items():
            _compare_fields(value, actual_mapping.get(key), counts)
        return
    counts.field_total += 1
    if expected == actual:
        counts.field_correct += 1


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "correct": numerator,
        "total": denominator,
        "rate": numerator / denominator if denominator else 1.0,
    }


if __name__ == "__main__":
    main()
