from collections import Counter
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from changeops.db.models import (
    CustomerCommitment,
    EnterpriseDocument,
    EnterpriseSystem,
    Organization,
    PolicyChange,
    PolicyDocumentDependency,
    PolicySystemDependency,
    PolicyTrainingDependency,
    Team,
    TrainingCourse,
    TrainingRecord,
    Worker,
)
from changeops.schemas.catalog import (
    AssessmentContextCountsResponse,
    AssessmentUsageResponse,
    CatalogBrowseResponse,
    CatalogContextResponse,
    CatalogCountsResponse,
    CatalogObjectDetailResponse,
    CatalogObjectResponse,
    CatalogObjectSummaryResponse,
    CatalogOrganizationResponse,
    CatalogRelationshipResponse,
    CatalogStatusResponse,
    DocumentMetadataResponse,
    PolicyReferenceResponse,
    PolicyRuleReferenceResponse,
    RecordProvenanceResponse,
    RelationshipEndpointResponse,
    RelationshipProvenanceResponse,
    RelationshipTrustResponse,
    RuleAuthorityBoundaryResponse,
    RuleRelationshipResponse,
    StructuredRuleReferenceResponse,
    SystemMetadataResponse,
    TrainingMetadataResponse,
)

SUPPORTED_OBJECT_TYPES = (
    "enterprise_document",
    "enterprise_system",
    "training_course",
)
OBJECT_TYPE_ORDER = {item: index for index, item in enumerate(SUPPORTED_OBJECT_TYPES)}

ASSESSMENT_USAGE = {
    "enterprise_document": (
        "The assessment service loads this policy-scoped dependency and the deterministic "
        "enterprise analyzer uses it to construct document impact, evidence, relationship path, "
        "and proposed-action output."
    ),
    "enterprise_system": (
        "The assessment service loads this policy-scoped dependency and the deterministic "
        "enterprise analyzer uses it to determine whether the system supports an applicable "
        "policy rule and to construct system impact, evidence, relationship path, and proposed-"
        "action output."
    ),
    "training_course": (
        "The assessment service loads this policy-scoped dependency and the deterministic "
        "enterprise analyzer uses it with the typed course and completion records to construct "
        "training impact, evidence, and relationship-path output."
    ),
}

RULE_REFERENCES = {
    "MANAGER_APPROVAL_REQUIRED": ("manager_approval", "Manager approval rule"),
    "TRAINING_REQUIRED": ("security_training", "Security training rule"),
    "POLICY_CHANGE": ("effective_date", "Policy effective-date rule"),
}


class CatalogOrganizationNotFoundError(Exception):
    pass


class UnsupportedCatalogObjectTypeError(Exception):
    pass


class CatalogObjectNotFoundError(Exception):
    pass


class PolicyChangeNotFoundError(Exception):
    pass


class PolicyRuleReferenceNotFoundError(Exception):
    pass


class CatalogProjectionIntegrityError(Exception):
    pass


@dataclass(frozen=True)
class DependencySpec:
    model: type
    target_field: str
    object_type: str
    source_type: str
    target_integrity: str


DEPENDENCY_BY_OBJECT_TYPE = {
    "enterprise_document": DependencySpec(
        PolicyDocumentDependency,
        "document_id",
        "enterprise_document",
        "policy_document_dependency",
        "enterprise_document_foreign_key",
    ),
    "enterprise_system": DependencySpec(
        PolicySystemDependency,
        "system_id",
        "enterprise_system",
        "policy_system_dependency",
        "enterprise_system_foreign_key",
    ),
    "training_course": DependencySpec(
        PolicyTrainingDependency,
        "course_id",
        "training_course",
        "policy_training_dependency",
        "training_course_foreign_key",
    ),
}


