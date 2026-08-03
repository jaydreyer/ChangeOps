import Link from "next/link";
import type { ReactNode } from "react";
import type {
  EnterpriseImpactDelta,
  FindingImpactDelta,
  ImpactDeltaEvidence,
  PolicyComparison,
  WorkerImpactDelta,
} from "@/lib/types";

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

      {comparison.impact_delta ? (
        <ImpactDeltaView delta={comparison.impact_delta} />
      ) : (
        <section className="impact-delta-notice">
          <p className="eyebrow">Historical comparison</p>
          <h2>Enterprise impact delta is unavailable</h2>
          <p>This comparison predates the immutable enterprise impact delta contract.</p>
        </section>
      )}
      <section className="impact-delta-notice">
        <p className="eyebrow">Deliberate boundary</p>
        <h2>AI explanation remains deferred</h2>
        <p>
          Deterministic code calculated and persisted every delta below from the two immutable
          assessments. No model classified workers, findings, impacts, reasons, or evidence.
        </p>
      </section>
      <Link href="/">Return to policy analysis and comparison</Link>
    </main>
  );
}

function ImpactDeltaView({
  delta,
}: {
  delta: NonNullable<PolicyComparison["impact_delta"]>;
}) {
  const summary = delta.summary;
  return (
    <section className="journey-card impact-delta-results">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Immutable enterprise impact delta</p>
          <h2>How did the persisted operational outcomes differ?</h2>
        </div>
        <span>Deterministic · {formatDateTime(delta.created_at)}</span>
      </div>

      <aside className="impact-delta-scope" aria-label="Enterprise impact delta scope">
        <h3>Outcome comparison, not sole-cause proof</h3>
        <p>
          This delta compares two authoritative persisted assessment outcomes. If enterprise
          source facts differed between assessment runs, it does not prove that policy changes
          alone caused every difference.
        </p>
        <p>
          The seeded demonstration evaluates both assessments against the same enterprise catalog
          state. This milestone does not version or compare generalized enterprise snapshots.
        </p>
      </aside>

      <div className="delta-summary" aria-label="Enterprise impact delta summary">
        <SummaryCount label="Workers became affected" value={summary.workers_became_affected} />
        <SummaryCount
          label="Workers no longer affected"
          value={summary.workers_no_longer_affected}
        />
        <SummaryCount label="Workers remain affected" value={summary.workers_remained_affected} />
        <SummaryCount label="Findings introduced" value={summary.findings_introduced} />
        <SummaryCount label="Findings disappeared" value={summary.findings_disappeared} />
        <SummaryCount
          label="Enterprise impacts introduced"
          value={summary.enterprise_impacts_introduced}
        />
        <SummaryCount label="Enterprise impacts removed" value={summary.enterprise_impacts_removed} />
      </div>

      <DeltaSection title="Worker impact changes" empty={delta.worker_deltas.length === 0}>
        {delta.worker_deltas.map((item) => (
          <WorkerDeltaCard key={item.id} item={item} />
        ))}
      </DeltaSection>
      <DeltaSection title="Finding changes" empty={delta.finding_deltas.length === 0}>
        {delta.finding_deltas.map((item) => (
          <FindingDeltaCard key={item.id} item={item} />
        ))}
      </DeltaSection>
      <DeltaSection
        title="Enterprise impact changes"
        empty={delta.enterprise_impact_deltas.length === 0}
      >
        {delta.enterprise_impact_deltas.map((item) => (
          <EnterpriseImpactDeltaCard key={item.id} item={item} />
        ))}
      </DeltaSection>

      <dl className="comparison delta-lineage">
        <div>
          <dt>Baseline assessment</dt>
          <dd>{delta.baseline_assessment_id}</dd>
        </div>
        <div>
          <dt>Proposed assessment</dt>
          <dd>{delta.proposed_assessment_id}</dd>
        </div>
        <div>
          <dt>Delta fingerprint</dt>
          <dd>{delta.impact_delta_fingerprint}</dd>
        </div>
      </dl>
    </section>
  );
}

