import type { PolicyAnalysisJourney } from "@/lib/types";
import { humanize, shortIdentifier } from "./formatters";

export function InterpretationSection({
  journey,
  busy,
  onCreate,
}: {
  journey: PolicyAnalysisJourney;
  busy: boolean;
  onCreate: () => void;
}) {
  const { assessment, interpretation } = journey;
  const lineageByFinding = new Map(
    interpretation.resolved_references.map((item) => [item.finding_key, item]),
  );
  return (
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
            {interpretation.change_plan.change_plan.coverage_gaps.map((gap) => {
              const lineage = lineageByFinding.get(gap.finding_key);
              return (
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
                  <div className="lineage-group">
                    <h4>Persisted policy snapshot</h4>
                    {lineage?.policy_spans.map((span) => (
                      <blockquote key={`${span.start}-${span.end}`}>
                        “{span.quote}”{" "}
                        <small>
                          Characters {span.start}–{span.end} · Validated against the policy snapshot
                        </small>
                      </blockquote>
                    ))}
                  </div>
                  {lineage && lineage.impacts.length > 0 && (
                    <div className="lineage-group">
                      <h4>Enterprise impacts</h4>
                      {lineage.impacts.map((impact) => (
                        <article className="lineage-reference" key={impact.impact_id}>
                          <strong>{impact.display_name}</strong>
                          <span>
                            {humanize(impact.domain)} · {humanize(impact.classification)}
                          </span>
                          <small>
                            Reason: <code>{impact.reason_code}</code>
                          </small>
                          <small title={impact.impact_id}>
                            Impact ID: <code>{shortIdentifier(impact.impact_id)}</code>
                          </small>
                        </article>
                      ))}
                    </div>
                  )}
                  {lineage && lineage.evidence.length > 0 && (
                    <div className="lineage-group">
                      <h4>Evidence</h4>
                      {lineage.evidence.map((evidence) => (
                        <article className="lineage-reference" key={evidence.evidence_key}>
                          <strong>{evidence.label}</strong>
                          <span>
                            {humanize(evidence.evidence_type)} · {humanize(evidence.source_type)}
                          </span>
                          <small>
                            Source: <code>{evidence.source_id}</code>
                          </small>
                          <small>
                            Evidence key: <code>{evidence.evidence_key}</code>
                          </small>
                        </article>
                      ))}
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        </>
      ) : assessment ? (
        <>
          <p>
            {interpretation.status === "failed"
              ? `The last interpretation attempt failed safely (${interpretation.failure_code}). The deterministic assessment is unchanged.`
              : "No grounded interpretation has been persisted for this completed assessment."}
          </p>
          <button type="button" onClick={onCreate} disabled={busy}>
            {busy ? "Generating…" : "Generate grounded interpretation"}
          </button>
        </>
      ) : (
        <p>Interpretation becomes available after the deterministic assessment completes.</p>
      )}
    </section>
  );
}
