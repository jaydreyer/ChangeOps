import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from changeops.db.models import (
    ActionApprovalRun,
    AssessmentEnterpriseImpact,
    ChangePlan,
    CustomerCommitment,
    EnterpriseDocument,
    EnterpriseSystem,
    Organization,
    PolicyAnalysisRun,
    PolicyChange,
    PolicyExtractionAttempt,
    PolicyInterpretationAttempt,
    Team,
)
from changeops.schemas.policy_analysis_journey import (
    AnalysisJourneyAssessmentResponse,
    AnalysisJourneyExtractionResponse,
    AnalysisJourneyPolicyResponse,
    AnalysisJourneyRunSummaryResponse,
    AnalysisUncertaintyResponse,
    ApprovalRunReferenceResponse,
    EnterpriseCoverageDomainResponse,
    EnterpriseCoverageObjectResponse,
    InterpretationJourneyResponse,
    PolicyAnalysisEntryResponse,
    PolicyAnalysisJourneyResponse,
)
from changeops.schemas.policy_extractions import ExtractionMetadataResponse
from changeops.schemas.policy_interpretation import ChangePlanResponse
from changeops.services.assessment_serializer import serialize_assessment
from changeops.services.assessment_service import get_impact_assessment
from changeops.services.policy_analysis_serializer import serialize_policy_analysis_run
from changeops.services.policy_analysis_service import (
    PolicyAnalysisRunNotFoundError,
    get_policy_analysis_run,
)


class PolicyAnalysisJourneyNotFoundError(Exception):
    pass


def get_policy_analysis_entry(session: Session) -> PolicyAnalysisEntryResponse:
    policies = list(
        session.scalars(
            select(PolicyChange)
            .join(Organization, Organization.id == PolicyChange.organization_id)
            .order_by(PolicyChange.effective_date.desc(), PolicyChange.id)
        )
    )
    organizations = {
        item.id: item
        for item in session.scalars(
            select(Organization).where(
                Organization.id.in_({policy.organization_id for policy in policies})
            )
        )
    }
    runs = list(
        session.scalars(
            select(PolicyAnalysisRun)
            .order_by(PolicyAnalysisRun.created_at.desc(), PolicyAnalysisRun.id.desc())
            .limit(10)
        )
    )
    return PolicyAnalysisEntryResponse(
        policies=[
            _serialize_policy(policy, organizations[policy.organization_id]) for policy in policies
        ],
        recent_runs=[
            AnalysisJourneyRunSummaryResponse(
                id=run.id,
                policy_change_id=run.policy_change_id,
                status=run.status,
                current_step=run.current_step,
                assessment_id=run.assessment_id,
                created_at=run.created_at,
                updated_at=run.updated_at,
            )
            for run in runs
        ],
    )


def get_policy_analysis_journey(
    session: Session, run_id: uuid.UUID
) -> PolicyAnalysisJourneyResponse:
    try:
        run = get_policy_analysis_run(session, run_id)
    except PolicyAnalysisRunNotFoundError as error:
        raise PolicyAnalysisJourneyNotFoundError(str(run_id)) from error
    policy = session.get(PolicyChange, run.policy_change_id)
    organization = session.get(Organization, run.organization_id)
    if policy is None or organization is None:
        raise PolicyAnalysisJourneyNotFoundError(str(run_id))

    attempt = (
        session.get(PolicyExtractionAttempt, run.latest_extraction_attempt_id)
        if run.latest_extraction_attempt_id is not None
        else None
    )
    if attempt is not None and attempt.policy_analysis_run_id != run.id:
        raise PolicyAnalysisJourneyNotFoundError(str(run_id))

    assessment = None
    assessment_response = None
    coverage: list[EnterpriseCoverageDomainResponse] = []
    if run.assessment_id is not None:
        assessment = get_impact_assessment(session, run.assessment_id)
        if assessment.policy_analysis_run_id != run.id:
            raise PolicyAnalysisJourneyNotFoundError(str(run_id))
        serialized = serialize_assessment(assessment)
        assessment_response = AnalysisJourneyAssessmentResponse.model_validate(
            serialized.model_dump(exclude={"input_fingerprint", "unresolved_questions"})
        )
        coverage = _derive_enterprise_coverage(
            session,
            run.organization_id,
            assessment.enterprise_impacts,
        )

    return PolicyAnalysisJourneyResponse(
        policy=_serialize_policy(
            policy,
            organization,
            policy_text=run.policy_text_snapshot,
        ),
        run=serialize_policy_analysis_run(run),
        extraction=_serialize_extraction(attempt) if attempt is not None else None,
        uncertainty=AnalysisUncertaintyResponse(
            extraction_findings=list(attempt.findings) if attempt is not None else [],
            clarifications=serialize_policy_analysis_run(run).clarifications,
            legacy_assessment_questions="omitted_schema_v1_fixture",
        ),
        assessment=assessment_response,
        enterprise_coverage=coverage,
        interpretation=_interpretation_projection(session, run, assessment),
        approval_run=_approval_projection(session, run),
    )


def _serialize_policy(
    policy: PolicyChange,
    organization: Organization,
    *,
    policy_text: str | None = None,
) -> AnalysisJourneyPolicyResponse:
    return AnalysisJourneyPolicyResponse(
        id=policy.id,
        organization_id=policy.organization_id,
        organization_name=organization.name,
        title=policy.title,
        owner=policy.owner,
        version=policy.version,
        effective_date=policy.effective_date,
        policy_text=policy_text if policy_text is not None else policy.policy_text,
    )


