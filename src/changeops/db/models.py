import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from changeops.db.base import Base

finding_evidence = Table(
    "finding_evidence",
    Base.metadata,
    Column(
        "finding_id",
        ForeignKey("findings.id"),
        primary_key=True,
    ),
    Column(
        "evidence_id",
        ForeignKey("evidence.id"),
        primary_key=True,
    ),
)

assessment_impact_evidence = Table(
    "assessment_impact_evidence",
    Base.metadata,
    Column(
        "impact_id",
        ForeignKey("assessment_enterprise_impacts.id"),
        primary_key=True,
    ),
    Column(
        "evidence_id",
        ForeignKey("evidence.id"),
        primary_key=True,
    ),
)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    industry: Mapped[str | None] = mapped_column(String(100))
    headquarters: Mapped[str | None] = mapped_column(String(200))


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"),
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(200))
    worker_type: Mapped[str] = mapped_column(String(30))
    department: Mapped[str] = mapped_column(String(100))
    manager_name: Mapped[str] = mapped_column(String(200))
    assigned_work_country: Mapped[str] = mapped_column(String(2))
    manager_worker_id: Mapped[str | None] = mapped_column(
        ForeignKey("workers.id"),
        index=True,
    )

    manager: Mapped["Worker | None"] = relationship(
        remote_side=[id],
        foreign_keys=[manager_worker_id],
    )


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200))
    manager_worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), index=True)

    manager: Mapped[Worker] = relationship(foreign_keys=[manager_worker_id])


class WorkerTeamMembership(Base):
    __tablename__ = "worker_team_memberships"
    __table_args__ = (UniqueConstraint("worker_id", name="uq_worker_team_memberships_worker"),)

    id: Mapped[str] = mapped_column(String(150), primary_key=True)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), index=True)
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"), index=True)


class EnterpriseSystem(Base):
    __tablename__ = "enterprise_systems"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200))
    system_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean)


class EnterpriseDocument(Base):
    __tablename__ = "enterprise_documents"
    __table_args__ = (
        CheckConstraint(
            "document_type IN ('policy', 'procedure', 'guide', 'knowledge_article')",
            name="ck_enterprise_documents_type",
        ),
        CheckConstraint(
            "status IN ('published', 'draft', 'archived')",
            name="ck_enterprise_documents_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300))
    document_type: Mapped[str] = mapped_column(String(30))
    source_system: Mapped[str] = mapped_column(String(100))
    version: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30))


class TrainingCourse(Base):
    __tablename__ = "training_courses"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"),
        index=True,
    )
    course_code: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean)


class Trip(Base):
    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint(
            "booking_status IN ('planned', 'booked')",
            name="ck_trips_booking_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), index=True)
    origin_country: Mapped[str] = mapped_column(String(2))
    destination_country: Mapped[str] = mapped_column(String(2))
    departure_date: Mapped[date] = mapped_column(Date)
    booking_date: Mapped[date | None] = mapped_column(Date)
    booking_status: Mapped[str] = mapped_column(String(20))


class TrainingRecord(Base):
    __tablename__ = "training_records"
    __table_args__ = (
        CheckConstraint(
            "completion_status IN ('completed', 'not_completed')",
            name="ck_training_records_completion_status",
        ),
        UniqueConstraint(
            "worker_id",
            "course_identifier",
            name="uq_training_records_worker_course",
        ),
    )

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), index=True)
    course_identifier: Mapped[str] = mapped_column(
        ForeignKey("training_courses.id"),
        index=True,
    )
    completion_status: Mapped[str] = mapped_column(String(30))
    completion_date: Mapped[date | None] = mapped_column(Date)

    course: Mapped[TrainingCourse] = relationship()


class PolicyChange(Base):
    __tablename__ = "policy_changes"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "organization_id",
            name="uq_policy_changes_id_organization",
        ),
    )

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300))
    owner: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(50))
    effective_date: Mapped[date] = mapped_column(Date)
    policy_text: Mapped[str] = mapped_column(Text)
    structured_rules: Mapped[dict[str, Any]] = mapped_column(JSONB)