def get_catalog_browse(
    session: Session,
    organization_id: str,
    object_type: str | None = None,
) -> CatalogBrowseResponse:
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise CatalogOrganizationNotFoundError(organization_id)
    if object_type is not None:
        _require_supported_type(object_type)

    documents = list(
        session.scalars(
            select(EnterpriseDocument)
            .where(EnterpriseDocument.organization_id == organization_id)
            .order_by(EnterpriseDocument.id)
        )
    )
    systems = list(
        session.scalars(
            select(EnterpriseSystem)
            .where(EnterpriseSystem.organization_id == organization_id)
            .order_by(EnterpriseSystem.id)
        )
    )
    courses = list(
        session.scalars(
            select(TrainingCourse)
            .where(TrainingCourse.organization_id == organization_id)
            .order_by(TrainingCourse.id)
        )
    )

    dependency_counts = _dependency_counts(session)
    completion_counts = _completion_counts(session)
    objects = [
        *(
            _document_summary(item, dependency_counts["enterprise_document"][item.id])
            for item in documents
        ),
        *(
            _system_summary(item, dependency_counts["enterprise_system"][item.id])
            for item in systems
        ),
        *(
            _training_summary(
                item,
                dependency_counts["training_course"][item.id],
                completion_counts[item.id],
            )
            for item in courses
        ),
    ]
    if object_type is not None:
        objects = [item for item in objects if item.object_type == object_type]
    objects.sort(key=lambda item: (OBJECT_TYPE_ORDER[item.object_type], item.object_id))

    return CatalogBrowseResponse(
        organization=CatalogOrganizationResponse(id=organization.id, name=organization.name),
        catalog_context=_catalog_context(),
        catalog_counts=CatalogCountsResponse(
            enterprise_document=len(documents),
            enterprise_system=len(systems),
            training_course=len(courses),
        ),
        assessment_context_counts=AssessmentContextCountsResponse(
            worker=_count_for_organization(session, Worker, organization_id),
            team=_count_for_organization(session, Team, organization_id),
            customer_commitment=_count_for_organization(
                session, CustomerCommitment, organization_id
            ),
        ),
        objects=objects,
    )


def get_catalog_object_detail(
    session: Session,
    object_type: str,
    object_id: str,
    *,
    organization_id: str | None = None,
) -> CatalogObjectDetailResponse:
    _require_supported_type(object_type)
    record = _get_object(session, object_type, object_id)
    if record is None or (
        organization_id is not None and record.organization_id != organization_id
    ):
        raise CatalogObjectNotFoundError(object_id)

    relationships = _relationships_for_object(session, object_type, record)
    completion_count = (
        session.scalar(
            select(func.count())
            .select_from(TrainingRecord)
            .where(TrainingRecord.course_identifier == record.id)
        )
        or 0
        if object_type == "training_course"
        else 0
    )
    summary = _summary_for_record(
        object_type,
        record,
        relationship_count=len(relationships),
        completion_count=completion_count,
    )
    return CatalogObjectDetailResponse(
        object=CatalogObjectResponse(
            **summary.model_dump(),
            organization_id=record.organization_id,
            record_provenance=RecordProvenanceResponse(
                classification="not_recorded",
                catalog_context="seeded_demonstration",
            ),
        ),
        relationships=relationships,
        assessment_usage=AssessmentUsageResponse(
            statement=ASSESSMENT_USAGE[object_type],
            changes_assessment_behavior=False,
        ),
    )


