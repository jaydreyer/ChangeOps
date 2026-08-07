#!/usr/bin/env python3
"""Render a reviewed ECS task definition with immutable release images."""

import argparse
import json
from pathlib import Path
from typing import Any

READ_ONLY_FIELDS = {
    "compatibilities",
    "deregisteredAt",
    "registeredAt",
    "registeredBy",
    "requiresAttributes",
    "revision",
    "status",
    "taskDefinitionArn",
}


def render_task_definition(
    describe_payload: dict[str, Any],
    image_replacements: dict[str, str],
) -> dict[str, Any]:
    task_definition = describe_payload.get("taskDefinition")
    if not isinstance(task_definition, dict):
        raise ValueError("ECS describe payload does not contain a taskDefinition object.")
    rendered = {key: value for key, value in task_definition.items() if key not in READ_ONLY_FIELDS}
    containers = rendered.get("containerDefinitions")
    if not isinstance(containers, list):
        raise ValueError("Task definition does not contain containerDefinitions.")
    found: set[str] = set()
    for container in containers:
        name = container.get("name")
        if name in image_replacements:
            container["image"] = image_replacements[name]
            found.add(name)
    missing = set(image_replacements) - found
    if missing:
        raise ValueError(f"Task definition is missing containers: {', '.join(sorted(missing))}.")
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--container",
        action="append",
        default=[],
        metavar="NAME=IMAGE",
        help="Replace one named container image. Repeat for multiple containers.",
    )
    args = parser.parse_args()
    replacements: dict[str, str] = {}
    for item in args.container:
        name, separator, image = item.partition("=")
        if not separator or not name or not image:
            parser.error("--container values must use NAME=IMAGE.")
        replacements[name] = image
    if not replacements:
        parser.error("At least one --container replacement is required.")

    payload = json.loads(args.input.read_text())
    rendered = render_task_definition(payload, replacements)
    args.output.write_text(json.dumps(rendered, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