class PolicyExtractionAttempt(Base):
    __tablename__ = "policy_extraction_attempts"
    __table_args__ = (
        CheckConstraint(
            "support_status IS NULL OR support_status IN ('supported', 'unsupported')",
            name="ck_policy_extraction_attempts_support_status",
        ),
        CheckConstraint(
            "validation_outcome IN ('accepted', 'unsupported', 'validation_failed')",
            name="ck_policy_extraction_attempts_validation_outcome",
        ),
        UniqueConstraint(
            "id",
            "policy_change_id",
            name="uq_policy_extraction_attempts_id_policy",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_analysis_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("policy_analysis_runs.id"),
        index=True,
    )
    retry_reason: Mapped[str | None] = mapped_column(String(100))
    policy_change_id: Mapped[str] = mapped_column(
        ForeignKey("policy_changes.id"),
        index=True,
    )
    policy_text_snapshot: Mapped[str] = mapped_column(Text)
    support_status: Mapped[str | None] = mapped_column(String(30))
    validation_outcome: Mapped[str] = mapped_column(String(30))
    model_provider: Mapped[str] = mapped_column(String(100))
    model_identifier: Mapped[str] = mapped_column(String(200))
    prompt_version: Mapped[str] = mapped_column(String(100))
    schema_version: Mapped[str] = mapped_column(String(100))
    raw_output: Mapped[Any | None] = mapped_column(JSONB)
    parsed_output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    candidate_rules: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    accepted_rules: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    provenance: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    findings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    validation_errors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PolicyAnalysisRun(Base):
    __tablename__ = "policy_analysis_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN "
            "('pending', 'running', 'awaiting_clarification', 'completed', "
            "'unsupported', 'failed')",
            name="ck_policy_analysis_runs_status",
        ),
        CheckConstraint(
            "current_step IN "
            "('initialize', 'extract', 'evaluate_extraction', "
            "'evaluate_clarification', 'await_clarification', "
            "'create_assessment', 'finalize', 'terminal')",
            name="ck_policy_analysis_runs_current_step",
        ),
        CheckConstraint("retry_count >= 0", name="ck_policy_analysis_runs_retry_count"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"),
        index=True,
    )
    policy_change_id: Mapped[str] = mapped_column(
        ForeignKey("policy_changes.id"),
        index=True,
    )
    policy_text_snapshot: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30))
    current_step: Mapped[str] = mapped_column(String(40))
    latest_extraction_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("policy_extraction_attempts.id"),
    )
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("impact_assessments.id"),
    )
    retry_count: Mapped[int] = mapped_column(Integer)
    failure_code: Mapped[str | None] = mapped_column(String(100))
    failure_detail: Mapped[str | None] = mapped_column(Text)
    workflow_version: Mapped[str] = mapped_column(String(100))
    model_provider: Mapped[str] = mapped_column(String(100))
    model_identifier: Mapped[str] = mapped_column(String(200))
    prompt_version: Mapped[str] = mapped_column(String(100))
    schema_version: Mapped[str] = mapped_column(String(100))
    accepted_rule_provenance: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    clarifications: Mapped[list["PolicyAnalysisClarification"]] = relationship(
        order_by="PolicyAnalysisClarification.created_at",
    )