def get_policy_rule_reference(
    session: Session,
    policy_change_id: str,
    rule_code: str,
) -> PolicyRuleReferenceResponse:
    policy = session.get(PolicyChange, policy_change_id)
    if policy is None:
        raise PolicyChangeNotFoundError(policy_change_id)

    dependencies = _dependencies_for_rule(session, policy_change_id, rule_code)
    if not dependencies:
        raise PolicyRuleReferenceNotFoundError(f"{policy_change_id}:{rule_code}")

    relationships = []
    for object_type, dependency in dependencies:
        target = _get_object(
            session,
            object_type,
            getattr(dependency, DEPENDENCY_BY_OBJECT_TYPE[object_type].target_field),
        )
        if target is None or target.organization_id != policy.organization_id:
            raise CatalogProjectionIntegrityError(
                f"Relationship {dependency.id} cannot resolve an organization-scoped target."
            )
        relationships.append(
            RuleRelationshipResponse(
                relationship_id=dependency.id,
                relationship_type=dependency.relationship_type,
                target_type=object_type,
                target_id=target.id,
                target_name=_display_name(object_type, target),
                target_href=_frontend_object_href(object_type, target.id),
            )
        )
    relationships.sort(key=lambda item: item.relationship_id)
    mapping = RULE_REFERENCES.get(rule_code)
    return PolicyRuleReferenceResponse(
        stable_key=f"{policy.id}:{rule_code}",
        policy=PolicyReferenceResponse(id=policy.id, title=policy.title, version=policy.version),
        rule_code=rule_code,
        structured_rule_reference=StructuredRuleReferenceResponse(
            field_path=mapping[0] if mapping else None,
            label=mapping[1] if mapping else None,
            mapping_status="supported" if mapping else "unknown",
        ),
        relationships=relationships,
        authority_boundary=RuleAuthorityBoundaryResponse(
            is_standalone_persisted_rule=False,
            relationship_source="persisted_dependency_rows",
            assessment_use="deterministic",
        ),
    )


def _require_supported_type(object_type: str) -> None:
    if object_type not in SUPPORTED_OBJECT_TYPES:
        raise UnsupportedCatalogObjectTypeError(object_type)


def _get_object(session: Session, object_type: str, object_id: str):
    model = {
        "enterprise_document": EnterpriseDocument,
        "enterprise_system": EnterpriseSystem,
        "training_course": TrainingCourse,
    }[object_type]
    return session.get(model, object_id)


def _relationships_for_object(
    session: Session,
    object_type: str,
    record,
) -> list[CatalogRelationshipResponse]:
    spec = DEPENDENCY_BY_OBJECT_TYPE[object_type]
    target_column = getattr(spec.model, spec.target_field)
    dependencies = list(
        session.scalars(
            select(spec.model).where(target_column == record.id).order_by(spec.model.id)
        )
    )
    relationships = []
    for dependency in dependencies:
        policy = session.get(PolicyChange, dependency.policy_change_id)
        if policy is None or policy.organization_id != record.organization_id:
            raise CatalogProjectionIntegrityError(
                f"Relationship {dependency.id} cannot resolve an organization-scoped policy."
            )
        relationships.append(
            CatalogRelationshipResponse(
                relationship_id=dependency.id,
                relationship_source_type=spec.source_type,
                relationship_type=dependency.relationship_type,
                explanation=dependency.explanation,
                impact_classification=getattr(dependency, "impact_classification", None),
                policy=PolicyReferenceResponse(
                    id=policy.id,
                    title=policy.title,
                    version=policy.version,
                ),
                source=RelationshipEndpointResponse(
                    object_type="policy_rule_reference",
                    stable_key=f"{policy.id}:{dependency.rule_code}",
                    display_name=dependency.rule_code,
                    href=_api_rule_href(policy.id, dependency.rule_code),
                ),
                target=RelationshipEndpointResponse(
                    object_type=object_type,
                    stable_key=record.id,
                    display_name=_display_name(object_type, record),
                    href=_frontend_object_href(object_type, record.id),
                ),
                trust=RelationshipTrustResponse(
                    state="persisted_typed_relationship",
                    integrity=[
                        "policy_change_foreign_key",
                        spec.target_integrity,
                        "semantic_uniqueness",
                    ],
                    used_deterministically=True,
                ),
                provenance=_missing_relationship_provenance(),
            )
        )
    return relationships


