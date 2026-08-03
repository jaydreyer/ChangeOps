# Milestone 5A — Policy-Version Comparison Foundation

## Status

Approved for implementation.

This document defines the next ChangeOps vertical slice after completion of the local end-to-end policy-analysis, approval, command-preparation, controlled-execution, lineage, and demo-readiness journey.

This milestone document is the authoritative implementation scope for the policy-version comparison foundation.

If this document conflicts with the broader feature-expansion roadmap, this narrower milestone document governs implementation of this slice.

---

## Product capability

Allow a reviewer to compare the accepted, validated rules of:

- one current international-travel policy; and
- one proposed revision of that policy.

ChangeOps will deterministically identify which supported policy obligations changed and preserve exact lineage to both policy versions.

This milestone answers:

> What validated policy obligations changed between the current policy and the proposed revision?

It does not yet answer:

> How did the affected workers, systems, documentation, training, customer commitments, or proposed actions change?

Enterprise impact delta is intentionally deferred to the next vertical slice.

---

## Product rationale

The current ChangeOps journey analyzes one policy and determines its enterprise impact.

That is a coherent and governed workflow, but it does not yet model the central change-management question implied by the product:

> What changed from the policy currently in effect?

Adding policy-version comparison makes the product more useful and differentiated without adding another policy family, execution adapter, or infrastructure technology.

This slice establishes the trusted comparison foundation before any attempt to compare assessments or enterprise impacts.

---

## User outcome

A reviewer can:

1. identify a current policy and a proposed revision;
2. initiate or retrieve a comparison;
3. see which validated policy rules were added, removed, or modified;
4. inspect the current and proposed values;
5. inspect provenance to both policy versions;
6. understand whether each semantic difference is operationally material;
7. repeat the same comparison without creating duplicate comparison artifacts.

The reviewer should be able to understand the comparison without inspecting source code, database tables, or raw model output.

---

## Supported scenario

This milestone supports only the existing flagship domain:

```text
policy_family = international_travel
schema_version = 1
```

Both policy versions must:

- belong to the same organization;
- be distinct policy records;
- use the same supported policy family;
- use the same supported rule-schema version;
- have an accepted extraction attempt;
- have deterministically validated and resolved typed rules;
- have no unresolved material clarification blocking acceptance.

Unsupported or inconsistent comparisons must fail closed.

No additional policy family is introduced.

---

## Product flow

```text
Current policy
        +
Proposed policy revision
        ↓
Accepted validated rules for each version
        ↓
Deterministic compatibility validation
        ↓
Deterministic semantic rule comparison
        ↓
Immutable policy comparison
        ↓
Human-readable comparison view
```

AI is not used for comparison.

The existing extraction boundary may be used independently to produce candidate typed rules for each policy, but only accepted and deterministically validated rules may enter the comparison.

---

## Architectural boundaries

### AI owns

For each individual policy version, existing AI capabilities may continue to own:

- extraction proposals;
- source-language interpretation;
- ambiguity identification.

AI does not own comparison.

### Deterministic code owns

- policy compatibility validation;
- authoritative accepted-extraction resolution;
- typed rule comparison;
- rule identity;
- change classification;
- materiality classification;
- stable reason codes;
- stable ordering;
- canonical fingerprints;
- idempotency;
- persistence;
- API lifecycle;
- provenance validation.

### Humans own

- selecting the intended current policy;
- selecting the proposed revision;
- initiating the comparison;
- interpreting the comparison in its business context.

### PostgreSQL owns

- authoritative policy-version records;
- accepted extraction lineage;
- immutable comparison records;
- immutable rule-difference records;
- durable idempotency constraints.

### LangGraph

LangGraph is not required for this milestone.

Policy comparison is a synchronous deterministic operation with no human interruption, retry lifecycle, long-running wait state, or branching workflow that benefits from a graph.

Do not introduce a policy-comparison graph.

---

## Semantic comparison boundary

The comparison operates on accepted typed policy semantics.

It does not compare raw documents, paragraphs, sentences, token sequences, or embeddings.