class PolicyAnalysisClarification(Base):
    __tablename__ = "policy_analysis_clarifications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'answered', 'superseded')",
            name="ck_policy_analysis_clarifications_status",
        ),
        UniqueConstraint(
            "policy_analysis_run_id",
            "question_code",
            name="uq_policy_analysis_clarifications_run_question",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("policy_analysis_runs.id"),
        index=True,
    )
    question_code: Mapped[str] = mapped_column(String(100))
    question_text: Mapped[str] = mapped_column(Text)
    expected_answer_contract: Mapped[dict[str, Any]] = mapped_column(JSONB)
    affected_fields: Mapped[list[str]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(30))
    answer: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    responder_identity: Mapped[str | None] = mapped_column(String(200))
    answer_provenance: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PolicyComparison(Base):
    __tablename__ = "policy_comparisons"
    __table_args__ = (
        CheckConstraint(
            "baseline_policy_change_id <> proposed_policy_change_id",
            name="ck_policy_comparisons_distinct_policies",
        ),
        CheckConstraint(
            "comparison_contract_version = 'international-travel-policy-comparison-v1'",
            name="ck_policy_comparisons_contract_version",
        ),
        CheckConstraint(
            "length(comparison_fingerprint) = 64",
            name="ck_policy_comparisons_fingerprint_length",
        ),
        CheckConstraint(
            "length(btrim(created_by)) > 0",
            name="ck_policy_comparisons_creator",
        ),
        UniqueConstraint(
            "comparison_fingerprint",
            name="uq_policy_comparisons_fingerprint",
        ),
        ForeignKeyConstraint(
            ["baseline_policy_change_id", "organization_id"],
            ["policy_changes.id", "policy_changes.organization_id"],
            name="fk_policy_comparisons_baseline_policy_organization",
        ),
        ForeignKeyConstraint(
            ["proposed_policy_change_id", "organization_id"],
            ["policy_changes.id", "policy_changes.organization_id"],
            name="fk_policy_comparisons_proposed_policy_organization",
        ),
        ForeignKeyConstraint(
            ["baseline_extraction_attempt_id", "baseline_policy_change_id"],
            ["policy_extraction_attempts.id", "policy_extraction_attempts.policy_change_id"],
            name="fk_policy_comparisons_baseline_attempt_policy",
        ),
        ForeignKeyConstraint(
            ["proposed_extraction_attempt_id", "proposed_policy_change_id"],
            ["policy_extraction_attempts.id", "policy_extraction_attempts.policy_change_id"],
            name="fk_policy_comparisons_proposed_attempt_policy",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"),
        index=True,
    )
    baseline_policy_change_id: Mapped[str] = mapped_column(String(100), index=True)
    proposed_policy_change_id: Mapped[str] = mapped_column(String(100), index=True)
    baseline_extraction_attempt_id: Mapped[uuid.UUID] = mapped_column(index=True)
    proposed_extraction_attempt_id: Mapped[uuid.UUID] = mapped_column(index=True)
    baseline_policy_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    proposed_policy_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    comparison_contract_version: Mapped[str] = mapped_column(String(100))
    comparison_fingerprint: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    differences: Mapped[list["PolicyComparisonDifference"]] = relationship(
        order_by="PolicyComparisonDifference.sequence",
    )


class PolicyComparisonDifference(Base):
    __tablename__ = "policy_comparison_differences"
    __table_args__ = (
        CheckConstraint(
            "change_type IN ('added', 'removed', 'modified')",
            name="ck_policy_comparison_differences_change_type",
        ),
        CheckConstraint(
            "sequence > 0",
            name="ck_policy_comparison_differences_sequence",
        ),
        CheckConstraint(
            "material",
            name="ck_policy_comparison_differences_material",
        ),
        UniqueConstraint(
            "policy_comparison_id",
            "sequence",
            name="uq_policy_comparison_differences_sequence",
        ),
        UniqueConstraint(
            "policy_comparison_id",
            "rule_identity",
            name="uq_policy_comparison_differences_identity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_comparison_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("policy_comparisons.id"),
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer)
    rule_identity: Mapped[str] = mapped_column(String(300))
    field_path: Mapped[str] = mapped_column(String(200))
    change_type: Mapped[str] = mapped_column(String(20))
    baseline_value: Mapped[Any | None] = mapped_column(JSONB(none_as_null=True))
    proposed_value: Mapped[Any | None] = mapped_column(JSONB(none_as_null=True))
    material: Mapped[bool] = mapped_column(Boolean)
    reason_code: Mapped[str] = mapped_column(String(100))
    baseline_provenance: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    proposed_provenance: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))


class PolicyChangeQuestion(Base):
    __tablename__ = "policy_change_questions"
    __table_args__ = (
        UniqueConstraint(
            "policy_change_id",
            "sequence",
            name="uq_policy_change_questions_policy_sequence",
        ),
    )

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    policy_change_id: Mapped[str] = mapped_column(
        ForeignKey("policy_changes.id"),
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(Text)


class PolicySystemDependency(Base):
    __tablename__ = "policy_system_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "policy_change_id",
            "rule_code",
            "system_id",
            name="uq_policy_system_dependencies_target",
        ),
    )

    id: Mapped[str] = mapped_column(String(150), primary_key=True)
    policy_change_id: Mapped[str] = mapped_column(
        ForeignKey("policy_changes.id"),
        index=True,
    )
    rule_code: Mapped[str] = mapped_column(String(100))
    system_id: Mapped[str] = mapped_column(ForeignKey("enterprise_systems.id"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(100))
    explanation: Mapped[str] = mapped_column(Text)


class PolicyDocumentDependency(Base):
    __tablename__ = "policy_document_dependencies"
    __table_args__ = (
        CheckConstraint(
            "impact_classification IN ('review_required', 'update_required')",
            name="ck_policy_document_dependencies_classification",
        ),
        UniqueConstraint(
            "policy_change_id",
            "rule_code",
            "document_id",
            name="uq_policy_document_dependencies_target",
        ),
    )

    id: Mapped[str] = mapped_column(String(150), primary_key=True)
    policy_change_id: Mapped[str] = mapped_column(
        ForeignKey("policy_changes.id"),
        index=True,
    )
    rule_code: Mapped[str] = mapped_column(String(100))
    document_id: Mapped[str] = mapped_column(
        ForeignKey("enterprise_documents.id"),
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(String(100))
    impact_classification: Mapped[str] = mapped_column(String(30))
    explanation: Mapped[str] = mapped_column(Text)


class PolicyTrainingDependency(Base):
    __tablename__ = "policy_training_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "policy_change_id",
            "rule_code",
            "course_id",
            name="uq_policy_training_dependencies_target",
        ),
    )

    id: Mapped[str] = mapped_column(String(150), primary_key=True)
    policy_change_id: Mapped[str] = mapped_column(
        ForeignKey("policy_changes.id"),
        index=True,
    )
    rule_code: Mapped[str] = mapped_column(String(100))
    course_id: Mapped[str] = mapped_column(ForeignKey("training_courses.id"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(100))
    explanation: Mapped[str] = mapped_column(Text)


class CustomerCommitment(Base):
    __tablename__ = "customer_commitments"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="ck_customer_commitments_dates"),
        CheckConstraint(
            "status IN ('active', 'completed', 'cancelled')",
            name="ck_customer_commitments_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id"),
        index=True,
    )
    customer_name: Mapped[str] = mapped_column(String(200))
    commitment_type: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30))


