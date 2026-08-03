Architectural Decisions
* Modular monolith, not microservices.
* FastAPI backend.
* PostgreSQL persistence.
* Deterministic impact matching first.
* LLM extraction comes after the expected policy structure works.
* LangGraph is introduced only when the workflow has multiple meaningful states.
* No frontend in Milestone 0.
* No MCP or simulated enterprise APIs yet.
* No approval execution yet.

# ADR-0007 — Delay AI Until Enterprise Context Exists

## Status

Accepted

## Context

ChangeOps is intended to demonstrate both enterprise software architecture and practical AI engineering.

Earlier project planning introduced LLM-based policy extraction immediately after the deterministic impact assessment.

As the product matured, the project evolved from demonstrating AI technologies to demonstrating an enterprise change-management platform that uses AI where appropriate.

This raised an architectural question:

Should AI be introduced immediately after the deterministic policy assessment, or should deterministic enterprise context be established first?

## Decision

ChangeOps will establish deterministic enterprise impact discovery before introducing AI workflows.

Milestone 1 expands deterministic analysis across multiple enterprise domains, including:

- people
- teams
- systems
- documentation
- training
- customer commitments

These relationships are represented explicitly using normalized enterprise data and deterministic business rules.

Milestone 2 introduces AI to perform tasks that require interpretation rather than deterministic evaluation, including:

- extracting structured policy changes from natural language
- identifying ambiguity
- synthesizing evidence across domains
- generating recommendations
- coordinating multi-step workflows

AI is intentionally not responsible for determining known enterprise relationships or applying deterministic business rules.

## Consequences

### Positive

- Clear separation between deterministic and probabilistic reasoning.
- Easier testing and regression verification.
- Explainable enterprise impact analysis.
- Stronger architectural justification for LangGraph.
- AI operates on trusted enterprise context rather than raw operational data.
- Better demonstration of enterprise software design.

### Negative

- AI capabilities appear one milestone later.
- Milestone 1 requires additional enterprise modeling before LLM features become visible.

## Alternatives Considered

### Introduce AI immediately after Milestone 0

Pros

- Earlier demonstration of LangChain and LangGraph.
- Faster visible AI functionality.

Cons

- AI introduced before a clear architectural need.
- Deterministic engine becomes little more than preprocessing.
- Weaker explanation of why workflow orchestration is required.

## Rationale

ChangeOps is intended to demonstrate thoughtful engineering decisions rather than maximum technology usage.

Technologies should enter the architecture only when they solve a demonstrated product problem.

Establishing deterministic enterprise context first produces a stronger foundation for later AI planning, approval workflows, execution, and auditing.

# ADR-0008 — Use Typed Relational Dependencies and Immutable Impact Paths

## Status

Accepted

## Context

Milestone 1 must explain impacts across several enterprise domains without introducing a graph
database or an opaque assessment payload.

## Decision

ChangeOps uses ordinary PostgreSQL relationships for the scoped enterprise context:

- workers reference manager workers;
- worker-team memberships connect workers and teams;
- customer assignments connect workers and commitments;
- separate policy-system, policy-document, and policy-training tables preserve target foreign keys.

Completed assessments store enterprise impacts as relational rows. Evidence uses a join table, and
each relationship path is stored as ordered path-element rows. Cross-domain proposed actions link
to their impact and retain `execution_status = not_executed`.

The existing pure worker analyzer remains intact. A second pure enterprise-impact analyzer consumes
immutable typed input, and the application service coordinates both after loading all source data.

## Consequences

- Target integrity remains enforceable with foreign keys.
- Impact records, evidence, paths, and actions remain directly queryable.
- Historical paths do not change when source relationships later change.
- Adding a new dependency target requires an explicit table and analyzer rule.
- The design intentionally does not provide a generalized enterprise graph or rules engine.

## ADR-0009: Separate AI Language Understanding and Interpretation from Deterministic Impact Analysis

**Status:** Accepted  
**Date:** 2026-08-01

### Context

ChangeOps must analyze policy and operational changes while preserving explainability, reproducibility, auditability, and human control.

Milestone 1 established a deterministic enterprise impact-analysis engine. Given validated policy rules and the same enterprise data, it produces the same immutable assessment, including impacts, evidence, reason codes, relationship paths, and proposed actions.

Milestone 2 introduces AI for work that deterministic software cannot perform reliably from unstructured language alone. The architecture must demonstrate structured extraction, ambiguity handling, evidence-grounded interpretation, durable workflows, and human clarification without allowing an LLM to become the authoritative source for enterprise facts, relationships, or impact conclusions.