The comparator must inspect the actual fields represented by the current `InternationalTravelPolicyRules` domain model.

Comparable semantics may include, where represented by the current schema:

- policy effective date;
- covered worker locations;
- covered employment types;
- applicable travel conditions;
- required training;
- manager-approval requirements;
- booking restrictions;
- pre-effective-date booking exemptions.

The implementation must use the current rule model as the source of truth and must not invent unsupported policy concepts.

---

## Change classification

Each persisted semantic difference must use a closed change classification.

Supported classifications:

- `added`
- `removed`
- `modified`

Unchanged fields should not be persisted by default.

An implementation may include unchanged fields in a read projection only if doing so materially improves reviewer comprehension without expanding the persisted comparison aggregate.

---

## Materiality

Materiality is deterministic and limited to the supported typed schema.

A changed validated operational rule is normally operationally material.

Examples include:

- a changed effective date;
- expanded or reduced worker coverage;
- a changed employment-type scope;
- a changed training requirement;
- a changed approval requirement;
- a changed booking restriction;
- a changed exemption.

A wording or provenance change that produces identical accepted typed semantics is not an operational policy-rule change.

This milestone does not claim to determine arbitrary legal, regulatory, editorial, or organizational materiality.

It determines materiality only within the supported international-travel rule contract.

---

## Provenance

Every difference must preserve lineage to both versions where applicable.

Baseline provenance should identify:

- baseline policy;
- baseline accepted extraction attempt;
- baseline semantic value;
- baseline source evidence or span already validated by the extraction boundary.

Proposed provenance should identify:

- proposed policy;
- proposed accepted extraction attempt;
- proposed semantic value;
- proposed source evidence or span already validated by the extraction boundary.

The comparison must not fabricate source spans.

A provenance reference must resolve against the policy version and extraction attempt that owns it.

Missing or cross-owned provenance must produce a stable integrity failure rather than being silently omitted.

---

## Persistence requirements

The implementation must introduce the smallest immutable relational aggregate that satisfies the product capability.

The expected aggregate contains:

- one policy-comparison record;
- ordered semantic-difference child records;
- references to both policy versions;
- references to both authoritative accepted extraction attempts;
- organization ownership;
- comparison schema or contract version;
- canonical comparison fingerprint;
- creator identity;
- creation timestamp.

Exact table, model, and field names must follow existing repository conventions.

### Required invariants

- baseline and proposed policy identifiers differ;
- both policies belong to the same organization;
- both policies use the same supported family and schema;
- each extraction attempt belongs to its referenced policy;
- each extraction attempt is accepted;
- both rule representations are fully resolved;
- equivalent repeated comparison requests return or reuse the same semantic comparison;
- completed comparison artifacts cannot be updated;
- source-policy or enterprise-data changes do not rewrite an existing comparison;
- persisted difference ordering is stable.

Use database constraints, uniqueness constraints, foreign keys, and immutability protections where they provide meaningful durable enforcement.

Do not create a generic audit-event table.

---

## Domain requirements

The semantic comparator must be pure deterministic domain code.

It must not depend on:

- FastAPI;
- SQLAlchemy;
- LangChain;
- LangGraph;
- a model provider;
- external APIs.

Prefer explicit comparison functions for the small supported schema.

Do not use:

- a generic recursive JSON diff;
- reflection-heavy comparison;
- embeddings;
- LLM comparison prompts;
- configurable rule engines;
- policy-schema registries;
- generalized document-diff libraries.

The comparator must produce stable output ordering.

Equivalent typed rule inputs must produce equivalent semantic output.

---

## Application-service requirements

The synchronous application service must:

1. load the two authoritative policy records;
2. verify that the policies are distinct;
3. verify organization compatibility;
4. verify policy-family and rule-schema compatibility;
5. resolve the authoritative accepted extraction attempt for each policy;
6. verify that each ruleset is fully validated and ready for comparison;
7. reconstruct immutable domain comparison inputs;
8. invoke the pure deterministic comparator;
9. calculate a canonical semantic fingerprint;
10. persist the complete comparison aggregate in one transaction;
11. return the existing comparison for an equivalent repeated request;
12. reload and serialize the persisted aggregate using existing repository conventions.