class CommitmentAssignment(Base):
    __tablename__ = "commitment_assignments"
    __table_args__ = (
        UniqueConstraint(
            "commitment_id",
            "worker_id",
            "assignment_role",
            name="uq_commitment_assignments_worker_role",
        ),
    )

    id: Mapped[str] = mapped_column(String(150), primary_key=True)
    commitment_id: Mapped[str] = mapped_column(
        ForeignKey("customer_commitments.id"),
        index=True,
    )
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), index=True)
    assignment_role: Mapped[str] = mapped_column(String(100))
    required: Mapped[bool] = mapped_column(Boolean)


class ImpactAssessment(Base):
    __tablename__ = "impact_assessments"
    __table_args__ = (
        CheckConstraint("status = 'completed'", name="ck_impact_assessments_status"),
        UniqueConstraint(
            "policy_analysis_run_id",
            name="uq_impact_assessments_policy_analysis_run",
        ),
        UniqueConstraint(
            "id",
            "policy_analysis_run_id",
            name="uq_impact_assessments_id_policy_analysis_run",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_analysis_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("policy_analysis_runs.id"),
        index=True,
    )
    policy_change_id: Mapped[str] = mapped_column(
        ForeignKey("policy_changes.id"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(30))
    analyzer_version: Mapped[str] = mapped_column(String(100))
    input_fingerprint: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    worker_results: Mapped[list["AssessmentWorkerResult"]] = relationship(
        order_by="AssessmentWorkerResult.worker_id",
    )
    findings: Mapped[list["Finding"]] = relationship(order_by="Finding.rule_code")
    evidence: Mapped[list["Evidence"]] = relationship(order_by="Evidence.evidence_key")
    proposed_actions: Mapped[list["ProposedAction"]] = relationship()
    enterprise_impacts: Mapped[list["AssessmentEnterpriseImpact"]] = relationship(
        order_by="AssessmentEnterpriseImpact.sort_key",
    )
    unresolved_questions: Mapped[list["AssessmentUnresolvedQuestion"]] = relationship(
        order_by="AssessmentUnresolvedQuestion.sequence",
    )


class AssessmentWorkerResult(Base):
    __tablename__ = "assessment_worker_results"
    __table_args__ = (
        CheckConstraint(
            "classification IN ('affected', 'unaffected')",
            name="ck_assessment_worker_results_classification",
        ),
        UniqueConstraint(
            "assessment_id",
            "trip_id",
            name="uq_assessment_worker_results_assessment_trip",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("impact_assessments.id"),
        index=True,
    )
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), index=True)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id"), index=True)
    classification: Mapped[str] = mapped_column(String(20))
    explanation: Mapped[str] = mapped_column(Text)
    reason_codes: Mapped[list[str]] = mapped_column(JSONB)

    worker: Mapped[Worker] = relationship()
    trip: Mapped[Trip] = relationship()


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("impact_assessments.id"),
        index=True,
    )
    worker_result_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_worker_results.id"),
        index=True,
    )
    finding_type: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(30))
    rule_code: Mapped[str] = mapped_column(String(100))
    explanation: Mapped[str] = mapped_column(Text)

    worker_result: Mapped[AssessmentWorkerResult] = relationship()
    evidence: Mapped[list["Evidence"]] = relationship(
        secondary=finding_evidence,
        order_by="Evidence.evidence_key",
    )


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            "evidence_key",
            name="uq_evidence_assessment_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("impact_assessments.id"),
        index=True,
    )
    evidence_key: Mapped[str] = mapped_column(String(200))
    evidence_type: Mapped[str] = mapped_column(String(50))
    source_type: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[str] = mapped_column(String(150))
    label: Mapped[str] = mapped_column(String(300))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)


