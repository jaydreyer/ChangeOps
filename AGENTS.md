# ChangeOps engineering policy

## Product purpose

ChangeOps analyzes policy and operational changes, identifies affected people,
systems, documentation, and commitments, proposes evidence-backed actions,
routes consequential actions through human approval, executes approved actions
against simulated enterprise systems, and records a complete audit trail.

## Non-negotiable rules

- Preserve auditability for every consequential operation.
- Never bypass human approval boundaries.
- Never weaken authentication, authorization, or permissions to make tests pass.
- Preserve immutable audit records.
- Keep external enterprise integrations fictional and deterministic.
- Do not introduce real Workday, Salesforce, Jira, or customer credentials.
- Every meaningful workflow state transition must be testable.
- Consequential actions must include evidence and provenance.
- Do not silently infer approval.
- Failed actions must not be represented as successful.

## Engineering workflow

- Start meaningful work from the latest default branch in an isolated worktree.
- Keep each pull request focused on one reviewable outcome.
- Read relevant documents under `docs/` before changing architecture.
- Update architecture documentation when implemented behavior changes.
- Run backend, frontend, integration, and browser checks applicable to the change.
- Map acceptance criteria to test or verification evidence.
- Use a fresh reviewer or subagent that did not implement the change.
- Open pull requests as drafts unless explicitly told otherwise.
- Do not merge without human approval.

## Completion standard

Work is complete only when:

1. acceptance criteria are addressed;
2. applicable tests pass;
3. relevant failure paths are tested;
4. implementation has received an independent review;
5. documentation is updated when needed;
6. the pull request contains a concise summary and verification evidence.
