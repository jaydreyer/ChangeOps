import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from changeops.db.models import (
    AssessmentUnresolvedQuestion,
    AssessmentWorkerResult,
    Evidence,
    Finding,
    ImpactAssessment,
    PolicyChange,
    PolicyChangeQuestion,
    ProposedAction,
    TrainingRecord,
    Trip,
    Worker,
)
from changeops.domain.impact_analysis import ANALYZER_VERSION, analyze_policy
from changeops.domain.types import (
    AnalysisResult,
    InternationalTravelPolicyRules,
    PolicyInput,
    TrainingInput,
    TripInput,
    WorkerInput,
)


class PolicyChangeNotFoundError(Exception):
    pass


class PolicyNotAnalyzableError(Exception):
    pass


class ImpactAssessmentNotFoundError(Exception):
    pass


def create_impact_assessment(session: Session, policy_change_id: str) -> ImpactAssessment:
    with session.begin():
        policy_record = session.get(PolicyChange, policy_change_id)
        if policy_record is None:
            raise PolicyChangeNotFoundError(policy_change_id)

        try:
            rules = InternationalTravelPolicyRules.model_validate(policy_record.structured_rules)
        except ValidationError as error:
            raise PolicyNotAnalyzableError(policy_change_id) from error

        worker_records = list(
            session.scalars(
                select(Worker)
                .where(Worker.organization_id == policy_record.organization_id)
                .order_by(Worker.id)
            )
        )
        worker_ids = [worker.id for worker in worker_records]
        trip_records = list(
            session.scalars(select(Trip).where(Trip.worker_id.in_(worker_ids)).order_by(Trip.id))
        )
        training_records = list(
            session.scalars(
                select(TrainingRecord)
                .where(TrainingRecord.worker_id.in_(worker_ids))
                .order_by(TrainingRecord.id)
            )
        )
        question_records = list(
            session.scalars(
                select(PolicyChangeQuestion)
                .where(PolicyChangeQuestion.policy_change_id == policy_change_id)
                .order_by(PolicyChangeQuestion.sequence)
            )
        )

        policy = _policy_input(policy_record, rules)
        workers = [_worker_input(record) for record in worker_records]
        trips = [_trip_input(record) for record in trip_records]
        training = [_training_input(record) for record in training_records]
        input_fingerprint = _input_fingerprint(policy, workers, trips, training)
        result = analyze_policy(policy, workers, trips, training)

        assessment_id = _persist_assessment(
            session=session,
            policy_record=policy_record,
            worker_records=worker_records,
            trip_records=trip_records,
            training_records=training_records,
            question_records=question_records,
            analysis=result,
            input_fingerprint=input_fingerprint,
        )

    return get_impact_assessment(session, assessment_id)


def get_impact_assessment(
    session: Session,
    assessment_id: uuid.UUID,
) -> ImpactAssessment:
    statement = (
        select(ImpactAssessment)
        .where(ImpactAssessment.id == assessment_id)
        .options(
            selectinload(ImpactAssessment.worker_results).selectinload(
                AssessmentWorkerResult.worker
            ),
            selectinload(ImpactAssessment.worker_results).selectinload(AssessmentWorkerResult.trip),
            selectinload(ImpactAssessment.findings).selectinload(Finding.worker_result),
            selectinload(ImpactAssessment.findings).selectinload(Finding.evidence),
            selectinload(ImpactAssessment.evidence),
            selectinload(ImpactAssessment.proposed_actions).selectinload(ProposedAction.worker),
            selectinload(ImpactAssessment.unresolved_questions),
        )
    )
    assessment = session.scalar(statement)
    if assessment is None:
        raise ImpactAssessmentNotFoundError(str(assessment_id))
    return assessment