class AssessmentEnterpriseImpact(Base):
    __tablename__ = "assessment_enterprise_impacts"
    __table_args__ = (
        CheckConstraint(
            "domain IN "
            "('people', 'teams', 'systems', 'documents', 'training', "
            "'customer_commitments')",
            name="ck_assessment_enterprise_impacts_domain",
        ),
        CheckConstraint(
            "classification IN "
            "('directly_affected', 'operationally_affected', 'review_required', "
            "'update_required', 'notification_required')",
            name="ck_assessment_enterprise_impacts_classification",
        ),
        UniqueConstraint(
            "assessment_id",
            "domain",
            "source_key",
            "reason_code",
            name="uq_assessment_enterprise_impacts_semantic",
        ),
        UniqueConstraint(
            "assessment_id",
            "sort_key",
            name="uq_assessment_enterprise_impacts_sort_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("impact_assessments.id"),
        index=True,
    )
    domain: Mapped[str] = mapped_column(String(30))
    object_type: Mapped[str] = mapped_column(String(50))
    source_key: Mapped[str] = mapped_column(String(200))
    display_name: Mapped[str] = mapped_column(String(300))
    classification: Mapped[str] = mapped_column(String(40))
    explanation: Mapped[str] = mapped_column(Text)
    reason_code: Mapped[str] = mapped_column(String(120))
    sort_key: Mapped[str] = mapped_column(String(400))

    evidence: Mapped[list[Evidence]] = relationship(
        secondary=assessment_impact_evidence,
        order_by="Evidence.evidence_key",
    )
    path_elements: Mapped[list["AssessmentImpactPathElement"]] = relationship(
        order_by="AssessmentImpactPathElement.sequence",
    )


class AssessmentImpactPathElement(Base):
    __tablename__ = "assessment_impact_path_elements"
    __table_args__ = (
        UniqueConstraint(
            "impact_id",
            "sequence",
            name="uq_assessment_impact_path_elements_sequence",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    impact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assessment_enterprise_impacts.id"),
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer)
    object_type: Mapped[str] = mapped_column(String(50))
    stable_key: Mapped[str] = mapped_column(String(200))
    display_label: Mapped[str] = mapped_column(String(300))
    relationship_to_next: Mapped[str | None] = mapped_column(String(100))


class ProposedAction(Base):
    __tablename__ = "proposed_actions"
    __table_args__ = (
        CheckConstraint(
            "execution_status = 'not_executed'",
            name="ck_proposed_actions_execution_status",
        ),
        CheckConstraint(
            "finding_id IS NOT NULL OR enterprise_impact_id IS NOT NULL",
            name="ck_proposed_actions_has_parent",
        ),
        UniqueConstraint(
            "id",
            "assessment_id",
            name="uq_proposed_actions_id_assessment",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("impact_assessments.id"),
        index=True,
    )
    finding_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("findings.id"), index=True)
    enterprise_impact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assessment_enterprise_impacts.id"),
        index=True,
    )
    worker_id: Mapped[str | None] = mapped_column(ForeignKey("workers.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(100))
    target_type: Mapped[str] = mapped_column(String(50))
    target_identifier: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    due_date: Mapped[date | None] = mapped_column(Date)
    execution_status: Mapped[str] = mapped_column(String(30), default="not_executed")

    worker: Mapped[Worker | None] = relationship()
    finding: Mapped[Finding | None] = relationship()
    enterprise_impact: Mapped[AssessmentEnterpriseImpact | None] = relationship()


class ActionReview(Base):
    __tablename__ = "action_reviews"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'deferred', 'revision_requested')",
            name="ck_action_reviews_status",
        ),
        CheckConstraint(
            "(status = 'pending' AND completed_at IS NULL) OR "
            "(status <> 'pending' AND completed_at IS NOT NULL)",
            name="ck_action_reviews_completion",
        ),
        UniqueConstraint("proposed_action_id", name="uq_action_reviews_proposed_action"),
        UniqueConstraint(
            "id",
            "proposed_action_id",
            "assessment_id",
            name="uq_action_reviews_id_action_assessment",
        ),
        ForeignKeyConstraint(
            ["proposed_action_id", "assessment_id"],
            ["proposed_actions.id", "proposed_actions.assessment_id"],
            name="fk_action_reviews_action_assessment",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("impact_assessments.id"),
        index=True,
    )
    proposed_action_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("proposed_actions.id"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(30))
    original_action_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    review_context_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    decisions: Mapped[list["ActionReviewDecision"]] = relationship(
        order_by="ActionReviewDecision.created_at",
    )


class ActionReviewDecision(Base):
    __tablename__ = "action_review_decisions"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved', 'rejected', 'deferred', 'revision_requested')",
            name="ck_action_review_decisions_decision",
        ),
        CheckConstraint(
            "(decision = 'approved') OR edited_action_snapshot IS NULL",
            name="ck_action_review_decisions_approved_edit",
        ),
        UniqueConstraint("action_review_id", name="uq_action_review_decisions_review"),
        UniqueConstraint(
            "id",
            "action_review_id",
            name="uq_action_review_decisions_id_review",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    action_review_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("action_reviews.id"),
        index=True,
    )
    decision: Mapped[str] = mapped_column(String(30))
    reviewer_identity: Mapped[str] = mapped_column(String(200))
    reviewer_role: Mapped[str] = mapped_column(String(30))
    rationale: Mapped[str] = mapped_column(Text)
    edited_action_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ActionApprovalRun(Base):
    __tablename__ = "action_approval_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('initializing', 'awaiting_decisions', 'completed', 'failed')",
            name="ck_action_approval_runs_status",
        ),
        CheckConstraint(
            "current_step IN ('create_reviews', 'evaluate_reviews', 'await_decisions', 'finalize')",
            name="ck_action_approval_runs_current_step",
        ),
        CheckConstraint(
            "total_action_count >= 0 AND pending_count >= 0 AND approved_count >= 0 "
            "AND rejected_count >= 0 AND deferred_count >= 0 "
            "AND revision_requested_count >= 0",
            name="ck_action_approval_runs_nonnegative_counts",
        ),
        CheckConstraint(
            "total_action_count = pending_count + approved_count + rejected_count "
            "+ deferred_count + revision_requested_count",
            name="ck_action_approval_runs_count_total",
        ),
        CheckConstraint(
            "(status = 'awaiting_decisions' AND pending_count > 0) "
            "OR status <> 'awaiting_decisions'",
            name="ck_action_approval_runs_awaiting_pending",
        ),
        CheckConstraint(
            "(status = 'completed' AND pending_count = 0 AND completed_at IS NOT NULL) "
            "OR (status <> 'completed' AND completed_at IS NULL)",
            name="ck_action_approval_runs_completion",
        ),
        UniqueConstraint("assessment_id", name="uq_action_approval_runs_assessment"),
        UniqueConstraint(
            "id",
            "assessment_id",
            name="uq_action_approval_runs_id_assessment",
        ),
        ForeignKeyConstraint(
            ["assessment_id", "policy_analysis_run_id"],
            ["impact_assessments.id", "impact_assessments.policy_analysis_run_id"],
            name="fk_action_approval_runs_assessment_analysis",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("impact_assessments.id"),
        index=True,
    )
    policy_analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("policy_analysis_runs.id"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(30))
    current_step: Mapped[str] = mapped_column(String(30))
    total_action_count: Mapped[int] = mapped_column(Integer)
    pending_count: Mapped[int] = mapped_column(Integer)
    approved_count: Mapped[int] = mapped_column(Integer)
    rejected_count: Mapped[int] = mapped_column(Integer)
    deferred_count: Mapped[int] = mapped_column(Integer)
    revision_requested_count: Mapped[int] = mapped_column(Integer)
    failure_code: Mapped[str | None] = mapped_column(String(100))
    failure_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list["ActionApprovalRunItem"]] = relationship(
        order_by="ActionApprovalRunItem.sequence",
        primaryjoin="ActionApprovalRun.id == ActionApprovalRunItem.approval_run_id",
        foreign_keys="ActionApprovalRunItem.approval_run_id",
    )
    transitions: Mapped[list["ActionApprovalRunTransition"]] = relationship(
        order_by="ActionApprovalRunTransition.created_at",
    )


