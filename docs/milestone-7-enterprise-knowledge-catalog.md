# Milestone 7 — Enterprise Knowledge Catalog Explorer

## Status

PR A is merged. PR B is implemented with fixture-backed verification and was live-validated
against the bounded Acme Confluence knowledge base on August 4, 2026. Live credentials and page
identifiers remain environment-only. The current local credential is broader than least privilege
and must be replaced or restricted before a public demo. PR C relationship-origin provenance
remains deferred.

This document is based on repository `main` at commit `14cfb5d` and on the implementation,
migrations, seed/reset behavior, tests, and product-facing read models at that commit. The
implementation is the source of truth where older planning language differs.

## Product capability

Add a read-only Enterprise Knowledge Catalog Explorer that answers:

> What enterprise objects does ChangeOps know about, where did they come from, and why does it
> trust their relationships?

The first vertical slice explains the persisted enterprise context that the deterministic
assessment already consumes. It does not create a second catalog system of record and does not
change assessment behavior.

The approved delivery sequence is:

1. **PR A — read-only explorer over existing typed tables:** prioritize documents, systems,
   training courses, and policy dependencies, with honest missing-metadata states and no
   migration.
2. **PR B — narrow external document identity and read-only Confluence metadata:** persist and
   display selected page identities, imported metadata, and external links without changing
   relationships or assessment behavior.
3. **PR C — relationship-origin provenance:** add only the narrowly required provenance for
   existing typed relationships after the PR A and PR B reviewer experiences show what is still
   missing.

PR A is the Codex-ready first vertical slice in this document. PR B is a named planned slice, not
merely a deferred possibility. PR C must remain distinct from PR B: external document identity and
relationship governance solve different product problems and must not be combined into a vague
provenance-completion feature. None of the three PRs may introduce a generalized
`catalog_objects` abstraction.

## Reviewer outcome

After PR A, a reviewer can:

- browse the existing documents, systems, and training courses by category;
- open a persisted enterprise object using its existing stable identity;
- see compact counts for workers, teams, and customer commitments as assessment context without
  treating each as an equal catalog-detail destination;
- distinguish stored fields, normalized display values, catalog-level demo context, and metadata
  that is not recorded;
- inspect the typed relationships connected to the object;
- follow a policy dependency to a policy-scoped rule reference;
- see the exact dependency row, relationship type, explanation, foreign-key integrity, and
  deterministic analyzer use that make the relationship trusted for current assessments;
- understand that row-level creator, import, curation, and approval provenance are not yet stored;
- return to the existing governed policy-analysis journey.

PR A must make limitations visible rather than filling them with inferred or invented values.

## Flagship walkthrough

The first slice should support this honest walkthrough:

```text
Manager Travel Approval Guide
    ↓
Object type: Document
Stable identity: document-manager-travel-approval-guide
Catalog context: Seeded demonstration catalog
Source system: Acme Knowledge
Owner: Not recorded in the current catalog
Status: Published
    ↓
Persisted typed relationship
Relationship: instructs_manager
Relationship row: dependency-policy-manager-guide
Row-level provenance: Not recorded
    ↓
Policy-scoped rule reference
policy-international-travel-2026-09:MANAGER_APPROVAL_REQUIRED
    ↓
Used deterministically during impact assessment
```

The guide also has a business-equivalent dependency row for the proposed policy:
`dependency-policy-manager-guide-proposed`. The detail page must show both policy-scoped
relationships rather than collapsing them into one relationship with ambiguous lineage.

The intended fully enriched walkthrough remains:

```text
Manager Travel Approval Guide
    ↓
Owner: Travel Operations
Source: Seeded demonstration catalog
Status: Published
    ↓
Trusted relationship with explicit provenance
    ↓
MANAGER_APPROVAL_REQUIRED
    ↓
Used deterministically during impact assessment
```

The current schema cannot honestly display `Owner: Travel Operations` or row-level relationship
origin. Those values belong in a separately reviewed later provenance migration, not in hard-coded
serializer logic.

## Current catalog and domain model

### Source and catalog objects

The following persisted records are enterprise source facts rather than assessment output:

| Object | Table/model | Stable business identity | Current descriptive fields | Current owner/source/status fields |
| --- | --- | --- | --- | --- |
| Organization | `organizations` / `Organization` | string primary key `id` | `name`, `industry`, `headquarters` | no source, owner, or status |
| Worker | `workers` / `Worker` | string primary key `id` | `full_name`, `worker_type`, `department`, assigned country | manager identity is a relationship; no source or status |
| Team | `teams` / `Team` | string primary key `id` | `name` | manager relationship; no source or status |
| Enterprise system | `enterprise_systems` / `EnterpriseSystem` | string primary key `id` | `name`, `system_type`, `description` | `active`; no owner or source system |
| Enterprise document | `enterprise_documents` / `EnterpriseDocument` | string primary key `id` | `title`, `document_type`, `version` | `source_system`, `status`; no description or owner |
| Training course | `training_courses` / `TrainingCourse` | string primary key `id`; unique `course_code` | `course_code`, `name` | `active`; no description, owner, or source system |
| Customer commitment | `customer_commitments` / `CustomerCommitment` | string primary key `id` | customer, type, description, dates | `status`; no owner or source system |
| Policy source | `policy_changes` / `PolicyChange` | string primary key `id` | title, version, effective date, text, structured rules | `owner`; no source-system or lifecycle-status field |

These are true persisted source/catalog records for the current bounded product. A policy source
is catalog-adjacent: it provides policy and rule context for dependencies, but the first browse
experience should keep the main categories focused on the enterprise object types named in the
product objective.

### PR A experience prioritization

