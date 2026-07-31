import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from changeops.db.models import (
    AssessmentEnterpriseImpact,
    AssessmentImpactPathElement,
    AssessmentUnresolvedQuestion,
    AssessmentWorkerResult,
    CommitmentAssignment,
    CustomerCommitment,
    EnterpriseDocument,
    EnterpriseSystem,
    Evidence,
    Finding,
    ImpactAssessment,
    PolicyChange,
    PolicyChangeQuestion,
    PolicyDocumentDependency,
    PolicySystemDependency,
    PolicyTrainingDependency,
    ProposedAction,
    Team,
    TrainingCourse,
    TrainingRecord,
    Trip,
    Worker,
    WorkerTeamMembership,
)
from changeops.domain.enterprise_impact_analysis import analyze_enterprise_impacts
from changeops.domain.fingerprinting import calculate_input_fingerprint
from changeops.domain.impact_analysis import ANALYZER_VERSION as WORKER_ANALYZER_VERSION
from changeops.domain.impact_analysis import analyze_policy
from changeops.domain.types import (
    AnalysisResult,
    CommitmentAssignmentInput,
    CustomerCommitmentInput,
    EnterpriseAnalysisResult,
    EnterpriseContextInput,
    EnterpriseDocumentInput,
    EnterpriseSystemInput,
    InternationalTravelPolicyRules,
    PolicyDocumentDependencyInput,
    PolicyInput,
    PolicySystemDependencyInput,
    PolicyTrainingDependencyInput,
    QuestionInput,
    TeamInput,
    TeamMembershipInput,
    TrainingCourseInput,
    TrainingInput,
    TripInput,
    WorkerInput,
)

ANALYZER_VERSION = f"{WORKER_ANALYZER_VERSION}+enterprise-impact-v1"


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

        source = _load_source_records(session, policy_record)
        policy = _policy_input(policy_record, rules)
        membership_by_worker_id = {item.worker_id: item for item in source["team_memberships"]}
        workers = [
            _worker_input(record, membership_by_worker_id.get(record.id))
            for record in source["workers"]
        ]
        trips = [_trip_input(record) for record in source["trips"]]
        training = [_training_input(record) for record in source["training_records"]]
        context = _enterprise_context(source)

        worker_result = analyze_policy(policy, workers, trips, training)
        enterprise_result = analyze_enterprise_impacts(
            policy,
            workers,
            trips,
            training,
            context,
            worker_result,
        )
        input_fingerprint = calculate_input_fingerprint(
            analyzer_version=ANALYZER_VERSION,
            policy=policy,
            workers=workers,
            trips=trips,
            training_records=training,
            context=context,
        )

        assessment_id = _persist_assessment(
            session=session,
            policy_record=policy_record,
            source=source,
            worker_analysis=worker_result,
            enterprise_analysis=enterprise_result,
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
            selectinload(ImpactAssessment.enterprise_impacts).selectinload(
                AssessmentEnterpriseImpact.evidence
            ),
            selectinload(ImpactAssessment.enterprise_impacts).selectinload(
                AssessmentEnterpriseImpact.path_elements
            ),
            selectinload(ImpactAssessment.proposed_actions).selectinload(ProposedAction.worker),
            selectinload(ImpactAssessment.proposed_actions).selectinload(ProposedAction.finding),
            selectinload(ImpactAssessment.proposed_actions).selectinload(
                ProposedAction.enterprise_impact
            ),
            selectinload(ImpactAssessment.unresolved_questions),
        )
    )
    assessment = session.scalar(statement)
    if assessment is None:
        raise ImpactAssessmentNotFoundError(str(assessment_id))
    return assessment