Any failure before commit must leave no partial comparison aggregate.

---

## API capability

Expose the narrowest useful API for comparison creation and retrieval.

A likely resource shape is:

```http
POST /api/v1/policy-comparisons
GET /api/v1/policy-comparisons/{comparison_id}
```

The create request should contain only:

- baseline policy identifier;
- proposed policy identifier.

The client must not provide:

- extraction-attempt identifiers;
- validated rules;
- materiality;
- reason codes;
- source provenance;
- comparison fingerprints;
- difference ordering.

Those values must be resolved or produced deterministically from authoritative persisted state.

API behavior must follow existing ChangeOps conventions for:

- creation responses;
- `Location` headers;
- idempotent resource creation;
- stable structured errors;
- deterministic serialization;
- missing-resource behavior.

Stable failures must distinguish at least:

- the same policy supplied as both versions;
- baseline policy not ready;
- proposed policy not ready;
- organization mismatch;
- family mismatch;
- schema mismatch;
- unsupported comparison schema;
- inconsistent policy or extraction lineage.

Exact error-code names should follow current repository naming conventions.

---

## Seeded demonstration revision

Add one proposed revision of the existing international-travel policy.

The proposed revision must:

- belong to the same fictional organization;
- use the same supported policy family;
- produce accepted schema-version-1 rules;
- contain a small and understandable number of semantic changes;
- produce at least two different comparison change categories where naturally supported;
- remain realistic for the existing scenario.

Potential supported differences include:

- effective date;
- covered employment type;
- training requirement;
- manager-approval requirement;
- booking restriction;
- exemption behavior.

The implementation must inspect the actual current rule schema before selecting revision differences.

Do not add another policy family.

Do not create an unrealistically large revision merely to increase comparison counts.

---

## Product-facing experience

Add the smallest coherent reviewer experience for policy comparison.

A reviewer must be able to see:

- the current policy;
- the proposed revision;
- comparison status;
- number of semantic differences;
- stable ordered rule differences;
- baseline values;
- proposed values;
- baseline provenance;
- proposed provenance;
- materiality;
- reason codes or readable explanations.

Reuse the current application design language and product terminology.

The UI should make clear that:

- AI may have proposed each policy’s typed extraction;
- deterministic validation accepted those rules;
- deterministic code calculated the comparison;
- no enterprise impact delta has been calculated yet.

Do not introduce:

- policy search;
- arbitrary policy uploads;
- generic comparison dashboards;
- comparison history management;
- collaboration;
- comments;
- approval controls;
- assessment impact delta;
- AI-generated difference explanation.

---

## Demo reset

The guarded local demo reset must remain safe and repeatable.

The reset should:

- preserve the fictional source catalog;
- preserve both seeded policy versions;
- remove generated comparison artifacts;
- continue removing generated analysis, approval, command, simulated enterprise, and execution history as currently documented;
- remain restricted to the recognized local demonstration database;
- remain safe to repeat.

Do not broaden the reset into a generic environment-management feature.

---

## Tests

### Domain tests

Add pure deterministic tests covering:

- identical typed rules;
- every supported semantic field change;
- added values;
- removed values;
- modified values;
- deterministic materiality;
- stable reason codes;
- stable ordering;
- correct baseline provenance;
- correct proposed provenance;
- identical semantics with different wording or source spans;
- canonical fingerprint input stability.

### PostgreSQL integration tests

Cover:

- successful atomic persistence;
- repeated equivalent creation;
- same-policy rejection;
- cross-organization rejection;
- family mismatch;
- schema mismatch;
- missing accepted baseline extraction;
- missing accepted proposed extraction;
- unresolved clarification;
- extraction-policy ownership;
- immutable historical comparison behavior;
- update or delete protections;
- uniqueness and fingerprint behavior;
- demo-reset removal of generated comparisons.

PostgreSQL remains required.

Do not substitute SQLite.

### API tests

Cover:

- valid creation;
- idempotent repeated creation;
- retrieval;
- stable difference ordering;
- structured error codes;
- missing comparison;
- inability to inject authoritative comparison values;
- complete provenance serialization.

### Frontend tests

Cover:

- current and proposed policy presentation;
- comparison summary;
- ordered semantic differences;
- baseline and proposed values;
- provenance;
- materiality;
- empty comparison state;
- loading state;
- stable error state;
- explicit explanation that impact delta is not yet available.

### Existing checks

All existing checks must remain green:

- backend unit and PostgreSQL integration tests;
- Ruff lint;
- Ruff format check;
- migration upgrade/downgrade/upgrade round trip;
- extraction evaluation;
- workflow evaluation;
- interpretation evaluation;
- approval-workflow evaluation;
- frontend typecheck;
- frontend lint;
- frontend tests;
- frontend production build;
- guarded demo reset.

No new LLM evaluation is required for the deterministic comparator.

---

## Documentation requirements

Update:

- `README.md`
- `docs/architecture.md`
- `docs/roadmap.md`
- `docs/decisions.md`
- `docs/demo-scenario.md`
- this milestone document if implementation details require an approved scope correction.

Add a new ADR covering:

- comparison of accepted typed semantics rather than raw text;
- deterministic materiality;
- immutable comparison persistence;
- why AI is excluded from semantic comparison;
- why LangGraph is excluded;
- why enterprise impact delta is deferred.

Do not rewrite prior ADR history.

---

## Explicit non-goals

This milestone does not include:

- enterprise impact delta;
- newly affected workers;
- no-longer-affected workers;
- changed enterprise impacts;
- changed proposed actions;
- AI-generated comparison interpretation;
- human-requested change-plan revision;
- action-review changes;
- approval-workflow changes;
- execution-command changes;
- Jira execution;
- a second simulated enterprise adapter;
- MCP;
- AWS;
- Terraform;
- production authentication;
- background workers;
- queues;
- schedulers;
- event sourcing;
- a generic policy-comparison platform;
- a generic JSON-diff framework;
- additional policy families.

---

## Risks to manage

### Risk: treating textual differences as semantic changes

Mitigation:

Compare only accepted typed rules.

### Risk: building an abstraction for future policy families

Mitigation:

Implement an explicit comparator for the current international-travel schema.

### Risk: coupling comparison to impact assessment

Mitigation:

Persist policy semantic comparison independently. Impact delta is a later aggregate or projection.

### Risk: allowing stale or rejected extraction attempts into comparison

Mitigation:

Resolve authoritative accepted attempts in application code and enforce durable lineage constraints.

### Risk: duplicating policy source data unnecessarily

Mitigation:

Persist immutable comparison values and provenance required for historical accuracy without copying unrelated policy or workflow aggregates.

### Risk: expanding the journey UI into a generic workflow interface

Mitigation:

Create one focused comparison experience with a bounded read model.

---

## Exit criteria

This milestone is complete when:

1. two supported policy versions can be compared;
2. only accepted validated rules enter comparison;
3. semantic differences are calculated deterministically;
4. wording changes with identical accepted semantics do not become operational changes;
5. every difference preserves lineage to both applicable policy versions;
6. materiality is deterministic and bounded to the supported schema;
7. comparison artifacts are immutable;
8. equivalent repeated requests do not create duplicate semantic comparisons;
9. the reviewer can understand the comparison through the UI;
10. the demo includes one clear current-policy/proposed-revision comparison;
11. demo reset removes generated comparison history but preserves both source policies;
12. all existing and new quality checks pass;
13. documentation accurately describes the implemented architecture;
14. no enterprise impact delta, AI comparison, MCP, AWS, or unrelated future work is introduced.

---

## Next milestone

The next planned vertical slice is:

**Enterprise impact delta from two immutable policy assessments.**

That future slice may answer:

- which workers became affected;
- which workers are no longer affected;
- which workers remain affected;
- which enterprise objects became affected;
- which enterprise impacts were cleared;
- why each impact changed;
- which operational actions are newly required or no longer required.

Do not implement that work as part of this milestone.