Repository evidence does not justify equal full-detail experiences for every source type.

PR A should provide full browse and detail experiences for:

- enterprise documents;
- enterprise systems;
- training courses.

It should make policy-system, policy-document, and policy-training dependencies first-class within
those details and through policy-scoped rule-reference pages.

Workers, teams, and customer commitments remain real authoritative assessment inputs, but full
catalog-detail pages for them are deferred because:

- the policy-analysis journey already explains their affected and cleared outcomes;
- their current tables lack the owner, source-system, and lifecycle metadata expected of a useful
  catalog detail;
- worker and team relationships describe organizational assessment context more than enterprise
  knowledge-source authority;
- worker detail would expand the explorer toward personnel browsing without advancing the
  flagship document-source and trusted-dependency story;
- customer commitments are important downstream obligations, but PR A needs only to prove that
  ChangeOps knows they exist, not reproduce their assessment experience.

PR A should expose compact assessment-context counts for workers, teams, and customer commitments
on the browse page. It may show stable names in a collapsed context summary if that improves
comprehension, but it must not add dedicated detail routes, relationship graphs, or duplicate the
existing impact journey for those types.

### Operational source facts

The following records are authoritative assessment inputs but should not be presented as top-level
catalog master objects in PR A:

- `trips` — worker-specific operational events;
- `training_records` — worker/course completion facts;
- `policy_change_questions` — legacy seeded scenario fixtures, not model-discovered uncertainty.

They may appear as related facts only where a future, separately approved catalog experience needs
them. PR A does not add trip or completion-record browsing.

### Source relationships

The existing schema represents relationships explicitly:

| Relationship | Persistence | Integrity and identity |
| --- | --- | --- |
| Worker managed by worker | `workers.manager_worker_id` | self foreign key to `workers.id` |
| Team managed by worker | `teams.manager_worker_id` | foreign key to `workers.id` |
| Worker member of team | `worker_team_memberships` | string row ID, worker/team foreign keys, one-membership-per-worker uniqueness |
| Training record for worker/course | `training_records` | worker/course foreign keys and semantic uniqueness |
| Commitment assigned to worker | `commitment_assignments` | string row ID, two foreign keys, semantic uniqueness |
| Policy rule connected to system | `policy_system_dependencies` | string row ID, policy/system foreign keys, semantic uniqueness |
| Policy rule connected to document | `policy_document_dependencies` | string row ID, policy/document foreign keys, semantic uniqueness |
| Policy rule connected to course | `policy_training_dependencies` | string row ID, policy/course foreign keys, semantic uniqueness |

The three policy dependency tables also store:

- `rule_code`;
- `relationship_type`;
- `explanation`;
- document `impact_classification`, where applicable.

These dependency rows are the most important trusted catalog relationships for PR A because the
deterministic enterprise analyzer loads them directly.

### Assessment and workflow artifacts

The following are not catalog objects. They are historical, derived, workflow, decision, or
execution artifacts:

- extraction attempts and policy-analysis runs;
- clarifications and interpretation attempts;
- impact assessments and worker results;
- findings;
- evidence snapshots;
- assessment enterprise impacts;
- assessment impact path elements;
- proposed actions;
- copied assessment unresolved questions;
- change plans;
- action reviews and decisions;
- approval runs, items, and transitions;
- execution commands, delivery state, simulated assignments, Jira receipts, and execution
  results;
- policy comparisons, semantic differences, impact deltas, and delta items.

In particular:

- `assessment_enterprise_impacts` is an immutable conclusion about a source object, not the object;
- `evidence` is an assessment-scoped snapshot, not the live catalog record;
- `assessment_impact_path_elements` is immutable historical traversal output, not the current
  relationship store;
- comparison `stable_identity` and policy-comparison `rule_identity` identify derived comparison
  semantics, not catalog rows.

The explorer must query source tables for current catalog facts and may link to assessment
artifacts for explanation. It must never reconstruct the catalog from evidence snapshots or impact
paths.

## Stable identity and policy-rule identity

### Enterprise objects

Current enterprise source objects use human-readable string primary keys. These keys are already:

- referenced by foreign keys;
- used in seed upserts;
- included in canonical assessment fingerprints;
- copied into `AssessmentEnterpriseImpact.source_key`;
- preserved in evidence source IDs and relationship paths;
- used for deterministic impact-delta matching.

PR A must reuse these IDs. It must not create catalog UUIDs, aliases, slugs, or a new identity
registry.

### Relationships

Relationship tables use stable string row IDs plus semantic uniqueness constraints. PR A should
expose both:

- the row identity, for exact lineage; and
- the semantic endpoints and relationship type, for business comprehension.

### Policy rules

The current implementation does not have a `policy_rules` table or a standalone rule aggregate.
Rule identity is represented in several bounded forms:

- dependency and finding `rule_code` values such as `MANAGER_APPROVAL_REQUIRED`,
  `TRAINING_REQUIRED`, and `POLICY_CHANGE`;
- typed structured-rule paths such as `manager_approval` and `security_training`;
- evidence keys such as
  `policy:{policy_change_id}:manager_approval`;
- impact-path stable keys, including both
  `{policy_change_id}:{rule_code}` and structured-rule suffix variants;
- comparison field identities such as
  `manager_approval.booking_before_effective_date_is_exempt`.

PR A must not pretend these are one persisted rule entity. It should project a
**policy-scoped rule reference** from:

```text
policy_change_id + persisted dependency rule_code
```

For the flagship relationship, the stable reference is:

```text
policy-international-travel-2026-09:MANAGER_APPROVAL_REQUIRED
```

