import type { AnalysisExtraction } from "@/lib/types";
import { flattenObject, formatValue, humanize } from "./formatters";

export function ExtractionSection({ extraction }: { extraction: AnalysisExtraction | null }) {
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
      {extraction.accepted_rules && (
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
