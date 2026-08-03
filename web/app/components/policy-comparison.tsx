import Link from "next/link";
import type { PolicyComparison } from "@/lib/types";

export function PolicyComparisonView({ comparison }: { comparison: PolicyComparison }) {
  return (
    <main className="analysis-shell">
      <header className="analysis-hero">
        <div>
          <p className="eyebrow">Immutable policy comparison</p>
          <h1>What changed in the proposed policy?</h1>
          <p className="lede">
            AI proposed each policy extraction. Deterministic validation accepted the typed rules,
            and deterministic code calculated this comparison.
          </p>
        </div>
        <div className="boundary-legend">
          <span className="badge deterministic">Deterministic comparison</span>
          <span className="badge human_input">Initiated by {comparison.created_by}</span>
        </div>
      </header>

      <section className="comparison-source-grid">
        <SourceCard label="Baseline policy" source={comparison.baseline} />
        <SourceCard label="Proposed revision" source={comparison.proposed} />
      </section>

      <section className="journey-card comparison-results">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Accepted typed semantics</p>
            <h2>
              {comparison.difference_count} semantic{" "}
              {comparison.difference_count === 1 ? "difference" : "differences"}
            </h2>
          </div>
          <span>Immutable · {formatDateTime(comparison.created_at)}</span>
        </div>
        {comparison.differences.length === 0 ? (
          <div className="empty-panel">
            <h3>No operational semantic differences</h3>
            <p>
              The accepted typed rules are equivalent. Wording and source-span changes are not
              treated as policy-rule changes.
            </p>
          </div>
        ) : (
          <ol className="difference-list">
            {comparison.differences.map((difference) => (
              <li key={difference.id} className="difference-card">
                <div className="difference-heading">
                  <div>
                    <span className={`badge ${difference.change_type}`}>
                      {humanize(difference.change_type)}
                    </span>
                    <h3>{humanize(difference.field_path)}</h3>
                  </div>
                  <span className="materiality">Operationally material</span>
                </div>
                <div className="semantic-values">
                  <SemanticValue label="Baseline value" value={difference.baseline_value} />
                  <SemanticValue label="Proposed value" value={difference.proposed_value} />
                </div>
                <dl className="comparison">
                  <div>
                    <dt>Reason code</dt>
                    <dd>{difference.reason_code}</dd>
                  </div>
                  <div>
                    <dt>Rule identity</dt>
                    <dd>{difference.rule_identity}</dd>
                  </div>
                </dl>
                <div className="provenance-grid">
                  <Provenance label="Baseline provenance" value={difference.baseline_provenance} />
                  <Provenance label="Proposed provenance" value={difference.proposed_provenance} />
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="impact-delta-notice">
        <p className="eyebrow">Deliberate boundary</p>
        <h2>Enterprise impact delta has not been calculated</h2>
        <p>
          This artifact compares policy obligations only. It does not identify newly affected or
          no-longer-affected workers, systems, documents, training, commitments, or actions.
        </p>
      </section>
      <Link href="/">Return to policy analysis and comparison</Link>
    </main>
  );
}

function SourceCard({
  label,
  source,
}: {
  label: string;
  source: PolicyComparison["baseline"];
}) {
  return (
    <article className="journey-card">
      <p className="eyebrow">{label}</p>
      <h2>{source.title}</h2>
      <dl className="comparison">
        <div>
          <dt>Effective</dt>
          <dd>{formatDate(source.effective_date)}</dd>
        </div>
        <div>
          <dt>Source record</dt>
          <dd>{source.policy_change_id}</dd>
        </div>
        <div>
          <dt>Accepted extraction</dt>
          <dd>{source.accepted_extraction_attempt_id}</dd>
        </div>
      </dl>
    </article>
  );
}

function SemanticValue({ label, value }: { label: string; value: unknown | null }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value === null ? "Not present" : String(value)}</strong>
    </div>
  );
}

function Provenance({
  label,
  value,
}: {
  label: string;
  value: Record<string, unknown> | null;
}) {
  if (!value) {
    return (
      <div>
        <h4>{label}</h4>
        <p>No source value exists on this side.</p>
      </div>
    );
  }
  return (
    <div>
      <h4>{label}</h4>
      {value.source === "human" ? (
        <p>
          Human clarification by {String(value.responder_identity ?? "recorded reviewer")}
        </p>
      ) : (
        <>
          <blockquote>{String(value.quote)}</blockquote>
          <small>
            Validated source span {String(value.start)}–{String(value.end)}
          </small>
        </>
      )}
    </div>
  );
}

function humanize(value: string) {
  return value.replaceAll(".", " · ").replaceAll("_", " ");
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
