import argparse
import json
from pathlib import Path
from typing import Any

from changeops.domain.action_approval import (
    calculate_approval_progress,
    map_approval_failure,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the deterministic action-approval workflow evaluation."
    )
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()
    report, passed = evaluate(args.dataset)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(1)


def evaluate(dataset_path: Path) -> tuple[dict[str, Any], bool]:
    dataset = json.loads(dataset_path.read_text())
    results = []
    metric_counts = {
        "count_correctness": [0, 0],
        "route_correctness": [0, 0],
        "resume_correctness": [0, 0],
        "failure_correctness": [0, 0],
    }
    for case in dataset["cases"]:
        if case["kind"] == "failure":
            error = (
                ValueError("fixture") if case["error"] == "membership" else RuntimeError("fixture")
            )
            actual_failure = map_approval_failure(error, phase=case["phase"])
            failure_correct = actual_failure == case["expected_failure_code"]
            count_correct = route_correct = resume_correct = True
            result = {"id": case["id"], "failure_code": actual_failure}
        else:
            progress = calculate_approval_progress(case["statuses"])
            count_correct = progress.__dict__ == case["expected_summary"]
            route_correct = progress.route == case["expected_route"]
            resumed = calculate_approval_progress(case.get("resumed_statuses", case["statuses"]))
            resume_correct = resumed.__dict__ == case.get(
                "expected_resumed_summary", case["expected_summary"]
            ) and resumed.route == case.get("expected_resumed_route", case["expected_route"])
            failure_correct = True
            result = {"id": case["id"], "route": progress.route}

        _count(metric_counts["count_correctness"], count_correct)
        _count(metric_counts["route_correctness"], route_correct)
        _count(metric_counts["resume_correctness"], resume_correct)
        _count(metric_counts["failure_correctness"], failure_correct)
        result["passed"] = all((count_correct, route_correct, resume_correct, failure_correct))
        results.append(result)

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