The workflow must also support a policy analysis run that pauses for human clarification and resumes later, potentially in a different process. A workflow run can therefore exist without an impact assessment and may terminate without producing one.

### Decision

ChangeOps will use a policy-analysis pipeline in which AI owns **language in** and **interpretation out**, and owns nothing in between.

```text
policy text
    ↓
AI policy understanding
    ↓
candidate typed rules, source provenance, and open questions
    ↓
deterministic validation and clarification gate
    ↓
validated policy rules
    ↓
deterministic enterprise impact analysis
    ↓
immutable impact assessment
    ↓
AI interpretation of the persisted assessment
    ↓
separate change-plan artifact
    ↓
human review
```

Four principles govern every AI step:

1. **AI assists; deterministic code decides.**
2. **AI output remains proposed until validated.**
3. **Every AI claim must reference existing source text, evidence, or assessment records.**
4. **Every AI step must have a test or evaluation that can fail.**

### AI responsibilities

The policy-understanding step may:

- extract candidate typed policy rules from policy text;
- identify ambiguity, missing information, and unsupported policy constructs;
- attach source-text provenance to extracted fields and open questions.

The interpretation step may:

- identify coverage gaps in the deterministic assessment;
- identify residual risks or conflicts grounded in the policy and assessment;
- synthesize related findings across impact domains;
- explain findings in human-readable form.

The extraction and interpretation roles must remain separate.

The extractor receives policy text but not workers, trips, training records, enterprise relationships, or other source-table context.

The interpreter receives the policy text and completed immutable assessment but does not query enterprise source tables directly.

### Responsibilities retained by deterministic code

AI must not:

- decide whether an enterprise object is affected;
- add, remove, or reclassify impacts;
- create impact domains, classifications, reason codes, action types, or evidence keys;
- create or alter enterprise facts or relationships;
- perform authoritative date arithmetic, filtering, overlap calculations, counting, or ordering;
- generate identifiers, fingerprints, or stable sort keys;
- perform schema, enum, referential, or business-rule validation;
- control workflow transitions, retries, completion, or clarification bypass;
- approve recommendations or execute actions against enterprise systems.

The deterministic impact engine remains authoritative and unchanged below the validated-rules boundary.

### Validation and grounding

AI-generated policy rules are candidate data until they pass:

- structured-output validation;
- closed-enum validation;
- business-rule validation;
- referential resolution;
- supported-policy validation.

An unsupported or unrepresentable policy must fail closed rather than be coerced into the current schema.

AI interpretation is stored separately from the immutable impact assessment. The model cites exact
policy quotes and existing impact IDs or evidence keys; deterministic code constructs span offsets,
lifecycle IDs, and evidence ownership. Every resulting reference must resolve against the persisted
assessment before the interpretation artifact is accepted.

The model may reference existing evidence but may not create authoritative evidence.

### Human clarification

AI may identify that clarification is needed, but deterministic code decides whether the workflow pauses.

Human clarification is treated as an explicit workflow input, not as an informal conversation. It must be persisted with provenance and used when validating the resulting policy rules.

Because clarification can change the validated rules and therefore the resulting assessment, material clarification must be included in the traceability and fingerprinting model defined by Milestone 2.

### Workflow orchestration

LangGraph is used for declarative workflow topology, typed orchestration state, conditional
routing, and explicit node and transition boundaries. It is not an autonomous agent framework or
the durable system of record.

PostgreSQL persists policy-analysis lifecycle state, extraction attempts, clarification records,
artifacts, and audit data. Both graphs are compiled without a LangGraph checkpointer. A resumed
analysis is a fresh graph invocation whose initial route is derived deterministically from those
records; it does not resume an opaque checkpoint thread.

Workflow routing is implemented in code. Model output may be an input to a routing decision, but
the model is never the router.

The current workflow could be expressed as sequential Python over the same persisted state.
LangGraph is retained because its explicit topology and transition model improve explainability,
separation of orchestration from business rules, inspection, and maintainable extension. This is a
tradeoff, not a claim that cross-process durability requires LangGraph.

A workflow run and an impact assessment have separate lifecycles. A run may be paused, unsupported, failed, abandoned, or completed without an assessment. A completed run may reference the assessment it produced.

### Evaluation

Evaluation responsibilities are separated by architectural layer:

- **Grounding and referential integrity** are deterministic assertions and must fail tests when references do not resolve.
- **Required CI contract evaluations** replay fixed model outputs and deterministic cases to protect
  structured-output, routing, lifecycle, provenance, grounding, and fail-closed behavior. They do
  not measure live provider accuracy.
- **Live provider verification** is a manually dispatched, non-gating smoke of the canonical
  extraction and interpretation path. It checks provider compatibility and end-to-end invariants,
  not comprehensive model quality.