class ActionApprovalRunItem(Base):
    __tablename__ = "action_approval_run_items"
    __table_args__ = (
        CheckConstraint("sequence >= 0", name="ck_action_approval_run_items_sequence"),
        UniqueConstraint(
            "approval_run_id",
            "proposed_action_id",
            name="uq_action_approval_run_items_action",
        ),
        UniqueConstraint(
            "approval_run_id",
            "action_review_id",
            name="uq_action_approval_run_items_review",
        ),
        UniqueConstraint(
            "approval_run_id",
            "sequence",
            name="uq_action_approval_run_items_sequence",
        ),
        UniqueConstraint(
            "approval_run_id",
            "action_review_id",
            "proposed_action_id",
            "assessment_id",
            name="uq_action_approval_items_execution_owner",
        ),
        ForeignKeyConstraint(
            ["approval_run_id", "assessment_id"],
            ["action_approval_runs.id", "action_approval_runs.assessment_id"],
            name="fk_action_approval_items_run_assessment",
        ),
        ForeignKeyConstraint(
            ["proposed_action_id", "assessment_id"],
            ["proposed_actions.id", "proposed_actions.assessment_id"],
            name="fk_action_approval_items_action_assessment",
        ),
        ForeignKeyConstraint(
            ["action_review_id", "proposed_action_id", "assessment_id"],
            [
                "action_reviews.id",
                "action_reviews.proposed_action_id",
                "action_reviews.assessment_id",
            ],
            name="fk_action_approval_items_review_action_assessment",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    approval_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("action_approval_runs.id"),
        index=True,
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("impact_assessments.id"),
    )
    proposed_action_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("proposed_actions.id"),
        index=True,
    )
    action_review_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("action_reviews.id"),
        index=True,
    )
    sequence: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    review: Mapped[ActionReview] = relationship(
        primaryjoin="ActionReview.id == ActionApprovalRunItem.action_review_id",
        foreign_keys=[action_review_id],
    )


