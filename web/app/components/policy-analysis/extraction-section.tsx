import type { AnalysisExtraction } from "@/lib/types";
import { flattenObject, formatValue, humanize } from "./formatters";

export function ExtractionSection({ extraction }: { extraction: AnalysisExtraction | null }) {
  if (!extraction) {
    return (
      <section className="journey-card unavailable-section">
        <p className="eyebrow">AI extraction</p>
        <h2>What rules did ChangeOps identify?</h2>
        <p>The workflow has not persisted an extraction attempt yet.</p>
      </section>
    );
  }
  const displayedRules = extraction.accepted_rules ?? extraction.candidate_rules ?? {};
  return (
    <section className="journey-card" aria-labelledby="extraction-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Structured policy understanding</p>
          <h2 id="extraction-heading">What rules did ChangeOps identify?</h2>
        </div>
        <span className={`badge validation-${extraction.validation_outcome}`}>
          {humanize(extraction.validation_outcome)}
        </span>
      </div>
      <div className="boundary-row">
        <span className="badge ai_proposal">AI suggested rules</span>
        <span aria-hidden="true">→</span>
        <span className="badge deterministic">System validated</span>
      </div>
      <p className="section-intro">
        AI proposed structured values from the policy text. Only deterministically validated values
        are allowed into the impact assessment.
      </p>
      <dl className="rule-grid">
        {flattenObject(displayedRules).map(([path, value]) => (
          <div key={path}>
            <dt>{humanize(path.replaceAll(".", " · "))}</dt>
            <dd>{formatValue(value)}</dd>
          </div>
        ))}
      </dl>
      {extraction.accepted_rules && (
        <p className="accepted-note">
          Accepted rules are the validated values allowed to cross into deterministic impact
          analysis.
        </p>
      )}
      <details className="technical-disclosure">
        <summary>View exact policy provenance ({extraction.provenance.length} records)</summary>
        <div className="provenance-list">
          {extraction.provenance.map((item) => (
            <article key={`${item.field_path}-${item.start}-${item.end}`}>
              <code>{item.field_path}</code>
              <blockquote>“{item.quote}”</blockquote>
              <small>
                Source characters {item.start}–{item.end}
              </small>
            </article>
          ))}
        </div>
      </details>
      {extraction.validation_errors.length > 0 && (
        <details className="technical-disclosure inline-technical">
          <summary>View deterministic validation records</summary>
          <ul className="technical-record-list">
            {extraction.validation_errors.map((error) => (
              <li key={`${error.code}-${error.field_path}`}>
                <strong>{error.message}</strong>
                <span>
                  <code>{error.code}</code>
                  {error.field_path && (
                    <>
                      {" · "}
                      <code>{error.field_path}</code>
                    </>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
