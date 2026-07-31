# ChangeOps Delivery Roadmap

## Milestone 0 — Deterministic Impact Assessment

Proves:
- normalized enterprise data;
- deterministic impact analysis;
- evidence-backed findings;
- persisted assessment snapshots.

Technologies:
- FastAPI
- PostgreSQL
- Docker

Not included:
- LLMs
- LangChain
- LangGraph
- frontend
- AWS
- MCP
- approvals
- execution

Exit criteria:
- golden scenario passes;
- assessments persist across restarts;
- evidence and actions are correct;
- integration tests pass against PostgreSQL.

## Milestone 1 — Policy Ingestion and Structured Extraction

Proves:
- policy text can be submitted;
- an LLM can extract a typed policy representation;
- ambiguous or invalid extractions are surfaced;
- deterministic impact analysis can operate on extracted rules.

Technologies added:
- LangChain
- LLM provider
- structured output
- tracing and evaluation support

Architectural boundary:
- LLM extracts policy meaning;
- deterministic code applies policy rules.

Exit criteria:
- policy text produces validated structured rules;
- invalid extraction fails safely;
- golden policy produces the expected structured representation;
- deterministic analysis results remain unchanged.

## Milestone 2 — Resumable Workflow

Proves:
- the policy-analysis process has explicit workflow state;
- uncertain extraction can pause for human review;
- processing can resume after clarification;
- failures and retries are visible and auditable.

Technologies added:
- LangGraph
- persisted graph state
- human-in-the-loop interruption and resume

Expected graph:
1. ingest policy;
2. extract rules;
3. validate extraction;
4. identify ambiguities;
5. pause for clarification when required;
6. run deterministic impact analysis;
7. persist findings and recommendations.

Exit criteria:
- graph state persists;
- ambiguous policy pauses;
- approved clarification resumes the same workflow;
- no consequential action is executed automatically.

## Milestone 3 — Documentation Impact

Proves:
- policy changes can be compared with existing knowledge content;
- outdated or incomplete guidance can be identified;
- draft updates can be generated with supporting evidence.

Technologies added:
- LangChain document comparison and drafting;
- knowledge-article data model;
- retrieval only if justified by the dataset.

Exit criteria:
- the seeded travel article is identified as incomplete;
- each proposed change cites the policy and article evidence;
- generated drafts remain recommendations only.

## Milestone 4 — Approval and Simulated Execution

Proves:
- consequential actions require human approval;
- reviewers can approve, reject, or edit recommendations;
- approved actions execute against simulated enterprise systems;
- the complete workflow is auditable.

Technologies added:
- LangGraph approval interruption and resume;
- MCP;
- simulated Workday, learning, Jira, Salesforce, and knowledge-system tools;
- idempotent execution;
- audit events.

Exit criteria:
- no action executes without approval;
- repeated execution does not duplicate effects;
- every action records actor, evidence, decision, and result.

## Milestone 5 — Portfolio Application and AWS Deployment

Proves:
- the system works as a usable end-to-end application;
- infrastructure is reproducible;
- the public demonstration reflects enterprise constraints.

Technologies added:
- Next.js
- TypeScript
- AWS
- Terraform
- CI/CD
- authentication and authorization
- observability

Likely AWS architecture:
- ECS Fargate for the API and workflow service;
- RDS PostgreSQL;
- ECR;
- Application Load Balancer;
- Secrets Manager or Parameter Store;
- CloudWatch;
- S3 where document storage is required.

Deployment sequencing:
- first minimal AWS deployment after Milestone 1;
- portfolio-grade deployment after Milestone 4 or during Milestone 5.

## Technology introduction rule

A technology enters the project only when the milestone contains a problem that requires it.

Examples:

- LangChain enters when policy text must be converted into typed model input.
- LangGraph enters when the workflow has branching, persistence, interruption, and resume.
- MCP enters when approved actions must call enterprise-style tools.
- AWS enters after the application has a stable deployable slice.