The read service may use a small closed mapping to explain that
`MANAGER_APPROVAL_REQUIRED` corresponds to the current structured `manager_approval` rule and its
policy evidence suffix. This mapping is presentation/domain adapter code, not new persistence and
not a generic rule registry. Unknown codes must remain visible as unknown structured mappings
rather than being guessed.

## How relationships are created today

All current enterprise source objects and relationships are created by the idempotent
`seed_database` service.

For the policy dependency catalog:

- two system dependencies are merged for the baseline policy and duplicated with source-specific
  IDs for the proposed policy;
- three document dependencies are merged for each policy;
- one training dependency is merged for each policy;
- the baseline and proposed dependency sets are deliberately business-equivalent;
- integration tests compare those business fields after excluding source-specific row and policy
  IDs.

The seed uses SQLAlchemy `Session.merge` with stable IDs. Re-running it updates or reuses the same
rows instead of creating duplicates.

There is currently:

- no import job;
- no catalog write API;
- no relationship editor;
- no human-curation workflow;
- no AI proposal or acceptance workflow;
- no per-row source batch, creator, timestamp, or approval record.

## How relationships are used today

The assessment service:

1. loads the policy and organization-scoped source records;
2. loads dependency rows scoped to the selected `policy_change_id`;
3. converts them into immutable typed domain input;
4. calls the pure enterprise-impact analyzer;
5. persists immutable impact, evidence, and path snapshots.

For `document-manager-travel-approval-guide`:

1. `PolicyDocumentDependency` links the selected policy, rule code
   `MANAGER_APPROVAL_REQUIRED`, and the document through real foreign keys.
2. Its `relationship_type` is `instructs_manager`.
3. Its `impact_classification` is `review_required`.
4. Its explanation is `The manager guide documents approval responsibilities.`
5. `_add_document_impacts` creates a document impact from that dependency.
6. The impact includes evidence snapshots for the document, dependency row, and policy rule.
7. The persisted path is policy change → policy rule → enterprise document.
8. The proposed action remains a separate immutable assessment artifact.

The relationship is therefore trusted by the current analyzer because it is a persisted typed
mapping with referential integrity and the analyzer consumes it deterministically. That is a
trust basis, not row-origin provenance.

## Current provenance and the gaps

### Provenance that already exists

The implementation already preserves several kinds of provenance, but none is relationship-origin
provenance:

- extraction attempts store model/provider/prompt/schema metadata and policy source-span
  provenance;
- policy comparisons store side-specific accepted extraction provenance;
- clarifications store responder and answer provenance;
- assessment evidence stores source type, source ID, label, and a source snapshot;
- assessment paths store the ordered relationship names used for one historical conclusion;
- reviews, approvals, commands, and results store human and execution lineage.

For dependency relationships themselves, the existing provenance-like fields are limited to:

- stable dependency ID;
- policy ID;
- rule code;
- typed target foreign key;
- relationship type;
- explanation;
- document impact classification where applicable.

There is no relationship creator, owning authority, creation time, import reference, curation
decision, approval record, or provenance category.

### Missing information by requested source category

| Category | What would be required for an honest claim | Current state |
| --- | --- | --- |
| Seeded demonstration data | row-level origin or an explicitly bounded dataset declaration tied to the canonical seed | dataset origin is evident from code and demo context, but not stored per row |
| Imported authoritative metadata | source system type, external stable ID/URL, import batch or retrieval time, source version/fingerprint | absent |
| Human-curated mapping | curator identity, authority/role, recorded time, rationale, lifecycle status | absent |
| Human-approved AI proposal | immutable proposal, exact evidence, model metadata, reviewer decision, reviewer identity/time, accepted relationship lineage | entirely absent and intentionally deferred |

Object metadata gaps are also material:

- documents have source system and status but no description or owner;
- systems have description and active state but no owner or source system;
- courses have name/code and active state but no description, owner, or source system;
- workers and teams have names and structural relationships but no record source or lifecycle
  status;
- commitments have description and status but no owner or record source.

PR A must use an explicit `not_recorded` state. It must not treat a team manager as an object
owner, `Acme Knowledge` as proof of import, an assessment evidence snapshot as relationship
provenance, or the existence of a foreign key as proof of human approval.

## Architecture decision

### Decision

Implement PR A as a read-only application projection over existing PostgreSQL tables.

Do not add:

- a `catalog_objects` table;
- a polymorphic catalog relationship table;
- a graph database;
- a generic repository or search framework;
- a persisted UI/read-model snapshot.

The projection should follow the existing journey and workbench pattern:

```text
FastAPI GET route
    ↓
catalog projection service
    ↓
explicit SQLAlchemy queries over current typed tables
    ↓
closed Pydantic response union
    ↓
Next.js server-rendered list/detail pages
```

PostgreSQL remains authoritative. The API resolves current records on every request. The browser
stores no catalog state beyond navigation.

### Why a projection is coherent

The source model already provides:

- closed object categories;
- stable business identities;
- organization ownership;
- business names;
- useful category-specific metadata;
- document source system and status;
- descriptions for systems and commitments;
- typed dependency tables with foreign keys;
- relationship types and explanations;
- policy-scoped rule codes;
- deterministic analyzer behavior that consumes those dependencies.

The missing fields affect completeness and provenance, not the ability to browse the existing
model coherently.

### Migration decision

**PR A requires no migration.**

A migration is genuinely required only if the approved acceptance criteria demand row-level:

- object owner or description where the current object table lacks it;
- seeded/imported/curated origin;
- creator or owning authority;
- recorded timestamp;
- external authoritative identity;
- human approval lineage.

The exact desired flagship value `Owner: Travel Operations` cannot be produced honestly from the
current database.

