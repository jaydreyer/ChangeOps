from pathlib import Path

from changeops.evaluation.approval_workflow import evaluate


def test_approval_workflow_golden_scenarios_pass() -> None:
    report, passed = evaluate(Path("tests/golden/approval_workflow/v1/dataset.json"))

    assert passed
    assert report["dataset_version"] == "action-approval-workflow-v1"
    assert len(report["cases"]) == 10