def _load_source_records(
    session: Session,
    policy_record: PolicyChange,
) -> dict[str, list[Any]]:
    organization_id = policy_record.organization_id
    workers = list(
        session.scalars(
            select(Worker).where(Worker.organization_id == organization_id).order_by(Worker.id)
        )
    )
    worker_ids = [item.id for item in workers]
    commitments = list(
        session.scalars(
            select(CustomerCommitment)
            .where(CustomerCommitment.organization_id == organization_id)
            .order_by(CustomerCommitment.id)
        )
    )
    commitment_ids = [item.id for item in commitments]
    return {
        "workers": workers,
        "trips": list(
            session.scalars(select(Trip).where(Trip.worker_id.in_(worker_ids)).order_by(Trip.id))
        ),
        "training_records": list(
            session.scalars(
                select(TrainingRecord)
                .where(TrainingRecord.worker_id.in_(worker_ids))
                .order_by(TrainingRecord.id)
            )
        ),
        "questions": list(
            session.scalars(
                select(PolicyChangeQuestion)
                .where(PolicyChangeQuestion.policy_change_id == policy_record.id)
                .order_by(PolicyChangeQuestion.sequence, PolicyChangeQuestion.id)
            )
        ),
        "teams": list(
            session.scalars(
                select(Team).where(Team.organization_id == organization_id).order_by(Team.id)
            )
        ),
        "team_memberships": list(
            session.scalars(
                select(WorkerTeamMembership)
                .where(WorkerTeamMembership.worker_id.in_(worker_ids))
                .order_by(WorkerTeamMembership.id)
            )
        ),
        "systems": list(
            session.scalars(
                select(EnterpriseSystem)
                .where(EnterpriseSystem.organization_id == organization_id)
                .order_by(EnterpriseSystem.id)
            )
        ),
        "documents": list(
            session.scalars(
                select(EnterpriseDocument)
                .where(EnterpriseDocument.organization_id == organization_id)
                .order_by(EnterpriseDocument.id)
            )
        ),
        "courses": list(
            session.scalars(
                select(TrainingCourse)
                .where(TrainingCourse.organization_id == organization_id)
                .order_by(TrainingCourse.id)
            )
        ),
        "system_dependencies": list(
            session.scalars(
                select(PolicySystemDependency)
                .where(PolicySystemDependency.policy_change_id == policy_record.id)
                .order_by(PolicySystemDependency.id)
            )
        ),
        "document_dependencies": list(
            session.scalars(
                select(PolicyDocumentDependency)
                .where(PolicyDocumentDependency.policy_change_id == policy_record.id)
                .order_by(PolicyDocumentDependency.id)
            )
        ),
        "training_dependencies": list(
            session.scalars(
                select(PolicyTrainingDependency)
                .where(PolicyTrainingDependency.policy_change_id == policy_record.id)
                .order_by(PolicyTrainingDependency.id)
            )
        ),
        "commitments": commitments,
        "commitment_assignments": list(
            session.scalars(
                select(CommitmentAssignment)
                .where(CommitmentAssignment.commitment_id.in_(commitment_ids))
                .order_by(CommitmentAssignment.id)
            )
        ),
    }