PR A should not trigger an immediate relationship-provenance migration.

PR B owns the narrow schema needed for external document identity and imported read-only
Confluence metadata. It must not add relationship-governance fields merely because both concerns
use the word provenance.

PR C, if narrowly required after PR A and PR B, owns relationship-origin provenance on the
existing typed dependency tables. It should duplicate a small closed provenance contract across
`policy_system_dependencies`, `policy_document_dependencies`, and
`policy_training_dependencies` when necessary rather than replacing their real target foreign
keys with a polymorphic abstraction.

Do not add placeholder fields claiming `human_approved_ai` provenance without an immutable proposal
and human decision aggregate. That category remains unrepresentable until the later proposal
governance slice exists.

## API/read projection

### API profile

- API name: `catalog-objects-v1`
- lifecycle: development/local demonstration
- base server: `http://localhost:8000`
- versioning: use the repository's existing `/api/v1` namespace and snake_case response fields
- authority: current PostgreSQL source rows
- writes: none

### Resources

PR A exposes two read resources:

1. catalog objects — a closed discriminated projection over existing source tables;
2. policy rule references — policy-scoped references resolved from persisted dependency rule
   codes, not standalone stored rules.

Supported full-detail catalog object types:

```text
enterprise_document
enterprise_system
training_course
```

Workers, teams, and customer commitments are returned only in a compact
`assessment_context_counts` projection. They are not valid PR A detail-route object types.

Category-specific status projection is deliberately small:

| Object type | Status response |
| --- | --- |
| Enterprise document | stored `published`, `draft`, or `archived` |
| Enterprise system | normalized `active` or `inactive` from stored `active` boolean |
| Training course | normalized `active` or `inactive` from stored `active` boolean |

Normalized values must include `basis = normalized`; stored values use `basis = stored`; absent
values use `basis = not_recorded`. Normalization is display behavior only.

Relationship projection is also closed:

| Current object | Relationships shown |
| --- | --- |
| Enterprise document | inverse policy-document dependencies |
| Enterprise system | inverse policy-system dependencies |
| Training course | inverse policy-training dependencies and related completion records only as counts, not browsable objects |

Typed policy-dependency relationships retain their persisted row ID. PR A does not project
worker-manager, team-membership, or commitment-assignment relationships into full catalog detail.
Those relationships remain authoritative assessment inputs and continue to appear in assessment
evidence and paths where applicable.

### Endpoints

```http
GET /api/v1/catalog-objects
GET /api/v1/catalog-objects/{object_type}/{object_id}
GET /api/v1/policy-changes/{policy_change_id}/rule-references/{rule_code}
```

Paths use plural noun resources. No create, update, delete, search, refresh, import, or relationship
action endpoint is added.

### List endpoint

`GET /api/v1/catalog-objects`

Purpose: return the bounded catalog browse projection.

Query parameters:

| Name | Type | Required | Meaning | Example |
| --- | --- | --- | --- | --- |
| `organization_id` | string | yes | existing organization stable ID | `org-acme-global-manufacturing` |
| `object_type` | closed string | no | primary category filter; absent returns all three full-detail types | `enterprise_document` |

Sorting is deterministic by object type order and existing stable object ID. PR A does not add
pagination because the endpoint is deliberately bounded to the small demonstration catalog. It
does not add free-text search.

Representative response:

```json
{
  "organization": {
    "id": "org-acme-global-manufacturing",
    "name": "Acme Global Manufacturing"
  },
  "catalog_context": {
    "kind": "seeded_demonstration",
    "label": "Seeded demonstration catalog",
    "record_level_origin": "not_recorded"
  },
  "catalog_counts": {
    "enterprise_document": 4,
    "enterprise_system": 3,
    "training_course": 1
  },
  "assessment_context_counts": {
    "worker": 12,
    "team": 4,
    "customer_commitment": 2
  },
  "objects": [
    {
      "object_type": "enterprise_document",
      "object_id": "document-manager-travel-approval-guide",
      "display_name": "Manager Travel Approval Guide",
      "description": null,
      "owner": null,
      "source_system": "Acme Knowledge",
      "status": {
        "value": "published",
        "basis": "stored"
      },
      "relationship_count": 2
    }
  ]
}
```

`catalog_context.kind` describes the bounded current demo dataset. It is not per-row import
provenance. The UI must present `record_level_origin = not_recorded` when discussing an individual
row.

Success: `200 OK`.

Stable errors:

- `404 organization_not_found`;
- `422 unsupported_catalog_object_type`.

### Detail endpoint

`GET /api/v1/catalog-objects/{object_type}/{object_id}`

Purpose: resolve one existing source record, its category-specific metadata, and its current typed
relationships.

PR A detail resolution supports only `enterprise_document`, `enterprise_system`, and
`training_course`. Requests for workers, teams, or customer commitments return
`422 unsupported_catalog_object_type`; those types remain assessment context in this slice.

The service must verify that the record exists and return its stored `organization_id`. An optional
`organization_id` query constraint may be accepted only if it rejects cross-organization records
rather than changing identity semantics.

Representative response:

```json
{
  "object": {
    "object_type": "enterprise_document",
    "object_id": "document-manager-travel-approval-guide",
    "organization_id": "org-acme-global-manufacturing",
    "display_name": "Manager Travel Approval Guide",
    "description": null,
    "owner": null,
    "source_system": "Acme Knowledge",
    "status": {
      "value": "published",
      "basis": "stored"
    },
    "metadata": {
      "document_type": "guide",
      "version": "2"
    },
    "record_provenance": {
      "classification": "not_recorded",
      "catalog_context": "seeded_demonstration"
    }
  },
  "relationships": [
    {
      "relationship_id": "dependency-policy-manager-guide",
      "relationship_source_type": "policy_document_dependency",
      "relationship_type": "instructs_manager",
      "explanation": "The manager guide documents approval responsibilities.",
      "impact_classification": "review_required",
      "source": {
        "object_type": "policy_rule_reference",
        "stable_key": "policy-international-travel-2026-09:MANAGER_APPROVAL_REQUIRED",
        "display_name": "MANAGER_APPROVAL_REQUIRED",
        "href": "/api/v1/policy-changes/policy-international-travel-2026-09/rule-references/MANAGER_APPROVAL_REQUIRED"
      },
      "target": {
        "object_type": "enterprise_document",
        "stable_key": "document-manager-travel-approval-guide",
        "display_name": "Manager Travel Approval Guide"
      },
      "trust": {
        "state": "persisted_typed_relationship",
        "integrity": [
          "policy_change_foreign_key",
          "enterprise_document_foreign_key",
          "semantic_uniqueness"
        ],
        "used_deterministically": true
      },
      "provenance": {
        "classification": "not_recorded",
        "creator": null,
        "owning_authority": null,
        "recorded_at": null,
        "approval": null
      }
    }
  ],
  "assessment_usage": {
    "statement": "The assessment service loads this policy-scoped dependency and the deterministic enterprise analyzer uses it to construct document impact, evidence, relationship path, and proposed-action output.",
    "changes_assessment_behavior": false
  }
}
```

For nullable fields, return `null` plus an explicit UI label `Not recorded`. Do not return guessed
values.

Success: `200 OK`.

Stable errors:

- `404 catalog_object_not_found`;
- `422 unsupported_catalog_object_type`;
- `409 catalog_projection_inconsistent` when a persisted relationship cannot resolve its policy
  or target.

### Policy rule reference endpoint

`GET /api/v1/policy-changes/{policy_change_id}/rule-references/{rule_code}`

Purpose: explain a policy-scoped dependency rule code and list the persisted dependency rows that
use it.

Representative response:

```json
{
  "stable_key": "policy-international-travel-2026-09:MANAGER_APPROVAL_REQUIRED",
  "policy": {
    "id": "policy-international-travel-2026-09",
    "title": "International Business Travel Approval and Security Training",
    "version": "1"
  },
  "rule_code": "MANAGER_APPROVAL_REQUIRED",
  "structured_rule_reference": {
    "field_path": "manager_approval",
    "label": "Manager approval rule",
    "mapping_status": "supported"
  },
  "relationships": [
    {
      "relationship_id": "dependency-policy-manager-guide",
      "relationship_type": "instructs_manager",
      "target_type": "enterprise_document",
      "target_id": "document-manager-travel-approval-guide",
      "target_name": "Manager Travel Approval Guide"
    }
  ],
  "authority_boundary": {
    "is_standalone_persisted_rule": false,
    "relationship_source": "persisted_dependency_rows",
    "assessment_use": "deterministic"
  }
}
```

Success: `200 OK`.

Stable errors:

- `404 policy_change_not_found`;
- `404 policy_rule_reference_not_found`;
- `409 catalog_projection_inconsistent`.

### Projection integrity rules

The projection must:

- query each supported source table explicitly;
- scope list queries by organization;
- preserve existing stable IDs;
- resolve every relationship endpoint;
- retain separate baseline and proposed dependency rows;
- use existing relationship row ordering by stable ID;
- return closed object-type and status-basis values;
- distinguish stored, normalized, and not-recorded values;
- fail with a stable integrity error instead of dropping broken relationships;
- perform no writes;
- avoid reading assessment evidence as current catalog state.

## Frontend routes and experience

### Routes

```text
/catalog
/catalog/[objectType]/[objectId]
/catalog/policy-rules/[policyChangeId]/[ruleCode]
```

The frontend route names are product-facing. The API continues to call the third resource a rule
reference to preserve the non-entity boundary.

### Navigation

The current application has page-specific headers and back links rather than a global navigation
shell. PR A should:

- add one clear secondary `Explore enterprise knowledge` link on the landing page;
- provide `Return to policy analysis` from the catalog;
- provide breadcrumb/back navigation from object and rule-reference details;
- avoid a broad navigation refactor across analysis, comparison, and approval pages.

### Catalog browse page

The browse page should:

- lead with the question `What enterprise knowledge does ChangeOps use?`;
- state that the current catalog is fictional seeded demonstration data;
- show primary catalog counts separately from compact assessment-context counts;
- allow category selection with ordinary links or buttons;
- show compact cards or rows with name, stable identity, available metadata, status, and
  relationship count;
- show workers, teams, and customer commitments in a secondary assessment-context summary without
  detail links;
- label missing values `Not recorded`;
- avoid search boxes, facets, pagination controls, and admin affordances.

Recommended category order:

1. Documents
2. Systems
3. Training

Workers, teams, and customer commitments belong in a visually secondary `Assessment context`
section after those categories.

### Object detail page

The detail page should use the current calm reviewer hierarchy:

1. business name and object type;
2. a compact metadata definition list;
3. a visible source/provenance boundary;
4. trusted relationships with business explanation;
5. `How ChangeOps uses this` explanation;
6. technical identity and database-integrity detail in native `<details>` disclosure.

Only documents, systems, and training courses receive this full detail experience in PR A.

For the Manager Travel Approval Guide, business-visible content should include:

- Document;
- Published;
- Acme Knowledge;
- version 2;
- owner not recorded;
- both baseline and proposed manager-approval relationships;
- `instructs_manager`;
- `review_required`;
- the persisted explanation;
- row-level provenance not recorded;
- deterministic assessment use.