def _serialize_extraction(
    attempt: PolicyExtractionAttempt,
) -> AnalysisJourneyExtractionResponse:
    return AnalysisJourneyExtractionResponse(
        id=attempt.id,
        policy_change_id=attempt.policy_change_id,
        policy_family=(attempt.parsed_output or {}).get("policy_family"),
        support_status=attempt.support_status,
        validation_outcome=attempt.validation_outcome,
        candidate_rules=attempt.candidate_rules,
        accepted_rules=attempt.accepted_rules,
        provenance=attempt.provenance,
        findings=attempt.findings,
        validation_errors=attempt.validation_errors,
        metadata=ExtractionMetadataResponse(
            model_provider=attempt.model_provider,
            model_identifier=attempt.model_identifier,
            prompt_version=attempt.prompt_version,
            schema_version=attempt.schema_version,
        ),
        created_at=attempt.created_at,
    )


def _derive_enterprise_coverage(
    session: Session,
    organization_id: str,
    impacts: Iterable[AssessmentEnterpriseImpact],
) -> list[EnterpriseCoverageDomainResponse]:
    impact_ids_by_domain_and_key: dict[tuple[str, str], list[uuid.UUID]] = {}
    for impact in impacts:
        impact_ids_by_domain_and_key.setdefault((impact.domain, impact.source_key), []).append(
            impact.id
        )

    universes = (
        (
            "systems",
            [
                (item.id, item.name)
                for item in session.scalars(
                    select(EnterpriseSystem)
                    .where(
                        EnterpriseSystem.organization_id == organization_id,
                        EnterpriseSystem.active.is_(True),
                    )
                    .order_by(EnterpriseSystem.id)
                )
            ],
        ),
        (
            "documents",
            [
                (item.id, item.title)
                for item in session.scalars(
                    select(EnterpriseDocument)
                    .where(
                        EnterpriseDocument.organization_id == organization_id,
                        EnterpriseDocument.status != "archived",
                    )
                    .order_by(EnterpriseDocument.id)
                )
            ],
        ),
        (
            "teams",
            [
                (item.id, item.name)
                for item in session.scalars(
                    select(Team).where(Team.organization_id == organization_id).order_by(Team.id)
                )
            ],
        ),
        (
            "customer_commitments",
            [
                (item.id, item.customer_name)
                for item in session.scalars(
                    select(CustomerCommitment)
                    .where(
                        CustomerCommitment.organization_id == organization_id,
                        CustomerCommitment.status == "active",
                    )
                    .order_by(CustomerCommitment.id)
                )
            ],
        ),
    )
    result = []
    for domain, objects in universes:
        projected = []
        for object_id, display_name in objects:
            impact_ids = sorted(impact_ids_by_domain_and_key.get((domain, object_id), []), key=str)
            projected.append(
                EnterpriseCoverageObjectResponse(
                    id=object_id,
                    display_name=display_name,
                    classification="affected" if impact_ids else "cleared",
                    impact_ids=impact_ids,
                )
            )
        affected = sum(item.classification == "affected" for item in projected)
        result.append(
            EnterpriseCoverageDomainResponse(
                domain=domain,
                considered=len(projected),
                affected=affected,
                cleared=len(projected) - affected,
                objects=projected,
            )
        )
    return result


def _interpretation_projection(
    session: Session,
    run: PolicyAnalysisRun,
    assessment,
) -> InterpretationJourneyResponse:
    if assessment is None:
        return InterpretationJourneyResponse(
            status="not_available", failure_code=None, change_plan=None
        )
    plan = session.scalar(
        select(ChangePlan).where(ChangePlan.impact_assessment_id == assessment.id)
    )
    if plan is not None:
        return InterpretationJourneyResponse(
            status="available",
            failure_code=None,
            change_plan=ChangePlanResponse(
                id=plan.id,
                policy_analysis_run_id=plan.policy_analysis_run_id,
                impact_assessment_id=plan.impact_assessment_id,
                interpretation_attempt_id=plan.interpretation_attempt_id,
                schema_version=plan.schema_version,
                created_at=plan.created_at,
                change_plan=plan.validated_plan,
            ),
        )
    latest_attempt = session.scalar(
        select(PolicyInterpretationAttempt)
        .where(
            PolicyInterpretationAttempt.policy_analysis_run_id == run.id,
            PolicyInterpretationAttempt.impact_assessment_id == assessment.id,
        )
        .order_by(
            PolicyInterpretationAttempt.created_at.desc(),
            PolicyInterpretationAttempt.id.desc(),
        )
        .limit(1)
    )
    return InterpretationJourneyResponse(
        status="failed" if latest_attempt is not None else "not_created",
        failure_code=latest_attempt.failure_code if latest_attempt is not None else None,
        change_plan=None,
    )


def _approval_projection(
    session: Session, run: PolicyAnalysisRun
) -> ApprovalRunReferenceResponse | None:
    if run.assessment_id is None:
        return None
    approval = session.scalar(
        select(ActionApprovalRun).where(ActionApprovalRun.assessment_id == run.assessment_id)
    )
    if approval is None or approval.policy_analysis_run_id != run.id:
        return None
    return ApprovalRunReferenceResponse(id=approval.id, status=approval.status)
