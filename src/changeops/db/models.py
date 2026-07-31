import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
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
    course_identifier: Mapped[str] = mapped_column(String(100))
    completion_status: Mapped[str] = mapped_column(String(30))
    completion_date: Mapped[date | None] = mapped_column(Date)


class PolicyChange(Base):
    __tablename__ = "policy_changes"

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


class ImpactAssessment(Base):
    __tablename__ = "impact_assessments"
    __table_args__ = (CheckConstraint("status = 'completed'", name="ck_impact_assessments_status"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
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
    proposed_actions: Mapped[list["ProposedAction"]] = relationship(
        order_by="ProposedAction.action_key",
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


class ProposedAction(Base):
    __tablename__ = "proposed_actions"
    __table_args__ = (
        CheckConstraint(
            "execution_status = 'not_executed'",
            name="ck_proposed_actions_execution_status",
        ),
        UniqueConstraint(
            "assessment_id",
            "action_key",
            name="uq_proposed_actions_assessment_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("impact_assessments.id"),
        index=True,
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("findings.id"), index=True)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"), index=True)
    action_key: Mapped[str] = mapped_column(String(200))
    action_type: Mapped[str] = mapped_column(String(100))
    target_type: Mapped[str] = mapped_column(String(50))
    target_identifier: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    due_date: Mapped[date | None] = mapped_column(Date)
    execution_status: Mapped[str] = mapped_column(String(30), default="not_executed")

    worker: Mapped[Worker] = relationship()
    finding: Mapped[Finding] = relationship()


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