def _persist_assessment(
    *,
    session: Session,
    policy_record: PolicyChange,
    source: dict[str, list[Any]],
    worker_analysis: AnalysisResult,
    enterprise_analysis: EnterpriseAnalysisResult,
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
    for result in worker_analysis.worker_results:
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

    required_evidence_keys = {
        key
        for item in (*worker_analysis.findings, *enterprise_analysis.impacts)
        for key in item.evidence_keys
    }
    evidence_by_key = _persist_evidence(
        session=session,
        assessment_id=assessment.id,
        policy_record=policy_record,
        source=source,
        required_keys=required_evidence_keys,
    )

    finding_by_key: dict[str, Finding] = {}
    for result in worker_analysis.findings:
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

    impact_by_key: dict[str, AssessmentEnterpriseImpact] = {}
    for result in enterprise_analysis.impacts:
        impact = AssessmentEnterpriseImpact(
            assessment_id=assessment.id,
            domain=result.domain,
            object_type=result.object_type,
            source_key=result.source_key,
            display_name=result.display_name,
            classification=result.classification,
            explanation=result.explanation,
            reason_code=result.reason_code,
            sort_key=result.sort_key,
            evidence=[evidence_by_key[key] for key in result.evidence_keys],
        )
        session.add(impact)
        session.flush()
        for sequence, element in enumerate(result.relationship_path):
            session.add(
                AssessmentImpactPathElement(
                    impact_id=impact.id,
                    sequence=sequence,
                    object_type=element.object_type,
                    stable_key=element.stable_key,
                    display_label=element.display_label,
                    relationship_to_next=element.relationship_to_next,
                )
            )
        impact_by_key[result.key] = impact
    session.flush()

    for result in worker_analysis.proposed_actions:
        worker_record = next(item for item in source["workers"] if item.id == result.worker_id)
        if result.action_type == "manager_approval_request":
            impact_key = f"people:manager:{worker_record.manager_worker_id}"
        elif result.action_type == "training_assignment":
            course_id = policy_record.structured_rules["security_training"]["course_identifier"]
            impact_key = f"training:worker_training_requirement:{result.worker_id}:{course_id}"
        else:
            impact_key = ""
        session.add(
            ProposedAction(
                assessment_id=assessment.id,
                finding_id=finding_by_key[result.finding_key].id,
                enterprise_impact_id=(
                    impact_by_key[impact_key].id if impact_key in impact_by_key else None
                ),
                worker_id=result.worker_id,
                action_type=result.action_type,
                target_type=result.target_type,
                target_identifier=result.target_identifier,
                description=result.description,
                due_date=result.due_date,
                execution_status=result.execution_status,
            )
        )
    for result in enterprise_analysis.proposed_actions:
        session.add(
            ProposedAction(
                assessment_id=assessment.id,
                finding_id=None,
                enterprise_impact_id=impact_by_key[result.impact_key].id,
                worker_id=result.worker_id,
                action_type=result.action_type,
                target_type=result.target_type,
                target_identifier=result.target_identifier,
                description=result.description,
                due_date=result.due_date,
                execution_status=result.execution_status,
            )
        )

    for source_question in source["questions"]:
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
    source: dict[str, list[Any]],
    required_keys: set[str],
) -> dict[str, Evidence]:
    evidence_specs = _evidence_specs(policy_record=policy_record, source=source)
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
    source: dict[str, list[Any]],
) -> dict[str, dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {}
    membership_by_worker_id = {item.worker_id: item for item in source["team_memberships"]}
    for worker in source["workers"]:
        membership = membership_by_worker_id.get(worker.id)
        specs[f"worker:{worker.id}"] = _evidence(
            "worker_record",
            "worker",
            worker.id,
            f"{worker.full_name} worker record",
            {
                "worker_id": worker.id,
                "full_name": worker.full_name,
                "worker_type": worker.worker_type,
                "department": worker.department,
                "manager_name": worker.manager_name,
                "manager_worker_id": worker.manager_worker_id,
                "team_id": membership.team_id if membership is not None else None,
                "assigned_work_country": worker.assigned_work_country,
            },
        )
    for trip in source["trips"]:
        specs[f"trip:{trip.id}"] = _evidence(
            "trip_record",
            "trip",
            trip.id,
            f"{trip.id} trip record",
            {
                "trip_id": trip.id,
                "worker_id": trip.worker_id,
                "origin_country": trip.origin_country,
                "destination_country": trip.destination_country,
                "departure_date": trip.departure_date.isoformat(),
                "booking_date": trip.booking_date.isoformat() if trip.booking_date else None,
                "booking_status": trip.booking_status,
            },
        )
    for record in source["training_records"]:
        specs[f"training:{record.id}"] = _evidence(
            "training_record",
            "training_record",
            record.id,
            f"{record.worker_id} training record",
            {
                "training_record_id": record.id,
                "worker_id": record.worker_id,
                "course_identifier": record.course_identifier,
                "completion_status": record.completion_status,
                "completion_date": (
                    record.completion_date.isoformat() if record.completion_date else None
                ),
            },
        )
    for team in source["teams"]:
        specs[f"team:{team.id}"] = _evidence(
            "team_record",
            "team",
            team.id,
            f"{team.name} team record",
            {
                "team_id": team.id,
                "name": team.name,
                "manager_worker_id": team.manager_worker_id,
            },
        )
    for membership in source["team_memberships"]:
        specs[f"team_membership:{membership.id}"] = _evidence(
            "team_membership_record",
            "worker_team_membership",
            membership.id,
            f"{membership.worker_id} team membership",
            {
                "membership_id": membership.id,
                "worker_id": membership.worker_id,
                "team_id": membership.team_id,
            },
        )
    for system in source["systems"]:
        specs[f"system:{system.id}"] = _evidence(
            "enterprise_system_record",
            "enterprise_system",
            system.id,
            f"{system.name} system record",
            {
                "system_id": system.id,
                "name": system.name,
                "system_type": system.system_type,
                "description": system.description,
                "active": system.active,
            },
        )
    for document in source["documents"]:
        specs[f"document:{document.id}"] = _evidence(
            "enterprise_document_record",
            "enterprise_document",
            document.id,
            f"{document.title} document record",
            {
                "document_id": document.id,
                "title": document.title,
                "document_type": document.document_type,
                "source_system": document.source_system,
                "version": document.version,
                "status": document.status,
            },
        )
    for course in source["courses"]:
        specs[f"course:{course.id}"] = _evidence(
            "training_course_record",
            "training_course",
            course.id,
            f"{course.name} course record",
            {
                "course_id": course.id,
                "course_code": course.course_code,
                "name": course.name,
                "active": course.active,
            },
        )
    for dependency in source["system_dependencies"]:
        specs[f"policy_system_dependency:{dependency.id}"] = _evidence(
            "policy_dependency",
            "policy_system_dependency",
            dependency.id,
            f"{dependency.rule_code} system dependency",
            {
                "dependency_id": dependency.id,
                "policy_change_id": dependency.policy_change_id,
                "rule_code": dependency.rule_code,
                "system_id": dependency.system_id,
                "relationship_type": dependency.relationship_type,
                "explanation": dependency.explanation,
            },
        )
    for dependency in source["document_dependencies"]:
        specs[f"policy_document_dependency:{dependency.id}"] = _evidence(
            "policy_dependency",
            "policy_document_dependency",
            dependency.id,
            f"{dependency.rule_code} document dependency",
            {
                "dependency_id": dependency.id,
                "policy_change_id": dependency.policy_change_id,
                "rule_code": dependency.rule_code,
                "document_id": dependency.document_id,
                "relationship_type": dependency.relationship_type,
                "impact_classification": dependency.impact_classification,
                "explanation": dependency.explanation,
            },
        )
    for dependency in source["training_dependencies"]:
        specs[f"policy_training_dependency:{dependency.id}"] = _evidence(
            "policy_dependency",
            "policy_training_dependency",
            dependency.id,
            f"{dependency.rule_code} training dependency",
            {
                "dependency_id": dependency.id,
                "policy_change_id": dependency.policy_change_id,
                "rule_code": dependency.rule_code,
                "course_id": dependency.course_id,
                "relationship_type": dependency.relationship_type,
                "explanation": dependency.explanation,
            },
        )
    for commitment in source["commitments"]:
        specs[f"commitment:{commitment.id}"] = _evidence(
            "customer_commitment_record",
            "customer_commitment",
            commitment.id,
            f"{commitment.customer_name} commitment",
            {
                "commitment_id": commitment.id,
                "customer_name": commitment.customer_name,
                "commitment_type": commitment.commitment_type,
                "description": commitment.description,
                "start_date": commitment.start_date.isoformat(),
                "end_date": commitment.end_date.isoformat(),
                "status": commitment.status,
            },
        )
    for assignment in source["commitment_assignments"]:
        specs[f"commitment_assignment:{assignment.id}"] = _evidence(
            "commitment_assignment_record",
            "commitment_assignment",
            assignment.id,
            f"{assignment.worker_id} commitment assignment",
            {
                "assignment_id": assignment.id,
                "commitment_id": assignment.commitment_id,
                "worker_id": assignment.worker_id,
                "assignment_role": assignment.assignment_role,
                "required": assignment.required,
            },
        )

    policy_snapshot = {
        "policy_id": policy_record.id,
        "title": policy_record.title,
        "version": policy_record.version,
        "effective_date": policy_record.effective_date.isoformat(),
        "policy_text": policy_record.policy_text,
    }
    rules = policy_record.structured_rules
    policy_specs = {
        "worker_scope": ("Policy worker-scope rule", rules["worker_scope"]),
        "destination_scope": ("Policy destination-scope rule", rules["trip_scope"]),
        "effective_date": (
            "Policy effective-date rule",
            {"effective_date": policy_record.effective_date.isoformat()},
        ),
        "manager_approval": ("Policy manager-approval rule", rules["manager_approval"]),
        "booking_exception": ("Policy booking-date exception", rules["manager_approval"]),
        "security_training": ("Policy security-training rule", rules["security_training"]),
    }
    for suffix, (label, rule_snapshot) in policy_specs.items():
        specs[f"policy:{policy_record.id}:{suffix}"] = _evidence(
            "policy_rule",
            "policy_change",
            policy_record.id,
            label,
            {**policy_snapshot, "rule": rule_snapshot},
        )
    return specs


def _evidence(
    evidence_type: str,
    source_type: str,
    source_id: str,
    label: str,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    return {
        "evidence_type": evidence_type,
        "source_type": source_type,
        "source_id": source_id,
        "label": label,
        "snapshot": snapshot,
    }


def _enterprise_context(source: dict[str, list[Any]]) -> EnterpriseContextInput:
    return EnterpriseContextInput(
        teams=tuple(
            TeamInput(id=item.id, name=item.name, manager_worker_id=item.manager_worker_id)
            for item in source["teams"]
        ),
        team_memberships=tuple(
            TeamMembershipInput(
                id=item.id,
                worker_id=item.worker_id,
                team_id=item.team_id,
            )
            for item in source["team_memberships"]
        ),
        systems=tuple(
            EnterpriseSystemInput(
                id=item.id,
                name=item.name,
                system_type=item.system_type,
                description=item.description,
                active=item.active,
            )
            for item in source["systems"]
        ),
        documents=tuple(
            EnterpriseDocumentInput(
                id=item.id,
                title=item.title,
                document_type=item.document_type,
                source_system=item.source_system,
                version=item.version,
                status=item.status,
            )
            for item in source["documents"]
        ),
        courses=tuple(
            TrainingCourseInput(
                id=item.id,
                course_code=item.course_code,
                name=item.name,
                active=item.active,
            )
            for item in source["courses"]
        ),
        system_dependencies=tuple(
            PolicySystemDependencyInput(
                id=item.id,
                rule_code=item.rule_code,
                system_id=item.system_id,
                relationship_type=item.relationship_type,
                explanation=item.explanation,
            )
            for item in source["system_dependencies"]
        ),
        document_dependencies=tuple(
            PolicyDocumentDependencyInput(
                id=item.id,
                rule_code=item.rule_code,
                document_id=item.document_id,
                relationship_type=item.relationship_type,
                impact_classification=item.impact_classification,
                explanation=item.explanation,
            )
            for item in source["document_dependencies"]
        ),
        training_dependencies=tuple(
            PolicyTrainingDependencyInput(
                id=item.id,
                rule_code=item.rule_code,
                course_id=item.course_id,
                relationship_type=item.relationship_type,
                explanation=item.explanation,
            )
            for item in source["training_dependencies"]
        ),
        commitments=tuple(
            CustomerCommitmentInput(
                id=item.id,
                customer_name=item.customer_name,
                commitment_type=item.commitment_type,
                description=item.description,
                start_date=item.start_date,
                end_date=item.end_date,
                status=item.status,
            )
            for item in source["commitments"]
        ),
        commitment_assignments=tuple(
            CommitmentAssignmentInput(
                id=item.id,
                commitment_id=item.commitment_id,
                worker_id=item.worker_id,
                assignment_role=item.assignment_role,
                required=item.required,
            )
            for item in source["commitment_assignments"]
        ),
        questions=tuple(
            QuestionInput(id=item.id, sequence=item.sequence, question=item.question)
            for item in source["questions"]
        ),
    )


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


def _worker_input(
    worker: Worker,
    membership: WorkerTeamMembership | None,
) -> WorkerInput:
    return WorkerInput(
        id=worker.id,
        full_name=worker.full_name,
        worker_type=worker.worker_type,
        department=worker.department,
        manager_name=worker.manager_name,
        assigned_work_country=worker.assigned_work_country,
        manager_worker_id=worker.manager_worker_id,
        team_id=membership.team_id if membership is not None else None,
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


# Compatibility alias for focused fingerprint tests and existing internal callers.
def _input_fingerprint(
    policy: PolicyInput,
    workers: list[WorkerInput],
    trips: list[TripInput],
    training: list[TrainingInput],
    context: EnterpriseContextInput,
) -> str:
    return calculate_input_fingerprint(
        analyzer_version=ANALYZER_VERSION,
        policy=policy,
        workers=workers,
        trips=trips,
        training_records=training,
        context=context,
    )
