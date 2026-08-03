import type { AnalysisAssessment, EnterpriseCoverageDomain } from "@/lib/types";
import { humanize } from "./formatters";

export function AssessmentSections({
  assessment,
  coverage,
}: {
  assessment: AnalysisAssessment | null;
  coverage: EnterpriseCoverageDomain[];
}) {
  if (!assessment) {
    return (
      <section className="journey-card unavailable-section">
        <p className="eyebrow">Deterministic analysis</p>
        <h2>Assessment unavailable</h2>
        <p>
          An immutable assessment is created only after extraction is accepted and any material
          clarification is resolved.
        </p>
      </section>
    );
  }
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
          {coverage.map((domain) => (
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
