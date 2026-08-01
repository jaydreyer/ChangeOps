"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { parseApiError } from "@/lib/api";
import type { Evidence, Review, Workbench, WorkbenchItem } from "@/lib/types";

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
};

function humanize(value: string) {
  return labels[value] ?? value.replaceAll("_", " ").replace(/^\w/, (letter) => letter.toUpperCase());
}

function ProvenanceLabel({ kind }: { kind: string }) {
  return <span className={`badge provenance ${kind}`}>{humanize(kind)}</span>;
}

export function WorkbenchView({ initialWorkbench }: { initialWorkbench: Workbench }) {
  const router = useRouter();
  const [actor, setActor] = useState("reviewer@example.com");
  const [message, setMessage] = useState("");
  const [resuming, setResuming] = useState(false);
  const { run, assessment, items } = initialWorkbench;

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
          <p className="eyebrow">ChangeOps · focused reviewer interface</p>
          <h1>Human Approval Workbench</h1>
          <p className="lede">
            Review persisted proposals against deterministic findings, enterprise impacts, and
            evidence.
          </p>
        </div>
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
      </header>

      <aside className="execution-notice" aria-label="Execution status notice">
        <ProvenanceLabel kind="not_executed" />
        <strong>Approval records a human decision. It does not execute the action.</strong>
      </aside>

      {run.status === "completed" && (
        <p className="completion-notice">
          Review is complete. Approved actions remain unexecuted.
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
            /^(Approval reconciliation|Decision recorded|Another committed)/.test(message)
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
            <p className="eyebrow">Immutable membership order</p>
            <h2 id="reviews-heading">Proposed actions</h2>
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
            />
          ))}
        </div>
      </section>

      <details className="technical">
        <summary>Technical workflow details</summary>
        <dl>
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

function ReviewCard({
  item,
  actor,
  onStatus,
}: {
  item: WorkbenchItem;
  actor: string;
  onStatus: (message: string) => void;
}) {
  const { review } = item;
  const action = review.original_action;
  return (
    <details className="review-card" open={item.sequence === 0}>
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
        <section>
          <div className="subheading">
            <h3>Original action snapshot</h3>
            <ProvenanceLabel kind="ai_proposal" />
          </div>
          <dl className="action-grid">
            <div>
              <dt>Action type</dt>
              <dd>{humanize(action.action_type)}</dd>
            </div>
            <div>
              <dt>Target</dt>
              <dd>
                {action.target_type}: {action.target_identifier}
              </dd>
            </div>
            <div>
              <dt>Worker</dt>
              <dd>{action.worker_id ?? "Not worker-specific"}</dd>
            </div>
            <div>
              <dt>Due date</dt>
              <dd>{action.due_date ?? "None"}</dd>
            </div>
            <div className="wide">
              <dt>Description</dt>
              <dd>{action.description}</dd>
            </div>
            <div>
              <dt>Execution state</dt>
              <dd>not_executed</dd>
            </div>
          </dl>
        </section>

        {(item.finding || item.enterprise_impact) && (
          <section>
            <div className="subheading">
              <h3>Deterministic context</h3>
              <ProvenanceLabel kind="deterministic_finding" />
            </div>
            {item.finding && (
              <div className="context-box">
                <strong>
                  {humanize(item.finding.finding_type)} · {item.finding.worker_id}
                </strong>
                <p>{item.finding.explanation}</p>
                <small>
                  Severity: {item.finding.severity} · Reason code: {item.finding.rule_code}
                </small>
              </div>
            )}
            {item.enterprise_impact && (
              <div className="context-box">
                <strong>{item.enterprise_impact.display_name}</strong>
                <p>{item.enterprise_impact.explanation}</p>
                <small>
                  {humanize(item.enterprise_impact.domain)} ·{" "}
                  {humanize(item.enterprise_impact.classification)} · Reason code:{" "}
                  {item.enterprise_impact.reason_code}
                </small>
                <RelationshipPath item={item} />
              </div>
            )}
          </section>
        )}

        <section>
          <div className="subheading">
            <h3>Resolved evidence</h3>
            <span>{item.evidence.length} persisted references</span>
          </div>
          <div className="evidence-list">
            {item.evidence.map((evidence) => (
              <EvidencePanel key={evidence.key} evidence={evidence} />
            ))}
          </div>
        </section>

        {review.status === "pending" ? (
          <DecisionForm review={review} actor={actor} onStatus={onStatus} />
        ) : (
          <DecisionSummary review={review} />
        )}

        <details className="technical">
          <summary>Technical action details</summary>
          <dl>
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
        <h3>Record human decision</h3>
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
        <h3>Persisted human decision</h3>
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
