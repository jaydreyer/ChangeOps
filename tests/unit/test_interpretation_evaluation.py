from pathlib import Path

from changeops.evaluation.interpretation import evaluate


def test_interpretation_golden_scenarios_pass() -> None:
    report, passed = evaluate(Path("tests/golden/interpretation/v1/dataset.json"))
    assert passed
    assert report["dataset_version"] == "policy-interpretation-evaluation-v1"
    assert len(report["cases"]) == 11
