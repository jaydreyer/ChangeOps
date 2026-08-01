import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from changeops.ai.policy_interpreter import PROMPT_VERSION, _ground_proposed_change_plan
from changeops.domain.policy_interpretation import (
    INTERPRETATION_SCHEMA_VERSION,
    CandidateChangePlan,
    ChangePlanValidationError,
    PolicyInterpretationInput,
    ProposedChangePlan,
)
from changeops.domain.policy_interpretation_validation import validate_candidate_change_plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate deterministic interpretation grounding.")
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()
    report, passed = evaluate(args.dataset)
    print(json.dumps(report, indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(1)


def evaluate(dataset_path: Path) -> tuple[dict[str, Any], bool]:
    dataset = json.loads(dataset_path.read_text())
    interpretation_input = PolicyInterpretationInput.model_validate(dataset["input"])
    results = []
    for case in dataset["cases"]:
        actual_valid = False
        reasons: list[str] = []
        try:
            if "proposal" in case:
                proposal = ProposedChangePlan.model_validate(case["proposal"])
                candidate = _ground_proposed_change_plan(proposal, interpretation_input)
            else:
                candidate = CandidateChangePlan.model_validate(case["candidate"])
            validate_candidate_change_plan(candidate, interpretation_input)
            actual_valid = True
        except ChangePlanValidationError as error:
            reasons = [item.code for item in error.issues]
        except ValidationError:
            reasons = ["malformed_output"]
        passed = actual_valid == case["expected_valid"]
        if case.get("expected_code") is not None:
            passed = passed and case["expected_code"] in reasons
        results.append(
            {"id": case["id"], "passed": passed, "valid": actual_valid, "failure_reasons": reasons}
        )
    report = {
        "dataset_version": dataset["dataset_version"],
        "prompt_version": PROMPT_VERSION,
        "schema_version": INTERPRETATION_SCHEMA_VERSION,
        "provider": "fixture",
        "model": "fixed-proposals-and-candidates-v1",
        "passed": all(item["passed"] for item in results),
        "cases": results,
    }
    return report, report["passed"]


if __name__ == "__main__":
    main()
