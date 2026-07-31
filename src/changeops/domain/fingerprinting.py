import hashlib
import json
from dataclasses import asdict
from datetime import date
from typing import Any

from changeops.domain.types import (
    EnterpriseContextInput,
    PolicyInput,
    TrainingInput,
    TripInput,
    WorkerInput,
)


def calculate_input_fingerprint(
    *,
    analyzer_version: str,
    policy: PolicyInput,
    workers: list[WorkerInput] | tuple[WorkerInput, ...],
    trips: list[TripInput] | tuple[TripInput, ...],
    training_records: list[TrainingInput] | tuple[TrainingInput, ...],
    context: EnterpriseContextInput,
) -> str:
    payload = {
        "analyzer_version": analyzer_version,
        "policy": {
            "id": policy.id,
            "title": policy.title,
            "version": policy.version,
            "effective_date": policy.effective_date,
            "policy_text": policy.policy_text,
            "structured_rules": policy.rules.model_dump(mode="json"),
        },
        "workers": _records(workers),
        "trips": _records(trips),
        "training_records": _records(training_records),
        "teams": _records(context.teams),
        "team_memberships": _records(context.team_memberships),
        "systems": _records(context.systems),
        "documents": _records(context.documents),
        "courses": _records(context.courses),
        "system_dependencies": _records(context.system_dependencies),
        "document_dependencies": _records(context.document_dependencies),
        "training_dependencies": _records(context.training_dependencies),
        "commitments": _records(context.commitments),
        "commitment_assignments": _records(context.commitment_assignments),
        "questions": _records(context.questions),
    }
    canonical = json.dumps(
        _canonical_value(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _records(records: Any) -> list[dict[str, Any]]:
    return [asdict(record) for record in sorted(records, key=lambda item: item.id)]


def _canonical_value(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _canonical_value(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    return value