### Rule-reference detail page

The rule-reference page should:

- lead with `MANAGER_APPROVAL_REQUIRED`;
- show the owning policy source and version;
- explain its current structured-rule mapping;
- state that it is a policy-scoped reference, not a standalone catalog row;
- list connected documents and systems for that policy;
- link back to each catalog object;
- distinguish dependency mapping from assessment findings that happen to reuse the same rule code.

### UX reuse

Reuse existing:

- Source Sans and IBM Plex Mono typography;
- color tokens and content width;
- `.product-mark`, `.eyebrow`, `.journey-card`, `.badge`, `.back-link`,
  `.technical-disclosure`, definition-list, and relationship-path visual language;
- progressive disclosure for raw identifiers and integrity basis;
- server-rendered initial reads and stable unavailable states.

Do not create a component library, graph visualization, canvas, node editor, or generic table
framework.

## Relationship-provenance representation

### PR A representation

PR A must separate three concepts:

1. **Catalog context** — the current bounded dataset is the canonical fictional seed.
2. **Trust basis** — a persisted typed relationship with foreign keys and deterministic analyzer
   use.
3. **Row provenance** — who/import/curation/approval information, currently not recorded.

Recommended response shape:

```json
{
  "trust": {
    "state": "persisted_typed_relationship",
    "integrity": ["target_foreign_key", "semantic_uniqueness"],
    "used_deterministically": true
  },
  "provenance": {
    "classification": "not_recorded",
    "creator": null,
    "owning_authority": null,
    "recorded_at": null,
    "approval": null
  }
}
```

Do not use `trusted` as a synonym for `human approved`. In the current model, the relationship is
trusted input because it is present in the typed source table and the analyzer consumes every
applicable row.

### PR C relationship-origin representation

After PR A and PR B are understood, PR C should make current seeded and future
human-curated/imported relationship origin explicit only where required, without weakening typed
foreign keys.

Minimum information under review:

- provenance category;
- owning authority or curator/import source;
- recorded timestamp;
- external source reference for imported metadata;
- human decision reference when a later approved proposal exists.

The closed product categories are:

- seeded demonstration data;
- imported authoritative metadata;
- human-curated mapping;
- human-approved AI proposal.

Only categories supported by real persisted lineage may be returned. PR C may implement seeded,
imported, and human-curated relationship-origin metadata. `human-approved AI proposal` must remain
unavailable until a later proposal-and-decision aggregate exists.

## Seed and reset implications

### PR A

No seed or reset change is required.

The existing seed already provides:

- 4 documents;
- 3 systems;
- 1 course;
- 12 worker records, including 6 managers;
- 4 teams;
- 2 customer commitments;
- 4 system dependencies across two policies;
- 6 document dependencies across two policies;
- 2 training dependencies across two policies.

The existing demo reset:

- truncates generated workflow and comparison history;
- preserves source/catalog and dependency rows;
- reruns the idempotent seed;
- requires the canonical organization marker and local safety confirmation.

Catalog pages should therefore render the same source records before and after reset. PR A tests
must prove this explicitly.

### PR B

PR B should:

- preserve stable seeded document IDs while adding or associating selected external Confluence
  page identities;
- keep fixture-backed import metadata deterministic in automated tests;
- make explicit/manual imports idempotent;
- preserve imported document metadata during ordinary workflow reset;
- keep seed-only fallback metadata honest when Confluence is not configured.

### PR C

PR C should:

- seed relationship-origin provenance only for rows the seed actually owns;
- keep source-specific baseline/proposed relationship IDs;
- make seed reruns idempotently refresh the same relationship provenance;
- preserve provenance-bearing source rows during demo reset;
- do not copy provenance into workflow tables merely for the catalog UI.

## Tests and quality gates

### Backend unit tests

Cover:

- closed object-type routing;
- deterministic category and object ordering;
- stored versus normalized versus not-recorded field representation;
- active-boolean status normalization without changing stored records;
- policy rule-code to structured-rule-reference mapping;
- unknown rule-code handling;
- relationship direction when viewed from source or target;
- no collapse of baseline/proposed dependency rows;
- trust-basis serialization;
- absence of invented owner or provenance.

### PostgreSQL integration tests

Cover:

- exact seeded category counts;
- separate primary catalog counts from worker, team, and commitment assessment-context counts;
- list filtering by organization and type;
- detail reads for documents, systems, and training courses;
- rejection of worker, team, and commitment detail requests;
- flagship Manager Travel Approval Guide response;
- both manager-guide dependency rows;
- exact relationship IDs, rule code, type, classification, and explanation;
- foreign-key endpoint resolution;
- stable integrity failure for a broken projection reference where a controlled fixture can
  simulate one;
- catalog reads before and after `reset_demo_workflows`;
- seed idempotency remains unchanged;
- catalog GET requests create no rows and change no assessment/source state;
- no assessment, finding, evidence, impact, action, review, command, or result is created by
  catalog access.

### API contract tests

Cover:

- `200` list and detail responses;
- stable ordering;
- query filtering;
- missing organization/object/policy/rule errors;
- unsupported type error;
- null metadata and explicit `not_recorded` semantics;
- complete relationship endpoint links;
- response schema rejects arbitrary object types, provenance claims, or relationship states;
- only GET routes exist.

### Frontend tests

Cover:

- landing-page catalog entry point;
- primary category counts and category selection;
- secondary worker, team, and commitment context counts without detail links;
- seeded-demonstration context remains visible;
- missing owner renders `Not recorded`;
- document stored source system and status render correctly;
- Manager guide relationship cards render baseline and proposed policy lineage;
- relationship follows to rule-reference page;
- rule reference follows back to the document;
- deterministic-use explanation is visible;
- technical details are collapsed by default;
- API unavailable, missing object, and integrity-error states;
- no edit, import, approve, refresh, AI-propose, or search control appears;
- narrow/mobile layout remains readable.

