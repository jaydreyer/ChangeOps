"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { parseApiError } from "@/lib/api";
import type {
  Evidence,
  ExecutionPreparation,
  Review,
  Workbench,
  WorkbenchItem,
} from "@/lib/types";

const labels: Record<string, string> = {
  ai_proposal: "AI proposal",
  human_decision: "Human decision",
  human_input: "Human input",
  workflow_state: "Workflow state",
  awaiting_decisions: "Awaiting decisions",
  revision_requested: "Revision requested",
  not_executed: "Not executed",
  policy_quote: "Policy source",
  deterministic_finding: "Deterministic conclusion",
  enterprise_impact: "Deterministic conclusion",
  relationship_path: "Deterministic relationship path",
  pending_execution: "Pending execution",
  unsupported_action_type: "Unsupported action type",
  unsupported_target_type: "Unsupported target type",
  executed: "Executed",
  execution_failed: "Execution failed",
  succeeded: "Succeeded",
  already_applied: "Already applied",
  execution_attempted: "Execution attempted",
};

function humanize(value: string) {
  return labels[value] ?? value.replaceAll("_", " ").replace(/^\w/, (letter) => letter.toUpperCase());
}

function ProvenanceLabel({ kind }: { kind: string }) {
  return <span className={`badge provenance ${kind}`}>{humanize(kind)}</span>;
}

