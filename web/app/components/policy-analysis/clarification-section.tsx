import type { AnalysisClarification, PolicyAnalysisJourney } from "@/lib/types";
import { formatDateTime, humanize } from "./formatters";
import { clarificationLabel } from "./journey-state";

export function ClarificationSection({
  journey,
  actor,
  busy,
  onActorChange,
  onAnswer,
}: {
  journey: PolicyAnalysisJourney;
  actor: string;
  busy: boolean;
  onActorChange: (value: string) => void;
  onAnswer: (clarification: AnalysisClarification) => void;
}) {
  const { extraction_findings: findings, clarifications } = journey.uncertainty;
  const label = clarificationLabel(journey);
  return (
    <section className="journey-card" aria-labelledby="clarification-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Authoritative uncertainty</p>
          <h2 id="clarification-heading">What needs human clarification?</h2>
        </div>
        <span className={`badge ${clarifications.length ? "human_input" : "not_required"}`}>
          {label}
        </span>
      </div>
      <p className="compatibility-note">
        This view uses extraction findings and persisted clarification records. Legacy seeded
        assessment questions are intentionally omitted because they were not discovered by AI.
      </p>
      {findings.length === 0 && clarifications.length === 0 ? (
        <p>No material clarification was required.</p>
      ) : (
        <>
          {findings.map((finding, index) => (
            <article className="finding-card" key={`${finding.code ?? "finding"}-${index}`}>
              <strong>{finding.code ? humanize(finding.code) : "Extraction finding"}</strong>
              <p>{finding.message}</p>
              {finding.provenance && <blockquote>{finding.provenance.quote}</blockquote>}
            </article>
          ))}
          {clarifications.map((clarification) => (
            <article className="clarification-card" key={clarification.id}>
              <div className="section-heading">
                <strong>{clarification.question_text}</strong>
                <span className={`badge status-${clarification.status}`}>
                  {humanize(clarification.status)}
                </span>
              </div>
              <p className="section-intro">
                This response is persisted with the reviewer identity before the same analysis run
                resumes.
              </p>
              {clarification.status === "pending" ? (
                <div className="clarification-action">
                  <label>
                    Responder identity
                    <input
                      type="email"
                      value={actor}
                      onChange={(event) => onActorChange(event.target.value)}
                    />
                  </label>
                  <button
                    type="button"
                    onClick={() => onAnswer(clarification)}
                    disabled={busy || !actor.trim()}
                  >
                    {busy ? "Submitting…" : "Confirm and resume analysis"}
                  </button>
                </div>
              ) : (
                <p>
                  Human response: <code>{JSON.stringify(clarification.answer)}</code> ·{" "}
                  {clarification.responder_identity} ·{" "}
                  {clarification.answered_at && formatDateTime(clarification.answered_at)}
                </p>
              )}
              <details className="technical-disclosure">
                <summary>View clarification contract</summary>
                <p>
                  Affected field: <code>{clarification.affected_fields.join(", ")}</code>
                </p>
                <p>
                  Allowed response:{" "}
                  <code>
                    {JSON.stringify(
                      clarification.expected_answer_contract.allowed_values ?? [],
                    )}
                  </code>
                </p>
              </details>
            </article>
          ))}
        </>
      )}
    </section>
  );
}