### Existing required gates

All current gates remain required:

- frontend typecheck;
- frontend lint;
- frontend Vitest suite;
- frontend production build;
- Ruff lint;
- Ruff format check;
- complete pytest suite against PostgreSQL;
- extraction evaluation;
- workflow evaluation;
- interpretation evaluation;
- approval-workflow evaluation;
- Alembic upgrade/downgrade/upgrade round trip;
- guarded demo reset.

No live AI, Jira, or Confluence call is required for this deterministic read-only slice.

## Explicit non-goals

Milestone 7 PR A does not include:

- Confluence integration or Confluence pages;
- importing or synchronizing external metadata;
- catalog object creation, editing, deletion, or administration;
- relationship creation, editing, deletion, or approval;
- AI relationship proposals;
- human approval of AI relationships;
- RAG;
- embeddings;
- vector search;
- document crawling or content ingestion;
- document bodies or excerpts;
- generic search infrastructure;
- graph database;
- generic knowledge graph tooling;
- a `catalog_objects` persistence abstraction;
- a polymorphic relationship table;
- metadata-schema builders;
- background or continuous synchronization, workers, queues, or webhooks;
- MCP;
- additional policy families;
- catalog state versioning or catalog-state comparison;
- assessment recalculation;
- changes to analyzer input, rules, classifications, evidence, paths, actions, fingerprints, or
  comparison behavior.

## Planned PR B — External document identity and read-only Confluence metadata

After PR A validates the catalog projection and reviewer experience, the next planned slice is a
bounded read-only Confluence integration for selected enterprise documents.

That slice may be stopped only if PR A demonstrates that real external document identity adds
insufficient reviewer, product, or architecture value. Missing metadata by itself is not a reason
to broaden Confluence scope, and the Confluence slice must still receive its own reviewed
implementation boundary before coding.

PR B owns:

- real Confluence page ID;
- space key or ID;
- canonical page URL;
- Confluence version;
- Confluence status;
- last-updated timestamp;
- source fingerprint;
- optional bounded excerpt or summary if separately justified;
- explicit/manual metadata import or refresh into PostgreSQL using read-only Confluence access;
- fixture-backed adapter tests;
- external link from ChangeOps to the actual page.

It must replace or enrich selected seeded document source metadata. It must not redefine catalog
identity, invent relationships, or make Confluence authoritative for assessments before imported
metadata is persisted in PostgreSQL.

PR B must not add relationship-origin categories, relationship approval state, relationship
editing, or AI relationship proposals. Existing typed dependency rows remain unchanged.

PR B preserves these explicit non-goals:

- broad crawling;
- RAG and embeddings;
- automatic relationship creation;
- Confluence editing/publishing;
- webhooks and continuous synchronization;
- arbitrary spaces or page inventories.

## Delivery recommendation

### PR A — Read-only catalog explorer

Approved and Codex-ready after this planning PR merges.

Scope:

- closed Pydantic catalog/read-reference schemas;
- explicit read-only projection service;
- three GET endpoints;
- API router registration;
- TypeScript types and API reads;
- `/catalog` browse page;
- object and rule-reference detail routes;
- landing-page entry link;
- backend, integration, API, and frontend tests;
- README, architecture, roadmap/inventory, demo-scenario, and decision documentation updates
  required by actual implementation.

Migration: none.

Review gate:

> Does the projection make the current enterprise-impact logic understandable while remaining
> honest about missing row provenance and owner metadata?

### PR B — Narrow external document identity and read-only Confluence metadata

Proceed after PR A review unless PR A demonstrates that real external document identity adds
insufficient value.

Scope remains limited to selected enterprise documents and the fields listed in
`Planned PR B — external document identity and read-only Confluence metadata`. It requires its own
implementation plan and review.

### PR C — Narrow relationship-origin provenance

Recommended only if the validated PR A and Confluence experiences show that missing persisted
relationship origin still materially blocks the reviewer story.

Likely scope:

- narrow provenance additions to the three typed policy dependency tables;
- canonical seed values;
- read-projection enrichment;
- migration round-trip, constraint, idempotency, reset, API, and UI tests;
- a new ADR for the accepted provenance persistence decision.

PR C must receive a concrete schema review before coding. It must not add AI proposals, Confluence
import behavior, external document identity changes, unrelated external imports, or a generic
catalog layer.

## Acceptance criteria for PR A

- [ ] A reviewer can browse documents, systems, and training courses as the three primary catalog
      categories.
- [ ] Workers, teams, and customer commitments are visible as compact assessment-context counts
      without dedicated detail routes.
- [ ] Existing stable object identities are visible and reused.
- [ ] Stored names, descriptions, source systems, and statuses are shown where they exist.
- [ ] Missing owner, description, source, status, and row-provenance values are labeled
      `Not recorded`.
- [ ] The current seeded-demonstration catalog context is explicit and is not misrepresented as
      per-row import provenance.
- [ ] The Manager Travel Approval Guide detail shows its stable ID, document type, Acme Knowledge
      source system, version, and published status.
- [ ] The Manager guide shows both baseline and proposed `instructs_manager` dependencies.
- [ ] A reviewer can follow the baseline dependency to
      `MANAGER_APPROVAL_REQUIRED`.
- [ ] The rule-reference view explains that the rule is policy-scoped and not a standalone stored
      rule entity.