export function WorkbenchView({
  initialWorkbench,
  initialPreparation = null,
}: {
  initialWorkbench: Workbench;
  initialPreparation?: ExecutionPreparation | null;
}) {
  const router = useRouter();
  const [actor, setActor] = useState("reviewer@example.com");
  const [message, setMessage] = useState("");
  const [resuming, setResuming] = useState(false);
  const { run, assessment, items } = initialWorkbench;
  const currentReviewId =
    items.find((item) => item.review.status === "pending")?.review.id ?? items[0]?.review.id;

  async function resume() {
    setResuming(true);
    setMessage("");
    try {
      const response = await fetch(`/api/v1/action-approval-runs/${run.id}/resume`, {
        method: "POST",
        headers: {
          "X-ChangeOps-Actor": actor,
          "X-ChangeOps-Role": "reviewer",
        },
      });
      if (!response.ok) {
        const error = await parseApiError(response);
        setMessage(error.message);
        return;
      }
      setMessage("Approval reconciliation completed; authoritative workflow state reloaded.");
      router.refresh();
    } catch {
      setMessage("The ChangeOps API is unavailable. Check that the local stack is running.");
    } finally {
      setResuming(false);
    }
  }

  return (
    <main className="workbench">
      <header className="workbench-header">
        <div>
          <Link href={`/policy-analyses/${run.policy_analysis_run_id}`} className="back-link">
            ← Return to policy analysis
          </Link>
          <p className="product-mark">ChangeOps</p>
          <p className="eyebrow">Human review and approval</p>
          <h1>Review proposed actions</h1>
          <p className="lede">
            You are reviewing {run.summary.total} proposed{" "}
            {run.summary.total === 1 ? "action" : "actions"}. Approval records a decision; it does
            not execute the action.
          </p>
        </div>
        <div className="approval-status-panel">
          <ProvenanceLabel kind="human_decision" />
          <strong>Authoritative approval state</strong>
          <span>{humanize(run.status)}</span>
          <span className="quiet-label">Current step: {humanize(run.current_step)}</span>
          <details className="technical-disclosure">
            <summary>View approval identity</summary>
            <dl className="identifiers">
              <div>
                <dt>Assessment</dt>
                <dd>{assessment.id}</dd>
              </div>
              <div>
                <dt>Approval run</dt>
                <dd>{run.id}</dd>
              </div>
            </dl>
          </details>
        </div>
      </header>

      <aside className="approval-boundary-notice" aria-label="Approval authority notice">
        <ProvenanceLabel kind="human_decision" />
        <div>
          <strong>A person decides whether each proposal may advance.</strong>
          <span>
            Deterministic findings and persisted evidence provide context; they do not make the
            decision.
          </span>
        </div>
      </aside>

      {run.status === "completed" && (
        <p className="completion-notice">
          Review is complete. Approval alone did not execute any action.
        </p>
      )}

      <section className="summary-panel" aria-labelledby="summary-heading">
        <div className="workflow-state">
          <ProvenanceLabel kind="workflow_state" />
          <h2 id="summary-heading">{humanize(run.status)}</h2>
          <p>Current step: {humanize(run.current_step)}</p>
        </div>
        <dl className="counts">
          {Object.entries(run.summary).map(([name, count]) => (
            <div key={name}>
              <dt>{humanize(name)}</dt>
              <dd>{count}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="reviewer-panel" aria-labelledby="identity-heading">
        <div>
          <h2 id="identity-heading">Demonstration reviewer</h2>
          <p>
            This identity populates trusted local demonstration headers. It is not authentication.
          </p>
        </div>
        <label>
          Reviewer email
          <input
            type="email"
            value={actor}
            onChange={(event) => setActor(event.target.value)}
            required
          />
        </label>
      </section>

      {run.failure_code && (
        <section className="failure-panel" aria-labelledby="failure-heading">
          <h2 id="failure-heading">Approval reconciliation failed</h2>
          <p>
            <code>{run.failure_code}</code> — {run.failure_message}
          </p>
          <button type="button" onClick={resume} disabled={resuming || !actor.trim()}>
            {resuming ? "Retrying…" : "Retry approval reconciliation"}
          </button>
        </section>
      )}
      {message && (
        <p
          className={
            /^(Approval reconciliation|Decision recorded|Another committed|Execution|Preparation)/.test(
              message,
            )
              ? "status-message"
              : "error"
          }
          role="status"
        >
          {message}
        </p>
      )}

      <section aria-labelledby="reviews-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Human decision boundary</p>
            <h2 id="reviews-heading">Review each proposed action</h2>
            <p className="section-intro">
              Items remain in their persisted membership order. The next pending review is open.
            </p>
          </div>
          <span>{items.length} actions</span>
        </div>
        <div className="review-list">
          {items.map((item) => (
            <ReviewCard
              key={item.review.id}
              item={item}
              actor={actor}
              onStatus={setMessage}
              isCurrent={item.review.id === currentReviewId}
            />
          ))}
        </div>
      </section>

      {run.status === "completed" && initialPreparation && (
        <ExecutionPreparationPanel
          runId={run.id}
          actor={actor}
          preparation={initialPreparation}
          onStatus={setMessage}
        />
      )}

      <details className="technical-disclosure workbench-technical">
        <summary>View technical workflow details</summary>
        <dl className="identifiers">
          <div>
            <dt>Lifecycle value</dt>
            <dd>{run.status}</dd>
          </div>
          <div>
            <dt>Current-step value</dt>
            <dd>{run.current_step}</dd>
          </div>
          <div>
            <dt>Policy-analysis run</dt>
            <dd>{run.policy_analysis_run_id}</dd>
          </div>
          <div>
            <dt>Policy change</dt>
            <dd>{assessment.policy_change_id}</dd>
          </div>
        </dl>
        <h3>Approval transitions</h3>
        <ol>
          {run.transitions.map((transition) => (
            <li key={transition.id}>
              {humanize(transition.trigger_type)}: {transition.from_status ?? "created"} →{" "}
              {transition.to_status} ({transition.reason_code})
            </li>
          ))}
        </ol>
      </details>
    </main>
  );
}

function ExecutionPreparationPanel({
  runId,
  actor,
  preparation,
  onStatus,
}: {
  runId: string;
  actor: string;
  preparation: ExecutionPreparation;
  onStatus: (message: string) => void;
}) {
  const router = useRouter();
  const [preparing, setPreparing] = useState(false);
  const [executingCommandId, setExecutingCommandId] = useState<string | null>(null);

  async function prepare() {
    setPreparing(true);
    onStatus("");
    try {
      const response = await fetch(
        `/api/v1/action-approval-runs/${runId}/execution-commands`,
        {
          method: "POST",
          headers: {
            "X-ChangeOps-Actor": actor,
            "X-ChangeOps-Role": "admin",
          },
        },
      );
      if (!response.ok) {
        const error = await parseApiError(response);
        if (response.status === 409) {
          onStatus(
            "Preparation state changed concurrently. Reloaded authoritative command state.",
          );
          router.refresh();
          return;
        }
        onStatus(error.message);
        return;
      }
      onStatus("Execution commands prepared. Reloaded authoritative command state.");
      router.refresh();
    } catch {
      onStatus(
        "Preparation response was ambiguous. Reloaded authoritative command state for reconciliation.",
      );
      router.refresh();
    } finally {
      setPreparing(false);
    }
  }

  async function execute(commandId: string) {
    setExecutingCommandId(commandId);
    onStatus("");
    try {
      const response = await fetch(`/api/v1/execution-commands/${commandId}/execute`, {
        method: "POST",
        headers: {
          "X-ChangeOps-Actor": actor,
          "X-ChangeOps-Role": "admin",
        },
      });
      if (!response.ok) {
        const error = await parseApiError(response);
        onStatus(error.message);
        router.refresh();
        return;
      }
      const result = (await response.json()) as { status: string };
      onStatus(
        result.status === "already_applied"
          ? "Execution was already applied. The original assignment was reused; no duplicate was created."
          : "Execution succeeded. The simulated learning assignment and audit result were committed together.",
      );
      router.refresh();
    } catch {
      onStatus(
        "Execution response was ambiguous. Reloaded authoritative assignment and audit state for reconciliation.",
      );
      router.refresh();
    } finally {
      setExecutingCommandId(null);
    }
  }

  return (
    <section className="preparation-panel" aria-labelledby="preparation-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Separate controlled operation</p>
          <h2 id="preparation-heading">Carry out approved actions</h2>
          <p className="section-intro">
            Approval is complete. Preparation creates immutable commands; execution still requires
            an explicit request.
          </p>
        </div>
        <ProvenanceLabel
          kind={preparation.execution_performed ? "execution_attempted" : "not_executed"}
        />
      </div>
      <dl className="execution-stage-summary" aria-label="Execution progress">
        <div>
          <dt>Authorization</dt>
          <dd>Completed</dd>
          <small>Human decisions are recorded.</small>
        </div>
        <div>
          <dt>Commands</dt>
          <dd>
            {preparation.prepared_command_count > 0
              ? `${preparation.prepared_command_count} prepared`
              : "Not prepared"}
          </dd>
          <small>Prepared contracts remain immutable.</small>
        </div>
        <div>
          <dt>Execution request</dt>
          <dd>{preparation.execution_performed ? "Recorded" : "Not requested"}</dd>
          <small>Execution never occurs during page load.</small>
        </div>
      </dl>
      <dl className="preparation-counts">
        <div>
          <dt>Approved</dt>
          <dd>{preparation.approved_action_count}</dd>
        </div>
        <div>
          <dt>Preparable</dt>
          <dd>{preparation.eligible_action_count}</dd>
        </div>
        <div>
          <dt>Manual follow-up</dt>
          <dd>{preparation.unsupported_approved_action_count}</dd>
        </div>
        <div>
          <dt>Prepared</dt>
          <dd>{preparation.prepared_command_count}</dd>
        </div>
      </dl>
      <button type="button" onClick={prepare} disabled={preparing || !actor.trim()}>
        {preparing ? "Preparing…" : "Prepare execution commands"}
      </button>

      {preparation.commands.length > 0 && (
        <div className="command-list">
          <div className="execution-group-heading">
            <div>
              <p className="eyebrow">Commands prepared</p>
              <h3>Authorized operations awaiting an explicit request</h3>
            </div>
            <span>{preparation.prepared_command_count} commands</span>
          </div>
          {preparation.commands.map((command) => (
            <article className="command-card" key={command.id}>
              <div className="command-heading">
                <div>
                  <strong>{command.effective_action.description}</strong>
                  <span>
                    {humanize(command.target_type)} · {command.target_identifier}
                  </span>
                  <span>
                    {humanize(command.system)} · {humanize(command.operation)}
                  </span>
                </div>
                <span className="badge execution">{humanize(command.execution_state)}</span>
              </div>
              {command.system === "learning" ? (
                <p>
                  Training:{" "}
                  <code>{String(command.parameters.course_identifier ?? "invalid command")}</code>
                </p>
              ) : (
                <>
                  <p>{String(command.parameters.summary ?? "Invalid Jira command")}</p>
                  <small>
                    Comparison <code>{String(command.parameters.comparison_id ?? "missing")}</code>
                  </small>
                </>
              )}
              <button
                type="button"
                onClick={() => execute(command.id)}
                disabled={executingCommandId !== null || !actor.trim()}
              >
                {executingCommandId === command.id
                  ? "Executing…"
                  : command.execution_state === "executed"
                    ? "Execute again safely"
                    : command.system === "jira"
                      ? "Create Jira task"
                      : "Execute training assignment"}
              </button>
              <details className="technical-disclosure command-technical">
                <summary>View command contract and lineage</summary>
                <dl className="identifiers">
                  <div>
                    <dt>Adapter operation</dt>
                    <dd>
                      <code>
                        {command.system}.{command.operation}
                      </code>
                    </dd>
                  </div>
                  <div>
                    <dt>Command status</dt>
                    <dd>{humanize(command.status)}</dd>
                  </div>
                  <div>
                    <dt>Due date</dt>
                    <dd>{command.effective_action.due_date ?? "None"}</dd>
                  </div>
                  <div>
                    <dt>Idempotency key</dt>
                    <dd>
                      <code>{command.idempotency_key}</code>
                    </dd>
                  </div>
                  <div>
                    <dt>Approval decision</dt>
                    <dd>
                      <code>{command.action_review_decision_id}</code>
                    </dd>
                  </div>
                  <div>
                    <dt>Proposed action</dt>
                    <dd>
                      <code>{command.proposed_action_id}</code>
                    </dd>
                  </div>
                  <div>
                    <dt>Prepared by</dt>
                    <dd>
                      {command.prepared_by} · {humanize(command.prepared_role)}
                    </dd>
                  </div>
                </dl>
                <h4>Immutable parameters</h4>
                <pre>{JSON.stringify(command.parameters, null, 2)}</pre>
              </details>
              {command.execution_results.length > 0 && (
                <div className="execution-history">
                  <div className="execution-group-heading">
                    <div>
                      <p className="eyebrow">Execution requested</p>
                      <h4>Immutable execution results</h4>
                    </div>
                  </div>
                  {command.execution_results.map((result) => (
                    <div key={result.id}>
                      <strong>{humanize(result.status)}</strong>
                      <p>{result.message}</p>
                      {result.learning_assignment && (
                        <p>
                          Assignment <code>{result.learning_assignment.id}</code>:{" "}
                          {result.learning_assignment.worker_id} →{" "}
                          {result.learning_assignment.training_course_id} (
                          {humanize(result.learning_assignment.assignment_status)})
                        </p>
                      )}
                      {result.jira_issue && (
                        <p>
                          Jira task{" "}
                          <a href={result.jira_issue.browse_url} target="_blank" rel="noreferrer">
                            {result.jira_issue.issue_key}
                          </a>{" "}
                          in {result.jira_issue.project_id_or_key}
                        </p>
                      )}
                      <details className="technical-disclosure inline-technical">
                        <summary>View result audit details</summary>
                        <dl className="identifiers">
                          <div>
                            <dt>Outcome code</dt>
                            <dd>
                              <code>{result.outcome_code}</code>
                            </dd>
                          </div>
                          <div>
                            <dt>Result ID</dt>
                            <dd>
                              <code>{result.id}</code>
                            </dd>
                          </div>
                          <div>
                            <dt>Attempted by</dt>
                            <dd>
                              {result.attempted_by} · {humanize(result.attempted_role)}
                            </dd>
                          </div>
                          <div>
                            <dt>Recorded</dt>
                            <dd>{result.created_at}</dd>
                          </div>
                        </dl>
                      </details>
                    </div>
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>
      )}

      {preparation.unsupported_items.length > 0 && (
        <div className="unsupported-list">
          <div className="execution-group-heading">
            <div>
              <p className="eyebrow">Manual completion required</p>
              <h3>Approved actions requiring manual follow-up</h3>
              <p>
                Automated execution is not available for these action types. Their approved
                records remain visible for follow-up outside ChangeOps.
              </p>
            </div>
            <span>
              {preparation.unsupported_approved_action_count}{" "}
              {preparation.unsupported_approved_action_count === 1 ? "action" : "actions"}
            </span>
          </div>
          {preparation.unsupported_items.map((item) => (
            <article key={item.action_review_id}>
              <strong>{humanize(item.action_type)}</strong>
              <p>
                {humanize(item.target_type)}: {item.target_identifier}
              </p>
              <small>Manual follow-up required. No automated execution is available.</small>
              <details className="technical-disclosure inline-technical">
                <summary>View execution limitation details</summary>
                <dl className="identifiers">
                  <div>
                    <dt>Authoritative classification</dt>
                    <dd>{humanize(item.reason_code)}</dd>
                  </div>
                  <div>
                    <dt>Persisted reason</dt>
                    <dd>{item.reason}</dd>
                  </div>
                  <div>
                    <dt>Action review</dt>
                    <dd>
                      <code>{item.action_review_id}</code>
                    </dd>
                  </div>
                  <div>
                    <dt>Proposed action</dt>
                    <dd>
                      <code>{item.proposed_action_id}</code>
                    </dd>
                  </div>
                </dl>
              </details>
            </article>
          ))}
        </div>
      )}
      <p className="execution-inline">
        <strong>Execution is always explicit.</strong> Only supported prepared Learning and Jira
        commands expose a control; approved actions without an automated mapping remain visible and
        inactive.
      </p>
    </section>
  );
}

function ReviewCard({
  item,
  actor,
  onStatus,
  isCurrent,
}: {
  item: WorkbenchItem;
  actor: string;
  onStatus: (message: string) => void;
  isCurrent: boolean;
}) {
  const { review } = item;
  const action = review.original_action;
  return (
    <details className="review-card" open={isCurrent}>
      <summary>
        <span className="sequence">{item.sequence + 1}</span>
        <span className="review-title">
          <strong>{humanize(action.action_type)}</strong>
          <span>
            {humanize(action.target_type)} · {action.target_identifier}
          </span>
          <span className="description">{action.description}</span>
        </span>
        <span className="review-state">
          <span className={`badge status ${review.status}`}>{humanize(review.status)}</span>
          <span className="badge execution">Execution: not_executed</span>
          <span>{action.due_date ? `Due ${action.due_date}` : "No due date"}</span>
        </span>
      </summary>
      <div className="review-body">
        <section className="review-proposal">
          <div className="subheading">
            <h3>What is being proposed?</h3>
            <ProvenanceLabel kind="ai_proposal" />
          </div>
          <p className="review-proposal-copy">{action.description}</p>
          <dl className="action-grid">
            <div>
              <dt>Target</dt>
              <dd>
                {humanize(action.target_type)} · {action.target_identifier}
              </dd>
            </div>
            <div>
              <dt>Due date</dt>
              <dd>{action.due_date ?? "None"}</dd>
            </div>
            <div>
              <dt>Decision state</dt>
              <dd>{humanize(review.status)}</dd>
            </div>
            <div>
              <dt>Execution state</dt>
              <dd>{humanize(action.execution_status)}</dd>
            </div>
          </dl>
        </section>

        {(item.finding || item.enterprise_impact) && (
          <section>
            <div className="subheading">
              <h3>Why is it being proposed?</h3>
              <ProvenanceLabel kind="deterministic_finding" />
            </div>
            {item.finding && (
              <div className="context-box">
                <strong>{humanize(item.finding.finding_type)}</strong>
                <p>{item.finding.explanation}</p>
                <details className="technical-disclosure inline-technical">
                  <summary>View deterministic finding details</summary>
                  <dl className="identifiers">
                    <div>
                      <dt>Worker</dt>
                      <dd>{item.finding.worker_id}</dd>
                    </div>
                    <div>
                      <dt>Severity</dt>
                      <dd>{humanize(item.finding.severity)}</dd>
                    </div>
                    <div>
                      <dt>Reason code</dt>
                      <dd>
                        <code>{item.finding.rule_code}</code>
                      </dd>
                    </div>
                  </dl>
                </details>
              </div>
            )}
            {item.enterprise_impact && (
              <div className="context-box">
                <strong>{item.enterprise_impact.display_name}</strong>
                <p>{item.enterprise_impact.explanation}</p>
                <details className="technical-disclosure inline-technical">
                  <summary>View deterministic impact details</summary>
                  <dl className="identifiers">
                    <div>
                      <dt>Domain</dt>
                      <dd>{humanize(item.enterprise_impact.domain)}</dd>
                    </div>
                    <div>
                      <dt>Classification</dt>
                      <dd>{humanize(item.enterprise_impact.classification)}</dd>
                    </div>
                    <div>
                      <dt>Reason code</dt>
                      <dd>
                        <code>{item.enterprise_impact.reason_code}</code>
                      </dd>
                    </div>
                  </dl>
                  <RelationshipPath item={item} />
                </details>
              </div>
            )}
          </section>
        )}

        <section>
          <div className="subheading">
            <h3>What evidence supports it?</h3>
            <span>{item.evidence.length} persisted references</span>
          </div>
          <details className="technical-disclosure evidence-disclosure">
            <summary>View persisted evidence</summary>
            <div className="evidence-list">
              {item.evidence.map((evidence) => (
                <EvidencePanel key={evidence.key} evidence={evidence} />
              ))}
            </div>
          </details>
        </section>

        {review.status === "pending" ? (
          <DecisionForm review={review} actor={actor} onStatus={onStatus} />
        ) : (
          <DecisionSummary review={review} />
        )}

        <details className="technical-disclosure inline-technical">
          <summary>View technical action details</summary>
          <dl className="identifiers">
            <div>
              <dt>Action type</dt>
              <dd>{humanize(action.action_type)}</dd>
            </div>
            <div>
              <dt>Worker</dt>
              <dd>{action.worker_id ?? "Not worker-specific"}</dd>
            </div>
            <div>
              <dt>Review ID</dt>
              <dd>{review.id}</dd>
            </div>
            <div>
              <dt>Proposed action ID</dt>
              <dd>{action.proposed_action_id}</dd>
            </div>
            <div>
              <dt>Reason code</dt>
              <dd>{review.review_context.reason_code ?? "None"}</dd>
            </div>
          </dl>
        </details>
      </div>
    </details>
  );
}

function RelationshipPath({ item }: { item: WorkbenchItem }) {
  const path = item.enterprise_impact?.relationship_path ?? [];
  if (!path.length) return null;
  return (
    <ol className="relationship-path" aria-label="Ordered relationship path">
      {path.map((element) => (
        <li key={element.sequence}>
          <span>{element.display_label}</span>
          {element.relationship_to_next && <small>{humanize(element.relationship_to_next)}</small>}
        </li>
      ))}
    </ol>
  );
}

function EvidencePanel({ evidence }: { evidence: Evidence }) {
  return (
    <article className="evidence">
      <div>
        <ProvenanceLabel kind={evidence.source_type} />
        <h4>{evidence.label}</h4>
      </div>
      <p>{evidence.detail}</p>
      {evidence.source_type === "policy_quote" && evidence.policy_quote && (
        <details>
          <summary>View persisted policy text</summary>
          <blockquote>{evidence.policy_quote}</blockquote>
        </details>
      )}
    </article>
  );
}

function DecisionForm({
  review,
  actor,
  onStatus,
}: {
  review: Review;
  actor: string;
  onStatus: (message: string) => void;
}) {
  const router = useRouter();
  const [decision, setDecision] = useState("approved");
  const [rationale, setRationale] = useState("");
  const [description, setDescription] = useState(review.original_action.description);
  const [dueDate, setDueDate] = useState(review.original_action.due_date ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!rationale.trim()) {
      setMessage("Rationale is required for every human decision.");
      return;
    }
    if (!actor.trim()) {
      setMessage("Enter a demonstration reviewer identity before submitting.");
      return;
    }
    setSubmitting(true);
    setMessage("");
    const edited =
      decision === "approved"
        ? {
            ...(description !== review.original_action.description ? { description } : {}),
            ...(dueDate !== (review.original_action.due_date ?? "") ? { due_date: dueDate } : {}),
          }
        : undefined;
    try {
      const response = await fetch(`/api/v1/action-reviews/${review.id}/decisions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-ChangeOps-Actor": actor,
          "X-ChangeOps-Role": "reviewer",
        },
        body: JSON.stringify({
          decision,
          rationale,
          ...(edited && Object.keys(edited).length ? { edited_action: edited } : {}),
        }),
      });
      if (!response.ok) {
        const error = await parseApiError(response);
        if (response.status === 409 && error.code === "action_review_already_decided") {
          const conflictMessage =
            "Another committed decision already completed this review. Reloaded authoritative state.";
          onStatus(conflictMessage);
          router.refresh();
          return;
        }
        setMessage(error.message);
        return;
      }
      const successMessage = "Decision recorded. Reloaded authoritative approval progress.";
      onStatus(successMessage);
      router.refresh();
    } catch {
      setMessage("The ChangeOps API is unavailable. Check that the local stack is running.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="decision-form" onSubmit={submit}>
      <div className="subheading">
        <h3>Record your decision</h3>
        <ProvenanceLabel kind="human_decision" />
      </div>
      <fieldset>
        <legend>Decision</legend>
        <div className="decision-options">
          {["approved", "rejected", "deferred", "revision_requested"].map((value) => (
            <label key={value}>
              <input
                type="radio"
                name={`decision-${review.id}`}
                value={value}
                checked={decision === value}
                onChange={(event) => setDecision(event.target.value)}
              />
              {humanize(value)}
            </label>
          ))}
        </div>
      </fieldset>
      <label>
        Rationale <span aria-hidden="true">*</span>
        <textarea
          value={rationale}
          onChange={(event) => setRationale(event.target.value)}
          required
          rows={3}
        />
      </label>
      {decision === "approved" && (
        <fieldset className="edit-fields">
          <legend>Optional permitted approval edits</legend>
          <p>Only description and due date may change. All other action fields remain immutable.</p>
          <label>
            Approved description
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows={3}
            />
          </label>
          <label>
            Approved due date
            <input
              type="date"
              value={dueDate}
              onChange={(event) => setDueDate(event.target.value)}
            />
          </label>
        </fieldset>
      )}
      <button type="submit" disabled={submitting}>
        {submitting ? "Recording…" : "Record terminal decision"}
      </button>
      {message && (
        <p className={message.startsWith("Decision recorded") ? "status-message" : "error"} role="status">
          {message}
        </p>
      )}
    </form>
  );
}

function DecisionSummary({ review }: { review: Review }) {
  const decision = review.current_decision;
  if (!decision) return null;
  const original = review.original_action;
  const effective = review.effective_approved_action;
  return (
    <section className="decision-summary">
      <div className="subheading">
        <h3>Recorded decision</h3>
        <ProvenanceLabel kind="human_decision" />
      </div>
      <p>
        <strong>{humanize(decision.decision)}</strong> by {decision.reviewer_identity}
      </p>
      <blockquote>{decision.rationale}</blockquote>
      {effective && (
        <div>
          <h4>Effective approved action</h4>
          <dl className="comparison">
            <div>
              <dt>Original description</dt>
              <dd>{original.description}</dd>
            </div>
            <div>
              <dt>Approved description</dt>
              <dd>{effective.description}</dd>
            </div>
            <div>
              <dt>Original due date</dt>
              <dd>{original.due_date ?? "None"}</dd>
            </div>
            <div>
              <dt>Approved due date</dt>
              <dd>{effective.due_date ?? "None"}</dd>
            </div>
          </dl>
          <p className="execution-inline">
            Execution state: <strong>{effective.execution_status}</strong>
          </p>
        </div>
      )}
    </section>
  );
}