No conclusion may be jointly owned by the deterministic engine and an AI step.

### Consequences

#### Positive

- The deterministic impact engine remains reproducible, explainable, and diffable.
- AI is used only where language understanding or interpretation provides real value.
- Invented impacts cannot enter the authoritative assessment through the AI layer.
- Extraction and interpretation can be evaluated independently.
- Human clarification is traceable and resumable.
- The architecture provides a defensible reason for using LangGraph.
- Immutable assessments remain unchanged by later AI interpretation.
- AI outputs can be rerun against a fixed assessment without recomputing deterministic impacts.

#### Negative

- The system requires separate persistence models for workflow runs, AI extraction results, human clarifications, and interpretation artifacts.
- The deterministic guarantee becomes: the same validated rules and enterprise data produce the same assessment. It does not extend to raw policy text producing identical extracted rules across model or prompt versions.
- Extraction runs must record model, prompt, and schema versions.
- The supported policy schema remains intentionally narrow, and unsupported policies must terminate without an assessment.
- The workflow is more complex than a synchronous request/response operation.

### Alternatives considered

#### AI extraction only

Rejected because structured extraction alone leaves reviewers with an impact list but no grounded explanation of coverage gaps, residual uncertainty, or cross-domain concerns.

#### Full AI orchestrator

Rejected because allowing an LLM to own extraction, impact reasoning, workflow control, and recommendations would undermine the deterministic engine and make authoritative conclusions non-reproducible.

#### Single AI agent with database tools

Rejected because it would allow policy extraction to become influenced by enterprise outcomes and would allow interpretation to bypass the immutable assessment aggregate.

#### Sequential Python workflow without LangGraph

Viable: PostgreSQL already provides the required persistence and cross-process recovery. Retaining
LangGraph adds an explicit, inspectable topology and conditional transition model at the cost of
another framework. Reconsider this choice if the graph stops improving explainability or
maintainability relative to straightforward sequential orchestration.

### Follow-up decisions

`docs/milestone-2.md` will define:

- the supported `international_travel` extraction scope;
- extraction-result and workflow-run schemas;
- clarification-gate rules;
- human-input provenance and fingerprinting;
- LangGraph state and node boundaries;
- retry and failure behavior;
- interpretation scope for Milestone 2;
- LangChain usage;
- prompt and model versioning;
- evaluation datasets, rubrics, and thresholds.

# ADR-0010 — Separate Immutable Action Review from Proposed Actions

## Status

Accepted

## Context

Milestone 3 must record consequential human decisions without rewriting the immutable assessment
that explains what the system originally proposed. Approval fields on `proposed_actions` would
combine historical analysis with a later human workflow and would lose the distinction between
original and edited values.

## Decision

ChangeOps uses a separate item-level action-review aggregate:

- one review per proposed action;
- a versioned immutable original-action snapshot;
- a small evidence-context snapshot;
- zero or one append-only decision event in the first slice;
- a persisted review status that must match its decision;
- optional typed description and due-date edits only for approval;
- a derived effective approved action rather than an executable record.

PostgreSQL composite foreign keys, uniqueness constraints, row locks, mutation triggers, and
deferred lifecycle constraint triggers enforce the aggregate. Reviewer identity is copied from a
narrow request-header authorization context. The proposed action is never updated.

## Consequences

- Original recommendations and reviewer edits remain independently auditable.
- Concurrent decisions have exactly one database winner.
- Later execution can consume an effective approved snapshot without treating the assessment as
  mutable.
- The first slice deliberately permits only one terminal decision and has no reopening or
  supersession semantics.
- Request headers demonstrate an authorization boundary but must be replaced by production
  authentication before external deployment.

# ADR-0011 — Separate Durable Approval Run from Completed Policy Analysis

## Status

Accepted

## Context

Policy analysis completes when it persists one immutable deterministic assessment. Human review can
begin much later, pause repeatedly, and fail independently. Reopening the completed analysis run or
inferring approval membership forever from all reviews would combine two business lifecycles and
make historical workflow scope unstable.

## Decision

ChangeOps uses one approval-specific aggregate per completed policy-analysis assessment:

- `ActionApprovalRun` stores lifecycle state, current step, deterministic counts, failure state, and
  timestamps;
- `ActionApprovalRunItem` snapshots ordered proposed-action and action-review membership;
- `ActionApprovalRunTransition` stores append-only transition visibility;
- a narrow deterministic LangGraph initializes membership, evaluates persisted reviews, ends at
  each human wait state, and completes when no item is pending;
