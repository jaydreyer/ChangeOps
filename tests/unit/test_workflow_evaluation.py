from pathlib import Path

from changeops.evaluation.workflow import evaluate


def test_workflow_golden_scenarios_pass() -> None:
    report, passed = evaluate(Path("tests/golden/workflow/v1/dataset.json"))

    assert passed
    assert report["dataset_version"] == "policy-analysis-workflow-v1"
    assert len(report["cases"]) == 6
