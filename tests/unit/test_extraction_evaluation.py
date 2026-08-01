import json
from pathlib import Path

from changeops.evaluation.extraction import evaluate
from changeops.services.seed_service import POLICY_TEXT, STRUCTURED_RULES


def test_versioned_golden_extraction_dataset_passes() -> None:
    dataset = Path("tests/golden/extraction/v1/dataset.json")

    report, passed = evaluate(dataset)

    assert passed is True
    assert report["dataset_version"] == "international-travel-golden-v1"
    assert report["metrics"]["support_status_accuracy"]["rate"] == 1.0
    assert report["metrics"]["field_level_correctness"]["rate"] == 1.0
    assert report["metrics"]["provenance_resolution"]["rate"] == 1.0
    assert report["metrics"]["fail_closed_behavior"]["rate"] == 1.0
    assert report["metrics"]["structured_output_failure_rate"] == {
        "failures": 1,
        "total": 7,
        "rate": 1 / 7,
    }


def test_first_golden_case_is_the_seeded_policy_and_hand_authored_rules() -> None:
    dataset = json.loads(Path("tests/golden/extraction/v1/dataset.json").read_text())
    first_case = dataset["cases"][0]

    assert first_case["id"] == "canonical_seeded_policy"
    assert first_case["policy_text"] == POLICY_TEXT
    assert first_case["expected"]["accepted_rules"] == STRUCTURED_RULES