class ExecutionCommand(Base):
    __tablename__ = "execution_commands"
    __table_args__ = (
        CheckConstraint(
            "status = 'pending_execution'",
            name="ck_execution_commands_status",
        ),
        CheckConstraint(
            "schema_version = 'execution-command-v1'",
            name="ck_execution_commands_schema_version",
        ),
        CheckConstraint(
            "system = 'learning' AND operation = 'assign_training'",
            name="ck_execution_commands_supported_mapping",
        ),
        CheckConstraint(
            "prepared_role = 'admin'",
            name="ck_execution_commands_prepared_role",
        ),
        UniqueConstraint(
            "action_review_id",
            name="uq_execution_commands_action_review",
        ),
        UniqueConstraint(
            "idempotency_key",
            name="uq_execution_commands_idempotency_key",
        ),
        ForeignKeyConstraint(
            [
                "approval_run_id",
                "action_review_id",
                "proposed_action_id",
                "assessment_id",
            ],
            [
                "action_approval_run_items.approval_run_id",
                "action_approval_run_items.action_review_id",
                "action_approval_run_items.proposed_action_id",
                "action_approval_run_items.assessment_id",
            ],
            name="fk_execution_commands_membership",
        ),
        ForeignKeyConstraint(
            ["action_review_decision_id", "action_review_id"],
            ["action_review_decisions.id", "action_review_decisions.action_review_id"],
            name="fk_execution_commands_approval_decision",
        ),
        ForeignKeyConstraint(
            ["action_review_id", "proposed_action_id", "assessment_id"],
            [
                "action_reviews.id",
                "action_reviews.proposed_action_id",
                "action_reviews.assessment_id",
            ],
            name="fk_execution_commands_review_lifecycle",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    approval_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("action_approval_runs.id"),
        index=True,
    )
    action_review_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("action_reviews.id"),
        index=True,
    )
    action_review_decision_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("action_review_decisions.id"),
        index=True,
    )
    proposed_action_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("proposed_actions.id"),
        index=True,
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("impact_assessments.id"),
        index=True,
    )
    schema_version: Mapped[str] = mapped_column(String(50))
    system: Mapped[str] = mapped_column(String(50))
    operation: Mapped[str] = mapped_column(String(100))
    target_type: Mapped[str] = mapped_column(String(50))
    target_identifier: Mapped[str] = mapped_column(String(200))
    parameters_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    effective_action_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    idempotency_key: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30))
    prepared_by: Mapped[str] = mapped_column(String(200))
    prepared_role: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    execution_results: Mapped[list["ExecutionResult"]] = relationship(
        order_by="ExecutionResult.created_at",
    )


