import type { AnalysisPolicy } from "@/lib/types";

export function PolicySection({ policy }: { policy: AnalysisPolicy }) {
  return (
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
  );
}
