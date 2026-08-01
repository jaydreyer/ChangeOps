# Milestone 2 — Enterprise AI Policy Intelligence

## Status

Milestone 2 backend complete; preparing Milestone 3.

The API workflow, deterministic validation and analysis, durable clarification, grounded
interpretation, offline evaluations, automated merge gates, and manual live-provider smoke path
are complete. The integrated reviewer UI is a deferred product-experience criterion because the
roadmap intentionally introduces Next.js later. Milestone 3 approval work has not started.

Milestone 1 is complete and merged into `main`.

This milestone follows ADR-0009: AI owns **language in** and **interpretation out**, while deterministic code remains authoritative for validation, enterprise facts, relationships, impact discovery, workflow routing, approval, and execution.

---

## Objective

Introduce AI into ChangeOps without weakening the deterministic guarantees established in Milestone 1.

By the end of this milestone, a reviewer can submit an unstructured international-travel policy, resolve any material ambiguity, and receive:

- validated structured policy rules;
- an immutable deterministic impact assessment;
- an evidence-grounded AI interpretation identifying coverage gaps;
- a durable workflow that can pause and resume around human clarification;
- a traceable record of policy text, AI proposals, deterministic conclusions, and human input.

The milestone should demonstrate:

- LangChain structured output;
- LangGraph durable workflow orchestration;
- typed extraction from policy text;
- deterministic validation of probabilistic output;
- human-in-the-loop clarification;
- evidence-grounded interpretation;
- automated AI evaluation.

The goal is not to demonstrate that an LLM can read a policy. The goal is to demonstrate how AI can participate safely in an enterprise workflow.

---

## Flagship user journey

1. A reviewer submits an unstructured international-travel policy.

2. The AI extractor proposes:
   - typed policy rules;
   - source provenance for material fields;
   - unresolved questions;
   - an unsupported-policy outcome when the policy cannot be represented safely.

3. Deterministic validation checks:
   - schema validity;
   - supported policy constructs;
   - business rules;
   - source provenance;
   - enterprise identifier resolution.

4. When an unresolved question could change the resulting impact set, the workflow pauses.

5. A reviewer submits an explicit clarification.

6. The same workflow resumes and re-validates the rules.

7. The existing Milestone 1 engine runs against the validated rules and creates the immutable impact assessment.

8. A separate AI interpretation step reads the persisted assessment and identifies grounded coverage gaps.

9. The reviewer sees:
   - the accepted policy understanding;
   - the human clarification;
   - the deterministic assessment;
   - the separate AI interpretation;
   - the evidence supporting each result.

---

## Architecture

```text
policy text
    ↓
AI policy understanding
    ↓
candidate typed rules, provenance, and clarification questions
    ↓
deterministic validation and clarification gate
    ↓
validated InternationalTravelPolicyRules
    ↓
deterministic enterprise impact analysis
    ↓
immutable impact assessment
    ↓
AI coverage-gap interpretation
    ↓
separate change plan
    ↓
human review
```

The deterministic assessment remains the authoritative record of enterprise impact.

AI may propose rules, ambiguity, and interpretation. It may not determine whether an enterprise object is affected or modify the resulting assessment.

---

## Architectural principles

### AI assists; deterministic code decides

No enterprise-impact conclusion is accepted on model authority alone.

### AI output is proposed until validated

LLM output must pass deterministic schema, business-rule, provenance, and referential validation before it can influence the workflow.

### AI references existing evidence

AI may cite policy text, impacts, evidence keys, relationship paths, proposed actions, and explicit human clarification.

AI may not create authoritative enterprise facts, relationships, impacts, reason codes, or evidence.

### Every AI step is evaluated

Extraction and interpretation must have explicit tests or evaluations that can fail.

### The model is a node, never the router

Workflow transitions, retries, clarification gates, and completion rules are implemented in code.

LangGraph is used for durable orchestration, not autonomous agent behavior.

---

## Scope

### In scope

#### Structured policy extraction

Convert `policy_changes.policy_text` into candidate `InternationalTravelPolicyRules`.

The extraction result includes:

- candidate rules;
- field-level source provenance;
- material clarification questions;
- unsupported-policy findings;
- model, prompt, and schema version metadata.

#### Deterministic validation

Validate AI output before it reaches the impact engine.

Validation includes:

- schema validation;
- supported-policy validation;
- business-rule validation;
- provenance validation;
- enterprise identifier resolution;
- clarification materiality.

The system must fail closed when a policy cannot be represented safely.

#### Human clarification

Pause the workflow when different reasonable interpretations could change:

- policy applicability;
- worker or country scope;
- effective-date behavior;
- approval requirements;
- training requirements;
- exception behavior;
- enterprise identifier resolution;
- the resulting impact set.

Clarification is persisted as explicit human input and used when validating the final rules.

#### Durable workflow

Use LangGraph to support:

- persisted workflow state;
- pause;
- resume;
- bounded retry;
- unsupported outcomes;
- terminal failure;
- successful completion;
- inspection of workflow progress.

A workflow run may exist without an assessment and may end without producing one.

#### Deterministic impact analysis

Invoke the existing Milestone 1 engine using validated rules.

The deterministic analyzers remain authoritative and unchanged in responsibility.

#### Coverage-gap interpretation

After the assessment is persisted, produce a separate change plan identifying grounded limitations in what the deterministic assessment can see.

Examples include:

- policy requirements with no corresponding dependency mapping;
- domains that depend on incomplete mappings;
- material policy concepts with no matching impact or action;
- missing enterprise context that limits completeness.

Coverage gaps are review concerns, not additional impacts.

#### Evaluation

Add automated evaluation for:

- extraction correctness;
- unsupported and fail-closed cases;
- provenance and reference integrity;
- interpretation grounding;
- interpretation usefulness.

---

### Out of scope

Milestone 2 does not include:

- arbitrary policy families;
- autonomous agents;
- multi-agent workflows;
- model-controlled routing;
- direct AI access to enterprise source tables;
- AI-created relationships or impacts;
- action prioritization or sequencing;
- stakeholder communication drafting;
- approval workflows;
- enterprise-system execution;
- MCP integrations;
- retrieval-augmented generation;
- vector databases;
- changes to the Milestone 1 impact model solely to expand the AI demo.

These capabilities should be added only when a later milestone contains a product problem that requires them.

---

## AI roles

### Extractor

The extractor sees:

- policy text;
- the supported policy schema;
- prompt and schema versions.

It does not see:

- workers;
- travel records;
- training completion;
- teams;
- dependency tables;
- customer commitments;
- existing impact conclusions.

Its responsibility is to understand language, not determine enterprise impact.

### Interpreter

The interpreter sees:

- the original policy text;
- the accepted extraction result;
- relevant human clarification;
- the persisted assessment aggregate.

It does not query source tables directly.

Its responsibility is to identify grounded coverage gaps without adding, removing, or reclassifying impacts.

---

## Key artifacts

### Workflow run

Represents the lifecycle of the policy-analysis process independently from an assessment.

A run may be:

- running;
- awaiting clarification;
- unsupported;
- failed;
- completed;
- cancelled.

It references an assessment only after one is created.

### Policy extraction result

Stores:

- candidate rules;
- accepted rules when validation succeeds;
- provenance;
- clarification questions;
- unsupported findings;
- model, prompt, and schema versions.

Extraction attempts are append-only.

### Human clarification

Stores:

- the question;
- the reviewer response;
- the affected field or conclusion;
- actor and timestamp;
- provenance;
- any superseding clarification.

Material clarification must be traceable into the accepted rules and assessment inputs.

### Change plan

Stores the AI interpretation linked to a completed assessment.

It contains structured coverage-gap findings and grounding references.

It never mutates the assessment.

---

## Why LangGraph

LangGraph is introduced because the workflow must pause for human clarification and resume later in a different request or process without losing state.

If pause and resume were removed, sequential Python orchestration over persisted state would be sufficient.

LangGraph is therefore used as a durable state machine with typed transitions and checkpoints.

It is not used to create an autonomous agent loop.

The graph should contain only meaningful orchestration boundaries. Deterministic helper functions do not each need to become graph nodes.

---

## LangChain usage

LangChain is used narrowly for:

- model abstraction;
- prompt templates;
- structured-output binding;
- typed response parsing.

LangChain is not used for:

- agents;
- tool-selection loops;
- workflow routing;
- memory;
- retrieval;
- database access.

Every AI invocation must record:

- model provider;
- model identifier;
- prompt version;
- schema version.

---

## Clarification gate

The AI may propose clarification questions.

Deterministic code decides whether a question is material enough to pause the workflow.

A question is material when different reasonable answers could change the validated rules or resulting impact set.

Questions must be:

- tied to a specific field or conclusion;
- supported by policy text or an identifiable absence;
- answerable by a reviewer;
- relevant to the supported policy schema.

Generic ambiguity lists do not satisfy this requirement.

---

## Coverage-gap interpretation

Coverage-gap interpretation is the only required interpretation capability in Milestone 2.

Each finding must include:

- a concise title;
- the observed limitation;
- why it matters;
- a recommended review action;
- cited policy spans;
- cited impacts or evidence keys where applicable.

Before persistence:

- the model cites exact policy quotes and existing impact IDs or evidence keys;
- deterministic code constructs span offsets, lifecycle IDs, and evidence ownership;
- every cited impact must exist;
- every evidence key must resolve;
- every policy span must resolve;
- the finding must not add or modify an impact.

Invalid references fail the interpretation step.

Interpretation failure does not invalidate the deterministic assessment.

---

## Evaluation

### Grounding

Grounding is a hard deterministic assertion.

Tests must fail when:

- a policy span does not resolve;
- an evidence key does not exist;
- an impact reference does not exist;
- an interpretation attempts to alter assessment content;
- a clarification references the wrong workflow run.

### Extraction

Create a versioned golden dataset containing:

- policy text;
- expected support status;
- expected typed rules;
- expected provenance;
- expected clarification behavior;
- unsupported cases.

The seeded policy and hand-verified rules form the first golden case.

The dataset should include:

- equivalent wording;
- material ambiguity;
- non-material ambiguity;
- unsupported policy family;
- unrepresentable international-travel policy;
- unresolvable enterprise reference;
- conflicting dates or exceptions.

Required-field extraction regressions should block merge.

### Interpretation

Use fixed assessment fixtures with annotated expected coverage concerns.

Evaluate:

- grounding;
- relevance;
- specificity;
- usefulness;
- boundary compliance;
- absence of invented impacts.

Grounding and boundary compliance are hard gates.

Usefulness may initially be measured without blocking merge.

---

## Acceptance criteria

### Policy understanding

- [x] Unstructured international-travel policy text produces typed candidate rules.
- [x] Material fields include resolvable source provenance.
- [x] Unsupported or unrepresentable policies fail closed.
- [x] The extractor does not invent enterprise identifiers.
- [x] Model, prompt, and schema versions are persisted.
- [x] Invalid AI output never reaches the deterministic engine.

### Clarification and workflow

- [x] Material ambiguity pauses the workflow before assessment creation.
- [x] Non-material observations do not block processing.
- [x] A reviewer can submit explicit clarification.
- [x] Clarification is persisted with actor and provenance.
- [x] The same workflow run resumes after clarification.
- [x] Invalid or stale clarification is rejected.
- [x] Workflow state is persisted and inspectable.
- [x] Workflow routing is deterministic and encoded in code.
- [x] Retries are bounded.

### Deterministic analysis

- [x] The Milestone 1 engine receives only validated rules.
- [x] The same validated rules and enterprise data produce the same assessment as Milestone 1.
- [x] AI cannot add, remove, or reclassify impacts.
- [x] Assessments remain immutable.

### Interpretation

- [x] Interpretation runs only after assessment persistence.
- [x] Interpretation reads the assessment aggregate rather than raw source tables.
- [x] Every cited impact, evidence key, and policy span resolves.
- [x] Invalid references prevent change-plan persistence.
- [x] Change plans are stored separately from assessments.
- [x] Interpretation failure does not invalidate the assessment.
- [x] Coverage gaps are presented as review concerns, not authoritative impacts.

### Evaluation

- [x] Versioned extraction, workflow, and interpretation golden datasets exist.
- [x] Unsupported and fail-closed cases are covered.
- [x] Grounding and boundary checks run as deterministic tests.
- [x] Interpretation fixtures and a documented rubric exist.
- [x] The repository documents commands for all three offline AI evaluations.
- [x] Evaluation output records model, prompt, schema, and dataset versions.

### Product experience

These criteria describe the integrated reviewer UI and are intentionally deferred until the
portfolio milestone introduces Next.js. The Milestone 2 API exposes each artifact and state
transition needed by that future experience without introducing frontend technology early.

- [ ] A reviewer can complete the flagship workflow through the integrated reviewer UI (deferred).
- [ ] AI proposals, deterministic conclusions, and human input are visibly distinguished in the
  UI (deferred).
- [ ] Provenance is inspectable in the UI (deferred).
- [ ] Pause and resume are visible in the UI (deferred).
- [ ] Unsupported and failed outcomes are understandable in the UI (deferred).
- [ ] The change plan is clearly separate from the deterministic assessment in the UI (deferred).

---

## Exit criteria

The Milestone 2 backend exit criteria are complete:

1. A reviewer can submit an unstructured international-travel policy.

2. AI produces typed candidate rules with provenance.

3. Unsupported or unrepresentable text fails closed.

4. Material ambiguity pauses a persisted workflow.

5. A reviewer can provide explicit clarification.

6. The same workflow resumes and validates the clarified rules.

7. The unchanged Milestone 1 engine creates the expected immutable assessment.

8. A separate AI change plan identifies grounded coverage gaps.

9. Every AI reference resolves against existing policy or assessment artifacts.

10. Extraction and grounding evaluations run automatically.

11. The product clearly communicates the architectural boundary:

   - AI understands language;
   - deterministic code determines enterprise impact;
   - AI explains what the deterministic analysis may not cover;
   - humans resolve ambiguity before consequential analysis proceeds.

The API and repository documentation communicate this boundary today. The full visual product
experience for these artifacts remains deferred as described above.

---

## Explicit deferrals

The following are intentionally deferred:

- residual-risk interpretation;
- broad cross-domain synthesis;
- action prioritization;
- action sequencing;
- communication drafting;
- approval routing;
- enterprise-system execution;
- MCP integrations;
- arbitrary policy-family support;
- RAG and vector search;
- multi-agent workflows.
- integrated Next.js reviewer UI.