def _dependencies_for_rule(session: Session, policy_id: str, rule_code: str):
    rows = []
    for object_type in SUPPORTED_OBJECT_TYPES:
        spec = DEPENDENCY_BY_OBJECT_TYPE[object_type]
        dependencies = session.scalars(
            select(spec.model).where(
                spec.model.policy_change_id == policy_id,
                spec.model.rule_code == rule_code,
            )
        )
        rows.extend((object_type, dependency) for dependency in dependencies)
    return sorted(rows, key=lambda item: item[1].id)


def _dependency_counts(session: Session) -> dict[str, Counter[str]]:
    result: dict[str, Counter[str]] = {}
    for object_type, spec in DEPENDENCY_BY_OBJECT_TYPE.items():
        result[object_type] = Counter(
            getattr(item, spec.target_field)
            for item in session.scalars(select(spec.model).order_by(spec.model.id))
        )
    return result


def _completion_counts(session: Session) -> Counter[str]:
    return Counter(
        item.course_identifier
        for item in session.scalars(select(TrainingRecord).order_by(TrainingRecord.id))
    )


def _count_for_organization(session: Session, model, organization_id: str) -> int:
    return (
        session.scalar(
            select(func.count()).select_from(model).where(model.organization_id == organization_id)
        )
        or 0
    )


def _summary_for_record(
    object_type: str,
    record,
    *,
    relationship_count: int,
    completion_count: int = 0,
) -> CatalogObjectSummaryResponse:
    if object_type == "enterprise_document":
        return _document_summary(record, relationship_count)
    if object_type == "enterprise_system":
        return _system_summary(record, relationship_count)
    return _training_summary(record, relationship_count, completion_count)


def _document_summary(
    record: EnterpriseDocument, relationship_count: int
) -> CatalogObjectSummaryResponse:
    return CatalogObjectSummaryResponse(
        object_type="enterprise_document",
        object_id=record.id,
        display_name=record.title,
        description=None,
        owner=None,
        source_system=record.source_system,
        status=CatalogStatusResponse(value=record.status, basis="stored"),
        metadata=DocumentMetadataResponse(
            document_type=record.document_type,
            version=record.version,
        ),
        relationship_count=relationship_count,
    )


def _system_summary(
    record: EnterpriseSystem, relationship_count: int
) -> CatalogObjectSummaryResponse:
    return CatalogObjectSummaryResponse(
        object_type="enterprise_system",
        object_id=record.id,
        display_name=record.name,
        description=record.description,
        owner=None,
        source_system=None,
        status=CatalogStatusResponse(
            value="active" if record.active else "inactive",
            basis="normalized",
        ),
        metadata=SystemMetadataResponse(system_type=record.system_type),
        relationship_count=relationship_count,
    )


def _training_summary(
    record: TrainingCourse,
    relationship_count: int,
    completion_count: int,
) -> CatalogObjectSummaryResponse:
    return CatalogObjectSummaryResponse(
        object_type="training_course",
        object_id=record.id,
        display_name=record.name,
        description=None,
        owner=None,
        source_system=None,
        status=CatalogStatusResponse(
            value="active" if record.active else "inactive",
            basis="normalized",
        ),
        metadata=TrainingMetadataResponse(
            course_code=record.course_code,
            completion_record_count=completion_count,
        ),
        relationship_count=relationship_count,
    )


def _catalog_context() -> CatalogContextResponse:
    return CatalogContextResponse(
        kind="seeded_demonstration",
        label="Seeded demonstration catalog",
        record_level_origin="not_recorded",
    )


def _missing_relationship_provenance() -> RelationshipProvenanceResponse:
    return RelationshipProvenanceResponse(
        classification="not_recorded",
        creator=None,
        owning_authority=None,
        recorded_at=None,
        approval=None,
    )


def _display_name(object_type: str, record) -> str:
    return record.title if object_type == "enterprise_document" else record.name


def _api_rule_href(policy_id: str, rule_code: str) -> str:
    return f"/api/v1/policy-changes/{policy_id}/rule-references/{rule_code}"


def _frontend_object_href(object_type: str, object_id: str) -> str:
    return f"/catalog/{object_type}/{object_id}"