class SimulatedLearningAssignment(Base):
    __tablename__ = "simulated_learning_assignments"
    __table_args__ = (
        CheckConstraint(
            "assignment_status = 'assigned'",
            name="ck_simulated_learning_assignments_status",
        ),
        UniqueConstraint(
            "source_execution_command_id",
            name="uq_simulated_learning_assignments_command",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), index=True)
    training_course_id: Mapped[str] = mapped_column(
        ForeignKey("training_courses.id"),
        index=True,
    )
    source_execution_command_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("execution_commands.id"),
        index=True,
    )
    source_approved_action_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("proposed_actions.id"),
        index=True,
    )
    assignment_status: Mapped[str] = mapped_column(String(30))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ExecutionResult(Base):
    __tablename__ = "execution_results"
    __table_args__ = (
        CheckConstraint(
            "status IN "
            "('succeeded', 'already_applied', 'rejected_unsupported', 'failed_validation')",
            name="ck_execution_results_status",
        ),
        CheckConstraint(
            "(status IN ('succeeded', 'already_applied') "
            "AND simulated_learning_assignment_id IS NOT NULL) "
            "OR (status IN ('rejected_unsupported', 'failed_validation') "
            "AND simulated_learning_assignment_id IS NULL)",
            name="ck_execution_results_assignment_outcome",
        ),
        CheckConstraint(
            "attempted_role = 'admin' AND length(btrim(attempted_by)) > 0",
            name="ck_execution_results_attempted_role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    execution_command_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("execution_commands.id"),
        index=True,
    )
    simulated_learning_assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("simulated_learning_assignments.id"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(30))
    outcome_code: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    command_idempotency_key: Mapped[str] = mapped_column(String(64))
    attempted_by: Mapped[str] = mapped_column(String(200))
    attempted_role: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    learning_assignment: Mapped[SimulatedLearningAssignment | None] = relationship()


class ActionApprovalRunTransition(Base):
    __tablename__ = "action_approval_run_transitions"
    __table_args__ = (
        CheckConstraint(
            "trigger_type IN "
            "('run_created', 'initialized', 'decision_recorded', "
            "'manual_resume', 'completed', 'failed')",
            name="ck_action_approval_run_transitions_trigger",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    approval_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("action_approval_runs.id"),
        index=True,
    )
    from_status: Mapped[str | None] = mapped_column(String(30))
    to_status: Mapped[str] = mapped_column(String(30))
    from_step: Mapped[str | None] = mapped_column(String(30))
    to_step: Mapped[str] = mapped_column(String(30))
    reason_code: Mapped[str] = mapped_column(String(100))
    trigger_type: Mapped[str] = mapped_column(String(30))
    trigger_reference: Mapped[str | None] = mapped_column(String(200))
    actor_identity: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AssessmentUnresolvedQuestion(Base):
    __tablename__ = "assessment_unresolved_questions"
    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            "sequence",
            name="uq_assessment_questions_assessment_sequence",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("impact_assessments.id"),
        index=True,
    )
    source_question_id: Mapped[str] = mapped_column(
        ForeignKey("policy_change_questions.id"),
    )
    sequence: Mapped[int] = mapped_column(Integer)
    question: Mapped[str] = mapped_column(Text)


class PolicyInterpretationAttempt(Base):
    __tablename__ = "policy_interpretation_attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('accepted', 'invalid', 'provider_failed')",
            name="ck_policy_interpretation_attempts_status",
        ),
        UniqueConstraint(
            "id",
            "policy_analysis_run_id",
            "impact_assessment_id",
            name="uq_policy_interpretation_attempts_lifecycle",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("policy_analysis_runs.id"), index=True
    )
    impact_assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("impact_assessments.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(30))
    raw_output: Mapped[Any | None] = mapped_column(JSONB)
    candidate_change_plan: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    validated_change_plan: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    validation_errors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    model_provider: Mapped[str] = mapped_column(String(100))
    model_identifier: Mapped[str] = mapped_column(String(200))
    prompt_version: Mapped[str] = mapped_column(String(100))
    schema_version: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(100))
    failure_message: Mapped[str | None] = mapped_column(Text)


class ChangePlan(Base):
    __tablename__ = "change_plans"
    __table_args__ = (
        UniqueConstraint("impact_assessment_id", name="uq_change_plans_impact_assessment"),
        UniqueConstraint("interpretation_attempt_id", name="uq_change_plans_attempt"),
        ForeignKeyConstraint(
            ["impact_assessment_id", "policy_analysis_run_id"],
            ["impact_assessments.id", "impact_assessments.policy_analysis_run_id"],
            name="fk_change_plans_assessment_lifecycle",
        ),
        ForeignKeyConstraint(
            [
                "interpretation_attempt_id",
                "policy_analysis_run_id",
                "impact_assessment_id",
            ],
            [
                "policy_interpretation_attempts.id",
                "policy_interpretation_attempts.policy_analysis_run_id",
                "policy_interpretation_attempts.impact_assessment_id",
            ],
            name="fk_change_plans_attempt_lifecycle",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    policy_analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("policy_analysis_runs.id"), index=True
    )
    impact_assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("impact_assessments.id"), index=True
    )
    interpretation_attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("policy_interpretation_attempts.id")
    )
    schema_version: Mapped[str] = mapped_column(String(100))
    validated_plan: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
