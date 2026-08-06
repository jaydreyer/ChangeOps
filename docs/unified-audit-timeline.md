# Unified Audit Timeline

## Repository findings

The timeline is scoped by `policy_analysis_runs.id`. That identifier owns the analyzed policy
snapshot and deterministically reaches extraction attempts, clarifications, one immutable impact
assessment, interpretation attempts and its change plan, one approval run, item-level reviews and
decisions, execution commands, execution results, simulated learning assignments, and Jira issues.

No migration is required. The projection reads the existing authoritative artifacts at request
time and does not create a timeline table, materialized view, event store, trigger, queue, or
background worker.

| Journey concept | Authoritative model/table | Connecting identifier | Timestamp | Actor identity |
|---|---|---|---|---|
| Analysis request and policy snapshot | `PolicyAnalysisRun` / `policy_analysis_runs` | `id`, `policy_change_id` | `created_at` | Not persisted |
| Extraction attempt and validation outcome | `PolicyExtractionAttempt` / `policy_extraction_attempts` | `policy_analysis_run_id` | `created_at` | Model provider and identifier |
| Clarification request and answer | `PolicyAnalysisClarification` / `policy_analysis_clarifications` | `policy_analysis_run_id` | `created_at`, `answered_at` | `responder_identity` for answers |
| Deterministic assessment | `ImpactAssessment` / `impact_assessments` | `policy_analysis_run_id` | `created_at`, `completed_at` | Deterministic system |
| Interpretation attempt and outcome | `PolicyInterpretationAttempt` / `policy_interpretation_attempts` | `policy_analysis_run_id`, `impact_assessment_id` | `created_at`, `completed_at` | Model provider and identifier |
| Grounded change plan | `ChangePlan` / `change_plans` | `policy_analysis_run_id`, `impact_assessment_id` | `created_at` | AI-assisted output validated by deterministic code |
| Item review | `ActionReview` / `action_reviews` | `assessment_id` | `created_at`, `completed_at` | No actor on creation |
| Human decision | `ActionReviewDecision` / `action_review_decisions` | `action_review_id` | `created_at` | `reviewer_identity`, `reviewer_role` |
| Approval completion or failure | `ActionApprovalRun` / `action_approval_runs` | `policy_analysis_run_id`, `assessment_id` | `completed_at` or `updated_at` | Deterministic calculation |
| Prepared command | `ExecutionCommand` / `execution_commands` | `approval_run_id`, `assessment_id` | `created_at` | `prepared_by`, `prepared_role` |
| Execution request, result, replay prevention, or failure | `ExecutionResult` / `execution_results` | `execution_command_id` | `created_at` | `attempted_by`, `attempted_role` |
| Simulated learning side effect | `SimulatedLearningAssignment` / `simulated_learning_assignments` | `source_execution_command_id` | `created_at` | Simulated learning target |
| Jira side effect | `JiraIssue` / `jira_issues` | `execution_command_id` | `created_at` | Jira |

`PolicyChange` is the authoritative source-policy record, but it has no persisted creation timestamp
or submitter identity. The first slice therefore does not fabricate a “policy stored” event. The
analysis-run entry identifies the stored journey and policy ID using the run's durable snapshot.

`PolicyComparison` connects through its persisted baseline and proposed extraction-attempt IDs, and
`PolicyComparisonImpactDelta` connects through its persisted assessment IDs. Both therefore appear
in every selected run whose authoritative lineage participates in the comparison. Confluence
metadata is durable catalog state, but there is no persisted Confluence activity artifact scoped
to a policy-analysis run, so the timeline does not narrate a refresh.

## API and projection

`GET /api/v1/policy-analysis-runs/{run_id}/audit-timeline` returns:

- `subject_type` and `subject_id`;
- chronologically ordered entries;
- closed actor-category, outcome, and event-type values;
- backend-authored title and description;
- one authoritative artifact type and ID per entry;
- a real detail destination only when an existing UI route can represent the artifact; and
- optional secondary metadata.

The projection service uses explicit artifact-specific mappers. Equal timestamps are ordered by
centrally defined causal event precedence, then artifact type, artifact ID, and entry key. The same
persisted state therefore returns the same order.

## Event-to-artifact mapping

| Timeline event | Authoritative artifact | Actor category | Detail route |
|---|---|---|---|
| Analysis requested or failed | `PolicyAnalysisRun` | Deterministic system | `/policy-analyses/{run_id}` |
| Extraction attempted | `PolicyExtractionAttempt` | AI-assisted | Policy journey extraction section |
| Extraction accepted or rejected | `PolicyExtractionAttempt` | Deterministic system | Policy journey extraction section |
| Clarification requested | `PolicyAnalysisClarification` | Deterministic system | Policy journey clarification section |
| Clarification answered | `PolicyAnalysisClarification` | Human | Policy journey clarification section |
| Assessment created or completed | `ImpactAssessment` | Deterministic system | Policy journey assessment section |
| Interpretation attempted | `PolicyInterpretationAttempt` | AI-assisted | Policy journey interpretation section |
| Interpretation accepted or failed | `PolicyInterpretationAttempt` | Deterministic system | Policy journey interpretation section |
| Change plan created | `ChangePlan` | AI-assisted | Policy journey interpretation section |
| Policy comparison created | `PolicyComparison` | Deterministic system | `/policy-comparisons/{comparison_id}` |
| Enterprise impact delta created | `PolicyComparisonImpactDelta` | Deterministic system | `/policy-comparisons/{comparison_id}` |
| Action review created | `ActionReview` | Deterministic system | `/approvals/{approval_run_id}` |
| Human decision recorded | `ActionReviewDecision` | Human | `/approvals/{approval_run_id}` |
| Approval completed or failed | `ActionApprovalRun` | Deterministic system | `/approvals/{approval_run_id}` |
| Execution command prepared | `ExecutionCommand` | Deterministic system | Approval execution section |
| Execution requested | `ExecutionResult` | Human | Approval execution section |
| Execution completed, failed, or replay prevented | `ExecutionResult` | Deterministic system | Approval execution section |
| Simulated learning assignment created | `SimulatedLearningAssignment` | External system | Approval execution section |
| Jira issue created | `JiraIssue` | External system | Persisted Jira browse URL |

## Test plan

Unit tests cover every explicit mapper, actor and outcome classification, identities, metadata,
links, negative attempts, and equal-timestamp ordering. Integration tests cover stable retrieval,
not-found behavior, absence of a mutation route, the flagship approval/Jira/replay path, and
authoritative artifact identity. Demo-reset coverage proves that the same fictional flagship
lifecycle is reconstructed with extraction, comparison, approval, Jira creation, and replay
prevention. Frontend tests cover API order, labels, identities, conditional
links, accessible metadata disclosure, empty state, and failure state. The browser smoke follows
the seeded journey to the timeline and one artifact destination without live Jira or Confluence.