function SummaryCount({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function DeltaSection({
  title,
  empty,
  children,
}: {
  title: string;
  empty: boolean;
  children: ReactNode;
}) {
  return (
    <section className="delta-section">
      <h3>{title}</h3>
      {empty ? <p className="empty-panel">No changes in this category.</p> : <ol>{children}</ol>}
    </section>
  );
}

function WorkerDeltaCard({ item }: { item: WorkerImpactDelta }) {
  const display = item.proposed?.display_name ?? item.baseline?.display_name ?? item.stable_identity;
  return (
    <li className="difference-card">
      <DeltaHeading changeType={item.change_type} title={display} reason={item.delta_reason_code} />
      <div className="delta-sides">
        <WorkerSide label="Baseline assessment" value={item.baseline} />
        <WorkerSide label="Proposed assessment" value={item.proposed} />
      </div>
    </li>
  );
}

function WorkerSide({
  label,
  value,
}: {
  label: string;
  value: WorkerImpactDelta["baseline"];
}) {
  if (!value) return <MissingSide label={label} />;
  return (
    <article className="delta-side">
      <h4>{label}</h4>
      <p className="side-classification">{humanize(value.classification)}</p>
      <p>{value.explanation}</p>
      <p className="identifiers">{value.reason_codes.join(" · ")}</p>
      <EvidenceList evidence={value.evidence} />
    </article>
  );
}

function FindingDeltaCard({ item }: { item: FindingImpactDelta }) {
  const side = item.proposed ?? item.baseline;
  return (
    <li className="difference-card">
      <DeltaHeading
        changeType={item.change_type}
        title={humanize(side?.finding_type ?? item.stable_identity)}
        reason={item.delta_reason_code}
      />
      <div className="delta-sides">
        <FindingSide label="Baseline finding" value={item.baseline} />
        <FindingSide label="Proposed finding" value={item.proposed} />
      </div>
    </li>
  );
}

function FindingSide({
  label,
  value,
}: {
  label: string;
  value: FindingImpactDelta["baseline"];
}) {
  if (!value) return <MissingSide label={label} />;
  return (
    <article className="delta-side">
      <h4>{label}</h4>
      <p>{value.explanation}</p>
      <p className="identifiers">
        {value.rule_code} · {humanize(value.severity)} · {value.worker_id}
      </p>
      <EvidenceList evidence={value.evidence} />
    </article>
  );
}

function EnterpriseImpactDeltaCard({ item }: { item: EnterpriseImpactDelta }) {
  const side = item.proposed ?? item.baseline;
  return (
    <li className="difference-card">
      <DeltaHeading
        changeType={item.change_type}
        title={side?.display_name ?? item.stable_identity}
        reason={item.delta_reason_code}
      />
      <div className="delta-sides">
        <EnterpriseImpactSide label="Baseline impact" value={item.baseline} />
        <EnterpriseImpactSide label="Proposed impact" value={item.proposed} />
      </div>
    </li>
  );
}

function EnterpriseImpactSide({
  label,
  value,
}: {
  label: string;
  value: EnterpriseImpactDelta["baseline"];
}) {
  if (!value) return <MissingSide label={label} />;
  return (
    <article className="delta-side">
      <h4>{label}</h4>
      <p>{value.explanation}</p>
      <p className="identifiers">
        {value.reason_code} · {humanize(value.domain)} · {humanize(value.classification)}
      </p>
      <p className="relationship-path">
        {value.relationship_path.map((element) => element.display_label).join(" → ")}
      </p>
      <EvidenceList evidence={value.evidence} />
    </article>
  );
}

function DeltaHeading({
  changeType,
  title,
  reason,
}: {
  changeType: string;
  title: string;
  reason: string;
}) {
  return (
    <div className="difference-heading">
      <div>
        <span className={`badge ${changeType}`}>{humanize(changeType)}</span>
        <h3>{title}</h3>
      </div>
      <span className="identifiers">{reason}</span>
    </div>
  );
}

function MissingSide({ label }: { label: string }) {
  return (
    <article className="delta-side missing-side">
      <h4>{label}</h4>
      <p>No matching persisted record exists on this side.</p>
    </article>
  );
}

function EvidenceList({ evidence }: { evidence: ImpactDeltaEvidence[] }) {
  return (
    <details className="delta-evidence">
      <summary>{evidence.length} authoritative evidence records</summary>
      <ul>
        {evidence.map((item) => (
          <li key={item.record_id}>
            <strong>{item.label}</strong>
            <span>
              {item.source_type} · {item.source_id} · {item.evidence_key}
            </span>
          </li>
        ))}
      </ul>
    </details>
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