- [ ] The relationship view distinguishes trust basis from missing row provenance.
- [ ] The relationship view explains its deterministic assessment use.
- [ ] All catalog endpoints are read-only.
- [ ] Catalog access creates no workflow or assessment artifact.
- [ ] Existing assessment behavior and golden counts remain unchanged.
- [ ] Demo reset preserves and re-renders the same catalog.
- [ ] All existing and new quality gates pass.
- [ ] No migration or new runtime dependency is introduced.
- [ ] No Confluence, AI proposal, graph, RAG, search, editing, synchronization, or MCP scope is
      introduced.

## Exit criteria for the complete reviewer objective

PR A proves the model and traversal. The complete objective is met when a reviewer can also see
persisted, honest row-level metadata for the required claims.

Before declaring the entire enterprise-knowledge foundation complete:

1. review PR A;
2. complete PR B, unless PR A demonstrates that real external document identity adds insufficient
   value;
3. decide and implement only the narrowly necessary PR C relationship-origin fields.

PR C should address only requirements that remain unsatisfied, such as:

- persisted Manager guide owner;
- persisted relationship source category;
- persisted owning authority and timestamp;
- clear distinction among seeded, imported, and human-curated mappings;
- future-safe deferral of human-approved AI proposals until real proposal/decision lineage exists.

## Risks and mitigations

### Risk: a read projection becomes a second system of record

Mitigation: persist no catalog read model, IDs, status, or relationships in PR A. Query current
typed source tables on every request.

### Risk: source-system labels are mistaken for import provenance

Mitigation: present `source_system` and `record_provenance` as separate fields.

### Risk: foreign-key integrity is described as human approval

Mitigation: present trust basis and provenance independently.

### Risk: rule codes are presented as standalone stored entities

Mitigation: call them policy-scoped rule references and expose the structured mapping boundary.

### Risk: baseline and proposed dependencies are accidentally deduplicated

Mitigation: preserve relationship row ID and policy ownership in ordering, response, UI, and tests.

### Risk: missing metadata leads to hard-coded demo values

Mitigation: render `Not recorded`; add values only through an approved PostgreSQL migration and
seed update.

### Risk: catalog work expands into generic platform infrastructure

Mitigation: closed object types, explicit queries, three GET endpoints, bounded demo counts, no
generic persistence, and the explicit non-goals above.

## Codex-ready implementation handoff — PR A

### Task

Implement the read-only Enterprise Knowledge Catalog Explorer exactly within PR A scope after this
planning PR merges.

### Required inspection before editing

Re-read:

- this milestone;
- `CONTRIBUTING.md`;
- current `src/changeops/db/models.py`;
- current seed and demo-reset services;
- current assessment loading, evidence, and enterprise-impact traversal;
- current journey/workbench projection patterns;
- current frontend routes, types, API helpers, CSS, and tests;
- current Alembic head and CI gates.

### Backend work

1. Add a closed catalog schema module.
2. Add a read-only projection service with explicit detail queries for documents, systems, and
   training courses plus compact worker, team, and commitment counts.
3. Add a small closed policy rule-reference mapping for current rule codes.
4. Resolve typed relationships in both directions for object detail.
5. Keep baseline and proposed policy dependency rows distinct.
6. Return explicit stored/normalized/not-recorded metadata basis.
7. Return trust basis separately from row provenance.
8. Fail closed on missing relationship endpoints.
9. Add a read-only API router for the three approved GET endpoints.
10. Register the router in the existing FastAPI application.
11. Do not add a migration, write method, dependency, AI call, or assessment query as catalog
    authority.

### Frontend work

1. Add TypeScript response types matching the closed backend contract.
2. Add server-side API helpers with `cache: "no-store"`.
3. Add `/catalog`.
4. Add `/catalog/[objectType]/[objectId]`.
5. Add `/catalog/policy-rules/[policyChangeId]/[ruleCode]`.
6. Add one secondary landing-page link into the catalog.
7. Do not create worker, team, or customer-commitment detail pages in PR A.
8. Reuse current visual and progressive-disclosure patterns.
9. Render `Not recorded` for null metadata.
10. Keep technical IDs and integrity detail collapsed by default.
11. Add stable loading/unavailable/error states.
12. Add no edit, search, refresh, import, AI, relationship, or approval controls.

### Required proof

Automated proof must show:

- exact document, system, and training-course catalog counts;
- exact worker, team, and commitment assessment-context counts without detail routes;
- exact Manager guide metadata;
- both Manager guide dependency rows;
- the baseline `MANAGER_APPROVAL_REQUIRED` rule reference;
- trust/provenance separation;
- reset preservation;
- no database writes;
- unchanged golden assessment counts and behavior;
- complete existing quality-gate success.

### Documentation on implementation

Update only documentation made stale by the implementation:

- `README.md`;
- `docs/architecture.md`;
- `docs/roadmap.md`;
- `docs/remaining-work-inventory.md`;
- `docs/demo-scenario.md`;
- `docs/decisions.md` only if implementation makes a new accepted architectural decision.

Do not mark row-level provenance complete in any document after PR A.

### Stop conditions

Stop and request review if implementation appears to require:

- any schema change;
- a `catalog_objects` table or generic graph abstraction;
- inferred owner or provenance values;
- changes to assessment behavior;
- Confluence or another external system;
- relationship writes or AI proposals;
- search, crawling, RAG, embeddings, background work, or MCP.

## Approval record

The repository analysis and projection-first architecture are approved.

The approved implementation sequence is:

1. PR A — read-only explorer over existing typed tables, with no migration;
2. PR B — narrow external document identity plus read-only Confluence metadata import and links;
3. PR C — relationship-origin provenance, only as narrowly required.
