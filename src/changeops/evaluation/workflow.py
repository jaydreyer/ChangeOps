import argparse
import json
from pathlib import Path
from typing import Any

from changeops.domain.policy_analysis import decide_extraction_outcome
from changeops.domain.policy_extraction import ValidationIssue


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the scoped deterministic policy-analysis workflow evaluation."
    )
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()
    report, passed = evaluate(args.dataset)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(1)


def evaluate(dataset_path: Path) -> tuple[dict[str, Any], bool]:
    dataset = json.loads(dataset_path.read_text())
    results: list[dict[str, Any]] = []
    metric_counts = {
        "terminal_status_correctness": [0, 0],
        "clarification_decision_correctness": [0, 0],
        "assessment_boundary_correctness": [0, 0],
        "retry_bound_correctness": [0, 0],
        "provenance_retention": [0, 0],
        "duplicate_assessment_prevention": [0, 0],
    }
    for case in dataset["cases"]:
        issues = tuple(
            ValidationIssue(
                code=code,
                message=(
                    "structured_output_parsing_failed: fixture"
                    if code == "structured_output_failure"
                    else "fixture"
                ),
            )
            for code in case["issues"]
        )
        decision = decide_extraction_outcome(
            validation_outcome=case["validation_outcome"],
            issues=issues,
            retry_count=case["retry_count"],
        )
        route_correct = decision.route == case["expected_route"]
        failure_correct = decision.failure_code == case["expected_failure_code"]
        clarification_actual = decision.route == "clarify"
        clarification_correct = clarification_actual == case["clarification_expected"]
        assessment_actual = decision.route == "accepted"
        boundary_correct = assessment_actual == case["assessment_allowed"]
        retry_correct = not (case["retry_count"] >= 1 and decision.route == "retry")
        provenance_correct = not case.get("human_provenance_expected", False) or assessment_actual
        duplicate_guard_correct = not assessment_actual or case["assessment_allowed"]

        _count(metric_counts["terminal_status_correctness"], route_correct and failure_correct)
        _count(metric_counts["clarification_decision_correctness"], clarification_correct)
        _count(metric_counts["assessment_boundary_correctness"], boundary_correct)
        _count(metric_counts["retry_bound_correctness"], retry_correct)
        _count(metric_counts["provenance_retention"], provenance_correct)
        _count(metric_counts["duplicate_assessment_prevention"], duplicate_guard_correct)
        case_passed = all(
            (
                route_correct,
                failure_correct,
                clarification_correct,
                boundary_correct,
                retry_correct,
                provenance_correct,
                duplicate_guard_correct,
            )
        )
        results.append({"id": case["id"], "passed": case_passed, "route": decision.route})

    report = {
        "dataset_version": dataset["dataset_version"],
        "scope": dataset["scope"],
        "passed": all(item["passed"] for item in results),
        "metrics": {
            name: {"correct": value[0], "total": value[1]} for name, value in metric_counts.items()
        },
        "cases": results,
    }
    return report, report["passed"]


def _count(metric: list[int], correct: bool) -> None:
    metric[1] += 1
    metric[0] += int(correct)


if __name__ == "__main__":
    main()