def _persist_assessment(
    *,
    session: Session,
    policy_record: PolicyChange,
    worker_records: list[Worker],
    trip_records: list[Trip],
    training_records: list[TrainingRecord],
    question_records: list[PolicyChangeQuestion],
    analysis: AnalysisResult,
    input_fingerprint: str,
) -> uuid.UUID:
    now = datetime.now(UTC)
    assessment = ImpactAssessment(
        policy_change_id=policy_record.id,
        status="completed",
        analyzer_version=ANALYZER_VERSION,
        input_fingerprint=input_fingerprint,
        created_at=now,
        completed_at=now,
    )
    session.add(assessment)
    session.flush()

    result_by_worker_id: dict[str, AssessmentWorkerResult] = {}
    for result in analysis.worker_results:
        record = AssessmentWorkerResult(
            assessment_id=assessment.id,
            worker_id=result.worker_id,
            trip_id=result.trip_id,
            classification=result.classification,
            explanation=result.explanation,
            reason_codes=list(result.reason_codes),
        )
        session.add(record)
        result_by_worker_id[result.worker_id] = record
    session.flush()

    required_evidence_keys = {key for finding in analysis.findings for key in finding.evidence_keys}
    evidence_by_key = _persist_evidence(
        session=session,
        assessment_id=assessment.id,
        policy_record=policy_record,
        worker_records=worker_records,
        trip_records=trip_records,
        training_records=training_records,
        required_keys=required_evidence_keys,
    )

    finding_by_key: dict[str, Finding] = {}
    for result in analysis.findings:
        finding = Finding(
            assessment_id=assessment.id,
            worker_result_id=result_by_worker_id[result.worker_id].id,
            finding_type=result.finding_type,
            severity=result.severity,
            rule_code=result.rule_code,
            explanation=result.explanation,
            evidence=[evidence_by_key[key] for key in result.evidence_keys],
        )
        session.add(finding)
        finding_by_key[result.key] = finding
    session.flush()

    for result in analysis.proposed_actions:
        session.add(
            ProposedAction(
                assessment_id=assessment.id,
                finding_id=finding_by_key[result.finding_key].id,
                worker_id=result.worker_id,
                action_key=result.key,
                action_type=result.action_type,
                target_type=result.target_type,
                target_identifier=result.target_identifier,
                description=result.description,
                due_date=result.due_date,
                execution_status=result.execution_status,
            )
        )

    for source_question in question_records:
        session.add(
            AssessmentUnresolvedQuestion(
                assessment_id=assessment.id,
                source_question_id=source_question.id,
                sequence=source_question.sequence,
                question=source_question.question,
            )
        )
    session.flush()
    return assessment.id


def _persist_evidence(
    *,
    session: Session,
    assessment_id: uuid.UUID,
    policy_record: PolicyChange,
    worker_records: list[Worker],
    trip_records: list[Trip],
    training_records: list[TrainingRecord],
    required_keys: set[str],
) -> dict[str, Evidence]:
    evidence_specs = _evidence_specs(
        policy_record=policy_record,
        worker_records=worker_records,
        trip_records=trip_records,
        training_records=training_records,
    )
    missing_keys = required_keys - evidence_specs.keys()
    if missing_keys:
        raise RuntimeError(f"Missing evidence specifications: {sorted(missing_keys)}")

    evidence_by_key: dict[str, Evidence] = {}
    for key in sorted(required_keys):
        spec = evidence_specs[key]
        evidence = Evidence(
            assessment_id=assessment_id,
            evidence_key=key,
            evidence_type=spec["evidence_type"],
            source_type=spec["source_type"],
            source_id=spec["source_id"],
            label=spec["label"],
            snapshot=spec["snapshot"],
        )
        session.add(evidence)
        evidence_by_key[key] = evidence
    session.flush()
    return evidence_by_key


