from typing import Literal

from pydantic import BaseModel, ConfigDict

CatalogObjectType = Literal[
    "enterprise_document",
    "enterprise_system",
    "training_course",
]
StatusBasis = Literal["stored", "normalized", "not_recorded"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CatalogOrganizationResponse(StrictModel):
    id: str
    name: str


class CatalogContextResponse(StrictModel):
    kind: Literal["seeded_demonstration"]
    label: Literal["Seeded demonstration catalog"]
    record_level_origin: Literal["not_recorded"]


class CatalogCountsResponse(StrictModel):
    enterprise_document: int
    enterprise_system: int
    training_course: int


class AssessmentContextCountsResponse(StrictModel):
    worker: int
    team: int
    customer_commitment: int


class CatalogStatusResponse(StrictModel):
    value: Literal["published", "draft", "archived", "active", "inactive"] | None
    basis: StatusBasis


class DocumentMetadataResponse(StrictModel):
    document_type: Literal["policy", "procedure", "guide", "knowledge_article"]
    version: str


class SystemMetadataResponse(StrictModel):
    system_type: str


class TrainingMetadataResponse(StrictModel):
    course_code: str
    completion_record_count: int


class CatalogObjectSummaryResponse(StrictModel):
    object_type: CatalogObjectType
    object_id: str
    display_name: str
    description: str | None
    owner: str | None
    source_system: str | None
    status: CatalogStatusResponse
    metadata: DocumentMetadataResponse | SystemMetadataResponse | TrainingMetadataResponse
    relationship_count: int


class CatalogBrowseResponse(StrictModel):
    organization: CatalogOrganizationResponse
    catalog_context: CatalogContextResponse
    catalog_counts: CatalogCountsResponse
    assessment_context_counts: AssessmentContextCountsResponse
    objects: list[CatalogObjectSummaryResponse]


class RecordProvenanceResponse(StrictModel):
    classification: Literal["not_recorded"]
    catalog_context: Literal["seeded_demonstration"]


class CatalogObjectResponse(CatalogObjectSummaryResponse):
    organization_id: str
    record_provenance: RecordProvenanceResponse


class PolicyReferenceResponse(StrictModel):
    id: str
    title: str
    version: str


class RelationshipEndpointResponse(StrictModel):
    object_type: Literal[
        "policy_rule_reference",
        "enterprise_document",
        "enterprise_system",
        "training_course",
    ]
    stable_key: str
    display_name: str
    href: str


class RelationshipTrustResponse(StrictModel):
    state: Literal["persisted_typed_relationship"]
    integrity: list[
        Literal[
            "policy_change_foreign_key",
            "enterprise_document_foreign_key",
            "enterprise_system_foreign_key",
            "training_course_foreign_key",
            "semantic_uniqueness",
        ]
    ]
    used_deterministically: Literal[True]


class RelationshipProvenanceResponse(StrictModel):
    classification: Literal["not_recorded"]
    creator: None
    owning_authority: None
    recorded_at: None
    approval: None


class CatalogRelationshipResponse(StrictModel):
    relationship_id: str
    relationship_source_type: Literal[
        "policy_document_dependency",
        "policy_system_dependency",
        "policy_training_dependency",
    ]
    relationship_type: str
    explanation: str
    impact_classification: Literal["review_required", "update_required"] | None
    policy: PolicyReferenceResponse
    source: RelationshipEndpointResponse
    target: RelationshipEndpointResponse
    trust: RelationshipTrustResponse
    provenance: RelationshipProvenanceResponse


class AssessmentUsageResponse(StrictModel):
    statement: str
    changes_assessment_behavior: Literal[False]


class CatalogObjectDetailResponse(StrictModel):
    object: CatalogObjectResponse
    relationships: list[CatalogRelationshipResponse]
    assessment_usage: AssessmentUsageResponse


class StructuredRuleReferenceResponse(StrictModel):
    field_path: str | None
    label: str | None
    mapping_status: Literal["supported", "unknown"]


class RuleRelationshipResponse(StrictModel):
    relationship_id: str
    relationship_type: str
    target_type: CatalogObjectType
    target_id: str
    target_name: str
    target_href: str


class RuleAuthorityBoundaryResponse(StrictModel):
    is_standalone_persisted_rule: Literal[False]
    relationship_source: Literal["persisted_dependency_rows"]
    assessment_use: Literal["deterministic"]


class PolicyRuleReferenceResponse(StrictModel):
    stable_key: str
    policy: PolicyReferenceResponse
    rule_code: str
    structured_rule_reference: StructuredRuleReferenceResponse
    relationships: list[RuleRelationshipResponse]
    authority_boundary: RuleAuthorityBoundaryResponse
