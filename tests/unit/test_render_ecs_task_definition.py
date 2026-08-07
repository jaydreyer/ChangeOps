import pytest

from scripts.render_ecs_task_definition import render_task_definition


def test_render_replaces_only_named_images_and_removes_read_only_fields() -> None:
    rendered = render_task_definition(
        {
            "taskDefinition": {
                "family": "changeops-demo-application",
                "taskDefinitionArn": "arn:old",
                "revision": 4,
                "status": "ACTIVE",
                "registeredAt": "timestamp",
                "containerDefinitions": [
                    {"name": "api", "image": "api:old", "secrets": [{"name": "DB_PASSWORD"}]},
                    {"name": "web", "image": "web:old"},
                ],
                "networkMode": "awsvpc",
            }
        },
        {"api": "api:commit-sha", "web": "web:commit-sha"},
    )

    assert rendered["containerDefinitions"] == [
        {
            "name": "api",
            "image": "api:commit-sha",
            "secrets": [{"name": "DB_PASSWORD"}],
        },
        {"name": "web", "image": "web:commit-sha"},
    ]
    assert rendered["family"] == "changeops-demo-application"
    assert "taskDefinitionArn" not in rendered
    assert "revision" not in rendered
    assert "registeredAt" not in rendered


def test_render_fails_when_reviewed_container_name_is_missing() -> None:
    with pytest.raises(ValueError, match="missing containers: web"):
        render_task_definition(
            {"taskDefinition": {"containerDefinitions": [{"name": "api", "image": "api:old"}]}},
            {"web": "web:commit-sha"},
        )