def _evidence_specs(
    *,
    policy_record: PolicyChange,
    worker_records: list[Worker],
    trip_records: list[Trip],
    training_records: list[TrainingRecord],
) -> dict[str, dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {}
    for worker in worker_records:
        specs[f"worker:{worker.id}"] = {
            "evidence_type": "worker_record",
            "source_type": "worker",
            "source_id": worker.id,
            "label": f"{worker.full_name} worker record",
            "snapshot": {
                "worker_id": worker.id,
                "full_name": worker.full_name,
                "worker_type": worker.worker_type,
                "department": worker.department,
                "manager_name": worker.manager_name,
                "assigned_work_country": worker.assigned_work_country,
            },
        }
    for trip in trip_records:
        specs[f"trip:{trip.id}"] = {
            "evidence_type": "trip_record",
            "source_type": "trip",
            "source_id": trip.id,
            "label": f"{trip.id} trip record",
            "snapshot": {
                "trip_id": trip.id,
                "worker_id": trip.worker_id,
                "origin_country": trip.origin_country,
                "destination_country": trip.destination_country,
                "departure_date": trip.departure_date.isoformat(),
                "booking_date": (trip.booking_date.isoformat() if trip.booking_date else None),
                "booking_status": trip.booking_status,
            },
        }
    for training in training_records:
        specs[f"training:{training.id}"] = {
            "evidence_type": "training_record",
            "source_type": "training_record",
            "source_id": training.id,
            "label": f"{training.worker_id} training record",
            "snapshot": {
                "training_record_id": training.id,
                "worker_id": training.worker_id,
                "course_identifier": training.course_identifier,
                "completion_status": training.completion_status,
                "completion_date": (
                    training.completion_date.isoformat() if training.completion_date else None
                ),
            },
        }

    policy_snapshot = {
        "policy_id": policy_record.id,
        "title": policy_record.title,
        "version": policy_record.version,
        "effective_date": policy_record.effective_date.isoformat(),
        "policy_text": policy_record.policy_text,
    }
    rules = policy_record.structured_rules
    policy_specs = {
        "worker_scope": (
            "Policy worker-scope rule",
            rules["worker_scope"],
        ),
        "destination_scope": (
            "Policy destination-scope rule",
            rules["trip_scope"],
        ),
        "effective_date": (
            "Policy effective-date rule",
            {"effective_date": policy_record.effective_date.isoformat()},
        ),
        "manager_approval": (
            "Policy manager-approval rule",
            rules["manager_approval"],
        ),
        "booking_exception": (
            "Policy booking-date exception",
            rules["manager_approval"],
        ),
        "security_training": (
            "Policy security-training rule",
            rules["security_training"],
        ),
    }
    for suffix, (label, rule_snapshot) in policy_specs.items():
        specs[f"policy:{policy_record.id}:{suffix}"] = {
            "evidence_type": "policy_rule",
            "source_type": "policy_change",
            "source_id": policy_record.id,
            "label": label,
            "snapshot": {**policy_snapshot, "rule": rule_snapshot},
        }
    return specs


def _policy_input(
    policy: PolicyChange,
    rules: InternationalTravelPolicyRules,
) -> PolicyInput:
    return PolicyInput(
        id=policy.id,
        title=policy.title,
        version=policy.version,
        effective_date=policy.effective_date,
        policy_text=policy.policy_text,
        rules=rules,
    )


def _worker_input(worker: Worker) -> WorkerInput:
    return WorkerInput(
        id=worker.id,
        full_name=worker.full_name,
        worker_type=worker.worker_type,
        department=worker.department,
        manager_name=worker.manager_name,
        assigned_work_country=worker.assigned_work_country,
    )


def _trip_input(trip: Trip) -> TripInput:
    return TripInput(
        id=trip.id,
        worker_id=trip.worker_id,
        origin_country=trip.origin_country,
        destination_country=trip.destination_country,
        departure_date=trip.departure_date,
        booking_date=trip.booking_date,
        booking_status=trip.booking_status,
    )


def _training_input(training: TrainingRecord) -> TrainingInput:
    return TrainingInput(
        id=training.id,
        worker_id=training.worker_id,
        course_identifier=training.course_identifier,
        completion_status=training.completion_status,
        completion_date=training.completion_date,
    )


def _input_fingerprint(
    policy: PolicyInput,
    workers: list[WorkerInput],
    trips: list[TripInput],
    training: list[TrainingInput],
) -> str:
    payload = {
        "analyzer_version": ANALYZER_VERSION,
        "policy": {
            "id": policy.id,
            "title": policy.title,
            "version": policy.version,
            "effective_date": policy.effective_date.isoformat(),
            "policy_text": policy.policy_text,
            "structured_rules": policy.rules.model_dump(mode="json"),
        },
        "workers": [
            {
                "id": worker.id,
                "full_name": worker.full_name,
                "worker_type": worker.worker_type,
                "department": worker.department,
                "manager_name": worker.manager_name,
                "assigned_work_country": worker.assigned_work_country,
            }
            for worker in sorted(workers, key=lambda item: item.id)
        ],
        "trips": [
            {
                "id": trip.id,
                "worker_id": trip.worker_id,
                "origin_country": trip.origin_country,
                "destination_country": trip.destination_country,
                "departure_date": trip.departure_date.isoformat(),
                "booking_date": (trip.booking_date.isoformat() if trip.booking_date else None),
                "booking_status": trip.booking_status,
            }
            for trip in sorted(trips, key=lambda item: item.id)
        ],
        "training": [
            {
                "id": record.id,
                "worker_id": record.worker_id,
                "course_identifier": record.course_identifier,
                "completion_status": record.completion_status,
                "completion_date": (
                    record.completion_date.isoformat() if record.completion_date else None
                ),
            }
            for record in sorted(training, key=lambda item: item.id)
        ],
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
