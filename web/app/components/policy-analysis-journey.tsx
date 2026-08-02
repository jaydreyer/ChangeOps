"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { parseApiError } from "@/lib/api";
import type {
  AnalysisAssessment,
  AnalysisClarification,
  AnalysisExtraction,
  PolicyAnalysisJourney,
} from "@/lib/types";

const stepNames = [
  "Policy",
  "Analysis",
  "Clarification",
  "Assessment",
  "Interpretation",
  "Approval",
  "Execution",
];

export function PolicyAnalysisJourneyView({
  initialJourney,
}: {
  initialJourney: PolicyAnalysisJourney;
}) {
  const router = useRouter();
  const [actor, setActor] = useState("reviewer@example.com");
  const [busy, setBusy] = useState<"clarification" | "interpretation" | "approval" | null>(null);
  const [message, setMessage] = useState("");
  const { policy, run, extraction, assessment, interpretation, approval_run: approvalRun } =
    initialJourney;

  async function answerClarification(clarification: AnalysisClarification) {
    setBusy("clarification");
    setMessage("");
    try {
      const response = await fetch(
        `/api/v1/policy-analysis-runs/${run.id}/clarifications/${clarification.id}/answer`,
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ value: true, responder_identity: actor }),
        },
      );
      if (!response.ok) {
        const error = await parseApiError(response);
        setMessage(error.message);
        return;
      }
      setMessage("Clarification recorded. The same durable analysis run resumed.");
      router.refresh();
    } catch {
      setMessage("The ChangeOps API is unavailable. Check that the local stack is running.");
    } finally {
      setBusy(null);
    }
  }

  async function createInterpretation() {
    if (!assessment) return;
    setBusy("interpretation");
    setMessage("");
    try {
      const response = await fetch(`/api/v1/impact-assessments/${assessment.id}/change-plans`, {
        method: "POST",
      });
      if (!response.ok) {
        const error = await parseApiError(response);
        setMessage(error.message);
        return;
      }
      setMessage("Grounded interpretation persisted. Reloaded the authoritative change plan.");
      router.refresh();
    } catch {
      setMessage("The interpretation response was unavailable. Reload to reconcile persisted state.");
    } finally {
      setBusy(null);
    }
  }

  async function openApproval() {
    if (!assessment) return;
    setBusy("approval");
    setMessage("");
    try {
      const response = await fetch(`/api/v1/impact-assessments/${assessment.id}/approval-run`, {
        method: "POST",
      });
      if (!response.ok) {
        const error = await parseApiError(response);
        setMessage(error.message);
        return;
      }
      const approval = (await response.json()) as { id: string };
      router.push(`/approvals/${approval.id}`);
    } catch {
      setMessage("The ChangeOps API is unavailable. Check that the local stack is running.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="analysis-shell">
      <header className="analysis-hero">
        <div>
          <Link href="/" className="back-link">
            ← Policy analyses
          </Link>
          <p className="eyebrow">Policy analysis journey</p>
          <h1>{policy.title}</h1>
          <p className="lede">
            {policy.organization_name} · Effective {formatDate(policy.effective_date)}
          </p>
        </div>
        <dl className="identifiers">
          <div>
            <dt>Analysis run</dt>
            <dd>{run.id}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>
              <span className={`badge status-${run.status}`}>{humanize(run.status)}</span>
            </dd>
          </div>
        </dl>
      </header>

      <JourneyNav journey={initialJourney} />

      {run.failure_code && (
        <section className="failure-panel" aria-labelledby="analysis-failure-heading">
          <h2 id="analysis-failure-heading">Analysis did not complete</h2>
          <p>
            <code>{run.failure_code}</code> — The persisted workflow stopped safely at{" "}
            {humanize(run.current_step)}.
          </p>
        </section>
      )}
      {message && (
        <p className={message.includes("unavailable") ? "error" : "status-message"} role="status">
          {message}
        </p>
      )}

      <section className="journey-card policy-detail" aria-labelledby="policy-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Authoritative source</p>
            <h2 id="policy-heading">Policy</h2>
          </div>
          <span>Version {policy.version}</span>
        </div>
        <dl className="policy-meta">
          <div>
            <dt>Policy ID</dt>
            <dd>{policy.id}</dd>
          </div>
          <div>
            <dt>Owner</dt>
            <dd>{policy.owner}</dd>
          </div>
        </dl>
        <blockquote className="policy-text">{policy.policy_text}</blockquote>
      </section>

      <ExtractionSection extraction={extraction} />

      <section className="journey-card" aria-labelledby="clarification-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Authoritative uncertainty</p>
            <h2 id="clarification-heading">Clarification</h2>
          </div>
          <span className="badge human_input">Human input</span>
        </div>
        <p className="compatibility-note">
          This view uses extraction findings and persisted clarification records. Legacy seeded
          assessment questions are intentionally omitted because they were not discovered by AI.
        </p>
        {initialJourney.uncertainty.extraction_findings.length === 0 &&
        initialJourney.uncertainty.clarifications.length === 0 ? (
          <p>No material clarification was required.</p>
        ) : (
          <>
            {initialJourney.uncertainty.extraction_findings.map((finding, index) => (
              <article className="finding-card" key={`${finding.code ?? "finding"}-${index}`}>
                <strong>{finding.code ? humanize(finding.code) : "Extraction finding"}</strong>
                <p>{finding.message}</p>
                {finding.provenance && <blockquote>{finding.provenance.quote}</blockquote>}
              </article>
            ))}
            {initialJourney.uncertainty.clarifications.map((clarification) => (
              <article className="clarification-card" key={clarification.id}>
                <div className="section-heading">
                  <strong>{clarification.question_text}</strong>
                  <span className={`badge status-${clarification.status}`}>
                    {humanize(clarification.status)}
                  </span>
                </div>
                <p>
                  Affected field: <code>{clarification.affected_fields.join(", ")}</code>
                </p>
                <p>
                  Allowed response:{" "}
                  <code>
                    {JSON.stringify(clarification.expected_answer_contract.allowed_values ?? [])}
                  </code>
                </p>
                {clarification.status === "pending" ? (
                  <div className="clarification-action">
                    <label>
                      Responder identity
                      <input
                        type="email"
                        value={actor}
                        onChange={(event) => setActor(event.target.value)}
                      />
                    </label>
                    <button
                      type="button"
                      onClick={() => answerClarification(clarification)}
                      disabled={busy !== null || !actor.trim()}
                    >
                      {busy === "clarification" ? "Submitting…" : "Confirm true and resume"}
                    </button>
                  </div>
                ) : (
                  <p>
                    Human response: <code>{JSON.stringify(clarification.answer)}</code> ·{" "}
                    {clarification.responder_identity} ·{" "}
                    {clarification.answered_at && formatDateTime(clarification.answered_at)}
                  </p>
                )}
              </article>
            ))}
          </>
        )}
      </section>

      {assessment ? (
        <AssessmentSection assessment={assessment} journey={initialJourney} />
      ) : (
        <section className="journey-card unavailable-section">
          <p className="eyebrow">Deterministic analysis</p>
          <h2>Assessment unavailable</h2>
          <p>
            An immutable assessment is created only after extraction is accepted and any material
            clarification is resolved.
          </p>
        </section>
      )}

      <section className="journey-card" aria-labelledby="interpretation-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Grounded model synthesis</p>
            <h2 id="interpretation-heading">Interpretation and change plan</h2>
          </div>
          <span className="badge ai_proposal">AI recommendation</span>
        </div>
        {interpretation.status === "available" && interpretation.change_plan ? (
          <>
            <p>{interpretation.change_plan.change_plan.summary}</p>
            <div className="interpretation-list">
              {interpretation.change_plan.change_plan.coverage_gaps.map((gap) => (
                <article key={gap.finding_key}>
                  <div className="section-heading">
                    <h3>{gap.title}</h3>
                    <span className="badge deterministic">Grounding accepted</span>
                  </div>
                  <p>{gap.observed_limitation}</p>
                  <p>
                    <strong>Why it matters:</strong> {gap.why_it_matters}
                  </p>
                  <p>
                    <strong>Recommended review:</strong> {gap.recommended_review_action}
                  </p>
                  {gap.policy_spans.map((span) => (
                    <blockquote key={`${span.start}-${span.end}`}>
                      “{span.quote}” <small>Policy span {span.start}–{span.end}</small>
                    </blockquote>
                  ))}
                  <p className="reference-line">
                    Impact IDs:{" "}
                    {gap.impact_references.map((item) => item.impact_id).join(", ") || "None cited"}
                  </p>
                  <p className="reference-line">
                    Evidence keys:{" "}
                    {gap.evidence_references.map((item) => item.evidence_key).join(", ") ||
                      "None cited"}
                  </p>
                </article>
              ))}
            </div>
          </>
        ) : assessment ? (
          <>
            <p>
              {interpretation.status === "failed"
                ? `The last interpretation attempt failed safely (${interpretation.failure_code}). The deterministic assessment is unchanged.`
                : "No grounded interpretation has been persisted for this completed assessment."}
            </p>
            <button
              type="button"
              onClick={createInterpretation}
              disabled={busy !== null}
            >
              {busy === "interpretation" ? "Generating…" : "Generate grounded interpretation"}
            </button>
          </>
        ) : (
          <p>Interpretation becomes available after the deterministic assessment completes.</p>
        )}
      </section>

      <section className="journey-card approval-handoff" aria-labelledby="approval-heading">
        <div>
          <p className="eyebrow">Human governance</p>
          <h2 id="approval-heading">Continue to action approval</h2>
          <p>
            The existing workbench preserves lineage from this analysis run through the immutable
            assessment and proposed actions. Approval still does not execute an action.
          </p>
        </div>
        {approvalRun ? (
          <Link className="button-link" href={`/approvals/${approvalRun.id}`}>
            Open approval workbench
          </Link>
        ) : (
          <button
            type="button"
            onClick={openApproval}
            disabled={!assessment || run.status !== "completed" || busy !== null}
          >
            {busy === "approval" ? "Creating…" : "Create approval run"}
          </button>
        )}
      </section>
    </main>
  );
}

function JourneyNav({ journey }: { journey: PolicyAnalysisJourney }) {
  const states = journeyStates(journey);
  return (
    <nav className="journey-nav" aria-label="ChangeOps workflow">
      <ol>
        {stepNames.map((name, index) => (
          <li key={name} className={states[index]} aria-current={states[index] === "current" ? "step" : undefined}>
            <span>{index + 1}</span>
            <strong>{name}</strong>
            <small>{humanize(states[index])}</small>
          </li>
        ))}
      </ol>
    </nav>
  );
}

function ExtractionSection({ extraction }: { extraction: AnalysisExtraction | null }) {
  if (!extraction) {
    return (
      <section className="journey-card unavailable-section">
        <p className="eyebrow">AI extraction</p>
        <h2>Extraction not available</h2>
        <p>The workflow has not persisted an extraction attempt yet.</p>
      </section>
    );
  }
  const proposed = extraction.candidate_rules ?? {};
  const accepted = extraction.accepted_rules;
  return (
    <section className="journey-card" aria-labelledby="extraction-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Structured policy understanding</p>
          <h2 id="extraction-heading">Extraction and provenance</h2>
        </div>
        <span className={`badge validation-${extraction.validation_outcome}`}>
          {humanize(extraction.validation_outcome)}
        </span>
      </div>
      <div className="boundary-row">
        <span className="badge ai_proposal">AI-proposed values</span>
        <span aria-hidden="true">→</span>
        <span className="badge deterministic">Deterministic validation</span>
      </div>
      <dl className="rule-grid">
        {flattenObject(proposed).map(([path, value]) => (
          <div key={path}>
            <dt>{humanize(path.replaceAll(".", " · "))}</dt>
            <dd>{formatValue(value)}</dd>
          </div>
        ))}
      </dl>
      {accepted && (
        <p className="accepted-note">
          Accepted rules are the validated values allowed to cross into deterministic impact
          analysis.
        </p>
      )}
      <h3>Exact policy provenance</h3>
      <div className="provenance-list">
        {extraction.provenance.map((item) => (
          <article key={item.field_path}>
            <code>{item.field_path}</code>
            <blockquote>“{item.quote}”</blockquote>
            <small>
              Source characters {item.start}–{item.end}
            </small>
          </article>
        ))}
      </div>
      {extraction.validation_errors.length > 0 && (
        <>
          <h3>Deterministic validation findings</h3>
          <ul>
            {extraction.validation_errors.map((error) => (
              <li key={`${error.code}-${error.field_path}`}>
                <code>{error.code}</code> — {error.message}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function AssessmentSection({
  assessment,
  journey,
}: {
  assessment: AnalysisAssessment;
  journey: PolicyAnalysisJourney;
}) {
  const evidenceById = new Map(assessment.evidence.map((item) => [item.id, item]));
  const impacts = Object.values(assessment.enterprise_impacts).flat();
  return (
    <>
      <section className="journey-card" aria-labelledby="assessment-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Immutable deterministic result</p>
            <h2 id="assessment-heading">Assessment</h2>
          </div>
          <span className="badge deterministic">Deterministic conclusion</span>
        </div>
        <dl className="assessment-counts">
          <div>
            <dt>Affected workers</dt>
            <dd>{assessment.summary.affected_workers}</dd>
          </div>
          <div>
            <dt>Cleared workers</dt>
            <dd>{assessment.summary.unaffected_workers}</dd>
          </div>
          <div>
            <dt>Enterprise impacts</dt>
            <dd>{assessment.summary.enterprise_impacts}</dd>
          </div>
          <div>
            <dt>Proposed actions</dt>
            <dd>{assessment.proposed_actions.length}</dd>
          </div>
        </dl>
        <div className="worker-columns">
          {(["affected", "unaffected"] as const).map((classification) => (
            <section key={classification}>
              <h3>{classification === "affected" ? "Affected workers" : "Cleared workers"}</h3>
              {assessment.worker_results
                .filter((item) => item.classification === classification)
                .map((item) => (
                  <article className="worker-card" key={item.trip_id}>
                    <strong>{item.worker.name}</strong>
                    <p>{item.explanation}</p>
                    <small>{item.reason_codes.map(humanize).join(" · ")}</small>
                  </article>
                ))}
            </section>
          ))}
        </div>
      </section>

      <section className="journey-card" aria-labelledby="coverage-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Evaluated-object coverage</p>
            <h2 id="coverage-heading">Enterprise coverage</h2>
          </div>
          <span className="badge deterministic">Derived, not persisted</span>
        </div>
        <p>
          Impact records exist only for affected objects. Cleared objects were in the deterministic
          organization universe but produced no impact record.
        </p>
        <div className="coverage-grid">
          {journey.enterprise_coverage.map((domain) => (
            <article key={domain.domain}>
              <h3>{humanize(domain.domain)}</h3>
              <dl>
                <div>
                  <dt>Considered</dt>
                  <dd>{domain.considered}</dd>
                </div>
                <div>
                  <dt>Affected</dt>
                  <dd>{domain.affected}</dd>
                </div>
                <div>
                  <dt>Cleared</dt>
                  <dd>{domain.cleared}</dd>
                </div>
              </dl>
              <ul>
                {domain.objects.map((item) => (
                  <li key={item.id}>
                    <span>{item.display_name}</span>
                    <span className={`badge ${item.classification}`}>
                      {humanize(item.classification)}
                    </span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="journey-card" aria-labelledby="impacts-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Evidence-backed facts</p>
            <h2 id="impacts-heading">Findings and enterprise impacts</h2>
          </div>
          <span>{impacts.length} impacts</span>
        </div>
        <div className="impact-list">
          {impacts.map((impact) => (
            <details key={impact.id}>
              <summary>
                <span>
                  <strong>{impact.display_name}</strong>
                  <small>{humanize(impact.domain)}</small>
                </span>
                <span className="badge deterministic">{humanize(impact.classification)}</span>
              </summary>
              <p>{impact.explanation}</p>
              <p>
                Reason code: <code>{impact.reason_code}</code>
              </p>
              <ol className="relationship-path">
                {impact.relationship_path.map((element) => (
                  <li key={`${impact.id}-${element.sequence}`}>
                    <span>{element.display_label}</span>
                    {element.relationship_to_next && <small>{element.relationship_to_next}</small>}
                  </li>
                ))}
              </ol>
              <div className="evidence-list">
                {impact.evidence_ids.map((id) => {
                  const evidence = evidenceById.get(id);
                  return evidence ? (
                    <article className="evidence" key={id}>
                      <strong>{evidence.label}</strong>
                      <pre>{JSON.stringify(evidence.snapshot, null, 2)}</pre>
                    </article>
                  ) : null;
                })}
              </div>
            </details>
          ))}
        </div>
      </section>

      <section className="journey-card" aria-labelledby="actions-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Not yet human reviewed</p>
            <h2 id="actions-heading">Proposed actions</h2>
          </div>
          <span className="badge deterministic">Deterministic proposal</span>
        </div>
        <ul className="proposed-action-list">
          {assessment.proposed_actions.map((action) => (
            <li key={action.id}>
              <div>
                <strong>{humanize(action.type)}</strong>
                <p>{action.description}</p>
              </div>
              <span className="badge not_executed">Not executed</span>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}

function journeyStates(journey: PolicyAnalysisJourney) {
  const { run, assessment, interpretation, approval_run: approval } = journey;
  const blocked = run.status === "awaiting_clarification";
  const terminalFailure = run.status === "failed" || run.status === "unsupported";
  return [
    "completed",
    run.latest_extraction_attempt_id ? "completed" : "current",
    blocked ? "current" : run.clarifications.length > 0 ? "completed" : "completed",
    assessment ? "completed" : blocked || terminalFailure ? "blocked" : "current",
    interpretation.status === "available"
      ? "completed"
      : assessment
        ? "current"
        : "unavailable",
    approval ? "completed" : assessment ? "available" : "unavailable",
    approval?.status === "completed" ? "available" : "unavailable",
  ];
}

function flattenObject(value: Record<string, unknown>, prefix = ""): [string, unknown][] {
  return Object.entries(value).flatMap(([key, item]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    if (item && typeof item === "object" && !Array.isArray(item)) {
      return flattenObject(item as Record<string, unknown>, path);
    }
    return [[path, item]];
  });
}

function formatValue(value: unknown) {
  return Array.isArray(value) ? value.join(", ") : String(value);
}

function humanize(value: string) {
  return value.replaceAll("_", " ").replace(/^\w/, (letter) => letter.toUpperCase());
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeZone: "UTC" }).format(
    new Date(value),
  );
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