- PostgreSQL remains authoritative, and each invocation starts from the persisted run ID;
- a committed review decision triggers synchronous post-commit resume, while an authorized
  idempotent endpoint provides explicit reconciliation.

The existing item-level review owns decisions and action snapshots. The approval run duplicates
neither. The completed policy-analysis run and impact assessment are never changed.

## Consequences

- Approval waiting and progress survive API restart without a worker, queue, scheduler, polling
  loop, or open HTTP request.
- Stable membership and transition records make the assessment-level process auditable.
- Row locking plus deterministic recalculation reconciles concurrent decisions safely.
- Automatic-resume failure cannot erase a valid human decision.
- All terminal decision types complete workflow items, but only approval may become a candidate for
  future execution.
- This slice adds approval-specific orchestration rather than a generic workflow platform.
- No action executes, and demonstration authorization headers still require replacement before
  public deployment.

# ADR-0012 — Add a Read-Only Approval Workbench Projection

## Status

Accepted

## Context

The reviewer screen needs approval lifecycle data, full item snapshots, deterministic finding or
enterprise-impact context, resolved evidence, and ordered relationship paths. Making the browser
assemble these resources would duplicate reference validation and workflow ordering outside the
backend ownership boundary.

## Decision

The frontend consumes one screen-oriented deterministic projection:
`GET /api/v1/action-approval-runs/{run_id}/workbench`.

- The projection reuses persisted domain records and existing run/review serializers.
- Immutable approval membership determines item order.
- Every evidence and context reference must resolve or the endpoint returns a stable inconsistency
  error.
- Domain write APIs for run creation, decisions, and manual resume remain unchanged.
- No durable workbench aggregate or snapshot is created.
- This is a focused application projection, not a generic backend-for-frontend framework.

## Consequences

- Initial server rendering can load one coherent reviewer representation.
- The backend remains authoritative for validation, ordering, progress, provenance, and effective
  approved-action derivation.
- Read retrieval performs no database mutation.
- The frontend can refresh after writes without reproducing approval transition logic.
- A future screen with materially different needs may require its own explicit projection rather
  than expanding this endpoint into generic query infrastructure.

# ADR-0013 — Materialize Immutable Execution Commands Before Tool Invocation

## Status

Accepted

## Context

An approved review currently proves what a person decided, but deriving connector input only at
execution time would make historical authorization depend on later application mapping code.
Allowing an MCP tool or adapter to derive action semantics would also couple integrations to review
serialization, assessment-era schemas, and approval workflow internals.

## Decision

ChangeOps materializes a separate immutable execution command before any tool invocation:

- command construction is pure and deterministic;
- the command snapshots exact effective approved values;
- a separate versioned snapshot stores connector-neutral parameters;
- relational provenance links the command to run, review, approval decision, proposed action, and
  assessment;
- canonical semantic JSON plus the approval decision produces a SHA-256 idempotency key;
- one command may exist per approved review;
- unsupported approved actions are explicit projection results;
- command rows are immutable and remain `pending_execution`;
- preparation runs synchronously in the modular monolith and changes no enterprise state.

The first mapping supports only seeded learning assignments. MCP and simulated adapters will
consume the stable command contract in later slices. This decision introduces neither a queue nor
a generic command bus, adapter registry, or preparation workflow.

## Consequences

- Approval and deterministic execution authorization are independently auditable.
- Future mapping-code changes cannot rewrite already prepared commands.
- Repeated and concurrent preparation reuses the same semantic command.
- Connectors can focus on current-state validation and invocation rather than deciding approval
  semantics.
- The system gains a table, migration, API projection, and lifecycle boundary before execution.
- Unsupported recommendations stay visible instead of being silently skipped or falsely treated
  as executable.
- No MCP tool, simulated system, or external service is called in this slice.

# ADR-0014 — Validate the Command Boundary with One In-Process Learning Adapter

## Status

Accepted

## Context

The immutable execution-command boundary must be proven by a real consumer before ChangeOps adds
MCP or generalized connector infrastructure. The seeded training command already contains an
approved worker, fixed course identifier, closed operation and system, canonical idempotency key,
and complete assessment and approval lineage. Execution additionally needs durable side-effect
state and immutable attempt metadata, but those are not command concerns.

## Decision

ChangeOps executes only `learning.assign_training` through one explicit synchronous
`SimulatedLearningAdapter` inside the modular monolith.

- Execution requires an explicit authorized `admin` request.
- The application service row-locks the command and revalidates persisted approval lineage and
  exact command semantics.
