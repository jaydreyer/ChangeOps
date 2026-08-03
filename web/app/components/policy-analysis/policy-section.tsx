import type { AnalysisPolicy } from "@/lib/types";

export function PolicySection({ policy }: { policy: AnalysisPolicy }) {
  return (
    <section className="journey-card policy-detail" aria-labelledby="policy-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Authoritative source</p>
          <h2 id="policy-heading">What policy are we evaluating?</h2>
        </div>
        <span className="quiet-label">Version {policy.version}</span>
      </div>
      <dl className="policy-meta">
        <div>
          <dt>Owner</dt>
          <dd>{policy.owner}</dd>
        </div>
        <div>
          <dt>Organization</dt>
          <dd>{policy.organization_name}</dd>
        </div>
      </dl>
      <blockquote className="policy-text">{policy.policy_text}</blockquote>
      <details className="technical-disclosure">
        <summary>View policy identity</summary>
        <dl className="identifiers">
          <div>
            <dt>Policy ID</dt>
            <dd>{policy.id}</dd>
          </div>
        </dl>
      </details>
    </section>
  );
}
