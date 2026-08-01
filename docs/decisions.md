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

AI interpretation is stored separately from the immutable impact assessment. Every referenced impact and evidence key must resolve against the persisted assessment before the interpretation artifact is accepted.

The model may reference existing evidence but may not create authoritative evidence.

### Human clarification

AI may identify that clarification is needed, but deterministic code decides whether the workflow pauses.

Human clarification is treated as an explicit workflow input, not as an informal conversation. It must be persisted with provenance and used when validating the resulting policy rules.

Because clarification can change the validated rules and therefore the resulting assessment, material clarification must be included in the traceability and fingerprinting model defined by Milestone 2.

### Workflow orchestration

LangGraph will be used as a durable workflow state machine, not as an autonomous agent framework.

It is introduced because a policy-analysis run must be able to:

- pause for human clarification;
- persist its state;
- resume later in a different process;
- continue without losing accepted prior work;
- expose inspectable transitions across deterministic and probabilistic steps.

Workflow routing is implemented in code. Model output may be an input to a routing decision, but the model is never the router.

If pause-and-resume behavior were removed, sequential Python orchestration over persisted state would be sufficient and LangGraph would not be justified.

A workflow run and an impact assessment have separate lifecycles. A run may be paused, unsupported, failed, abandoned, or completed without an assessment. A completed run may reference the assessment it produced.

### Evaluation

Evaluation responsibilities are separated by architectural layer:

- **Grounding and referential integrity** are deterministic assertions and must fail tests when references do not resolve.
- **Policy extraction** is evaluated against a golden dataset of policy text, expected typed rules, provenance, and negative cases that must fail closed.
- **Interpretation quality** is evaluated with a rubric covering grounding, coverage, and usefulness. Initially, these results may be tracked without blocking merges.

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

Rejected for Milestone 2 because the required clarification interrupt must persist and resume across requests and processes. This alternative would be reconsidered if durable interruption were removed from scope.

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