- The adapter validates a closed payload and verifies the worker and active course.
- One `SimulatedLearningAssignment` records durable simulated enterprise state.
- Every adapter attempt records a separate immutable `ExecutionResult`.
- Assignment and success result commit in one PostgreSQL transaction.
- One assignment per source command is enforced by a database uniqueness constraint.
- Repeated requests append `already_applied` results referencing the original assignment.
- Commands, proposed actions, and approval records remain unchanged.

No adapter registry, generic connector interface, command bus, queue, retry framework, background
worker, or workflow engine is introduced.

## Consequences

- The existing command contract is validated without modification.
- Approval remains necessary but is not inferred by the adapter.
- Concurrent duplicate requests cannot create duplicate assignments.
- Enterprise state and execution audit history have distinct persistence models.
- Unsupported commands and malformed payloads have explicit deterministic outcomes.
- The slice remains synchronous and intentionally supports only one operation.
- A later MCP decision can be based on demonstrated transport or process-boundary needs rather
  than anticipated abstraction.

## Why MCP is not introduced

MCP would add protocol, tool-hosting, and process-boundary concerns without improving this first
consumer's product behavior. The architectural question is whether an immutable command can safely
drive an approved, idempotent side effect. An in-process adapter answers that question directly.
MCP remains a possible later transport when multiple external tool providers or a genuine
cross-process integration boundary makes it useful.

# ADR-0015 — Project Authoritative Analysis Uncertainty

## Status

Accepted

## Context

Uncertainty currently has two unrelated lineages. The policy-analysis workflow persists
model-proposed extraction findings and bounded `policy_analysis_clarifications`. Separately, the
Milestone 0 seed creates eight `PolicyChangeQuestion` rows, and every assessment copies them into
`assessment_unresolved_questions`.

The copied questions have no independent effect on validation, workflow routing, impact analysis,
approval, or execution. They are nevertheless part of the assessment fingerprint, immutable
historical aggregates, the assessment response, interpretation input, golden-scenario assertions,
and the manual live smoke. The response name does not reveal that they are seed fixtures, so an API
consumer may infer that a completed AI run detected them.

## Decision

Extraction findings and persisted clarification records are authoritative for current
policy-analysis uncertainty and human resolution. The copied assessment questions are classified
as a legacy schema-v1 scenario fixture, not AI-derived uncertainty.

The historical assessment endpoint will not delete, rename, or reinterpret the field. The
product-facing policy-analysis journey instead provides an additive screen-oriented projection
that exposes extraction findings and clarification history from their authoritative persisted
records. Its assessment sub-projection omits `unresolved_questions` and explicitly classifies the
legacy field as an omitted schema-v1 fixture.

The projection reads workflow lineage and current immutable artifacts; it does not rewrite
completed assessments, copy clarification data, persist screen snapshots, or become another
system of record.

## Consequences

- Existing database rows, fingerprints, API consumers, and historical assessments remain stable.
- Existing clients of the historical assessment response can still misread
  `unresolved_questions` unless they follow the documented schema-v1 limitation.
- The product-facing journey cannot misrepresent those fixtures because they are absent from its
  assessment sub-projection and its uncertainty lineage is explicit.
- Tests that assert eight questions remain regression tests for the legacy seeded scenario, not
  model-quality assertions.

# ADR-0016 — Enrich the Existing Journey Read Model and Reset Workflow State In Place

## Status

Accepted

## Context

Immutable interpretation references are audit-friendly but raw UUIDs and evidence keys are not
reviewer-friendly. The journey also needs accurate presentation of clarification, approval,
command, execution, and replay state. A repeatable demo must remove generated history without
destroying or duplicating the stable fictional enterprise catalog.

## Decision

- Resolve plan citations in the existing journey projection against the same persisted assessment
  and policy snapshot; retain every original identifier and key.
- Fail with a stable integrity response when an accepted reference is missing, cross-assessment, or
  not owned by its cited impact or finding.
- Derive the seven fixed frontend step states with one pure function rather than introducing a
  workflow UI framework.
- Derive execution summary values from persisted approval runs, commands, and results without
  persisting UI state.
- Reset an explicit list of workflow-owned tables transactionally, preserve the source catalog,
  and require local-target, confirmation, and organization-marker safety guards.
- Keep the provider-free historical assessment seed available to tests but remove it from ordinary
  application startup so reviewers begin at the policy.

## Consequences

- Reviewers can understand lineage without sacrificing audit identifiers.
- The projection performs stricter integrity checks but remains read-only.
- Approval completion cannot be mistaken for command preparation or execution.
- The reset is repeatable and safer than dropping the Compose volume, but it is intentionally
  limited to the recognized local demo database.
- No table, workflow engine, state library, scenario manager, adapter, or deployment technology is
  introduced.
