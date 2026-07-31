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