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
      <header className="analysis-hero comparison-hero">
        <div>
          <Link href="/" className="back-link">
            ← All policy analyses and comparisons
          </Link>
          <p className="product-mark">ChangeOps</p>
          <p className="eyebrow">Policy comparison</p>
          <h1>Compare policy versions</h1>
          <p className="lede">
            See the accepted policy obligations first, then inspect how the two persisted
            operational outcomes differ.
          </p>
        </div>
        <div className="analysis-status-panel comparison-status-panel">
          <span className="badge deterministic">Deterministic result</span>
          <strong>Authoritative comparison</strong>
          <span>Immutable persisted record</span>
          <span className="quiet-label">Initiated by {comparison.created_by}</span>
          <details className="technical-disclosure">
            <summary>View comparison identity</summary>
            <dl className="identifiers">
              <div>
                <dt>Comparison</dt>
                <dd>{comparison.id}</dd>
              </div>
              <div>
                <dt>Created</dt>
                <dd>
                  <time dateTime={comparison.created_at}>
                    {formatDateTime(comparison.created_at)}
                  </time>
                </dd>
              </div>
            </dl>
          </details>
        </div>
      </header>

      <section className="comparison-policy-section" aria-labelledby="policies-compared-heading">
        <div className="section-heading comparison-section-heading">
          <div>
            <p className="eyebrow">Policies being compared</p>
            <h2 id="policies-compared-heading">Current policy and proposed revision</h2>
          </div>
          <span>
            <time dateTime={comparison.created_at}>{formatDateTime(comparison.created_at)}</time>
          </span>
        </div>
        <div className="comparison-source-grid">
          <SourceCard label="Baseline policy" source={comparison.baseline} />
          <SourceCard label="Proposed revision" source={comparison.proposed} />
        </div>
      </section>

      <section
        className="journey-card comparison-results policy-change-results"
        aria-labelledby="policy-changes-heading"
      >
        <div className="section-heading">
          <div>
            <p className="eyebrow">Accepted typed semantics</p>
            <h2 id="policy-changes-heading">What policy obligations changed</h2>
            <p>
              {comparison.difference_count} deterministic semantic{" "}
              {comparison.difference_count === 1 ? "difference" : "differences"}
            </p>
          </div>
          <span className="badge deterministic">Immutable accepted rules</span>
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
              <li
                key={difference.id}
                className={`difference-card difference-card-${difference.change_type}`}
              >
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
                <details className="technical-disclosure comparison-technical">
                  <summary>View accepted rule evidence and identity</summary>
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
                </details>
              </li>
            ))}
          </ol>
        )}
      </section>

      {comparison.impact_delta ? (
        <>
          <ChangeSummary comparison={comparison} delta={comparison.impact_delta} />
          <ImpactDeltaView delta={comparison.impact_delta} />
        </>
      ) : (
        <section className="impact-delta-notice">
          <p className="eyebrow">Historical comparison</p>
          <h2>Enterprise impact delta is unavailable</h2>
          <p>This comparison predates the immutable enterprise impact delta contract.</p>
        </section>
      )}
      <section
        className="impact-delta-notice technical-boundary comparison-boundary-notice"
        aria-labelledby="comparison-ai-boundary-heading"
      >
        <p className="eyebrow">Deliberate boundary</p>
        <h2 id="comparison-ai-boundary-heading">AI explanation remains deferred</h2>
        <p>
          AI proposed each extraction. Deterministic validation accepted the rules, and
          deterministic code calculated and persisted every delta from the two immutable
          assessments. No model classified workers, findings, impacts, reasons, or evidence.
        </p>
      </section>
      <ComparisonLineage comparison={comparison} />
      <Link href="/" className="back-link comparison-return-link">
        ← Return to policy analysis and comparison
      </Link>
    </main>
  );
}

function ChangeSummary({
  comparison,
  delta,
}: {
  comparison: PolicyComparison;
  delta: NonNullable<PolicyComparison["impact_delta"]>;
}) {
  const policyCounts = countByChangeType(comparison.differences);
  const workerTotal =
    delta.summary.workers_became_affected +
    delta.summary.workers_no_longer_affected +
    delta.summary.workers_remained_affected;
  const findingTotal =
    delta.summary.findings_introduced + delta.summary.findings_disappeared;
  const impactTotal =
    delta.summary.enterprise_impacts_introduced + delta.summary.enterprise_impacts_removed;

  return (
    <section className="journey-card change-story" aria-labelledby="change-summary-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Business story first</p>
          <h2 id="change-summary-heading">Change summary</h2>
          <p>Deterministic comparison of the two persisted policy and assessment outcomes.</p>
        </div>
        <span className="badge deterministic">No sole-cause claim</span>
      </div>
      <ol className="change-story-flow" aria-label="Policy and operational outcome summary">
        <ChangeStoryStage
          value={comparison.difference_count}
          label="Policy obligations changed"
          breakdown={[
            `${policyCounts.added ?? 0} added`,
            `${policyCounts.removed ?? 0} removed`,
            `${policyCounts.modified ?? 0} modified`,
          ]}
        />
        <ChangeStoryStage
          value={workerTotal}
          label="Worker-trip outcomes in the delta"
          breakdown={[
            `${delta.summary.workers_became_affected} became affected`,
            `${delta.summary.workers_no_longer_affected} no longer affected`,
            `${delta.summary.workers_remained_affected} remain affected`,
          ]}
        />
        <ChangeStoryStage
          value={findingTotal}
          label="Finding differences"
          breakdown={[
            `${delta.summary.findings_introduced} introduced`,
            `${delta.summary.findings_disappeared} disappeared`,
          ]}
        />
        <ChangeStoryStage
          value={impactTotal}
          label="Enterprise impact differences"
          breakdown={[
            `${delta.summary.enterprise_impacts_introduced} introduced`,
            `${delta.summary.enterprise_impacts_removed} removed`,
          ]}
        />
      </ol>
    </section>
  );
}

function ChangeStoryStage({
  value,
  label,
  breakdown,
}: {
  value: number;
  label: string;
  breakdown: string[];
}) {
  return (
    <li>
      <strong>{value}</strong>
      <span>{label}</span>
      <small>{breakdown.join(" · ")}</small>
    </li>
  );
}

function ImpactDeltaView({
  delta,
}: {
  delta: NonNullable<PolicyComparison["impact_delta"]>;
}) {
  const summary = delta.summary;
  return (
    <section
      className="journey-card impact-delta-results"
      aria-labelledby="operational-impact-heading"
    >
      <div className="section-heading">
        <div>
          <p className="eyebrow">Immutable enterprise impact delta</p>
          <h2 id="operational-impact-heading">Operational impact changes</h2>
          <p>Comparison of two authoritative persisted assessment outcomes.</p>
        </div>
        <span className="badge deterministic">Deterministically calculated</span>
      </div>

      <aside className="impact-delta-scope" aria-label="Enterprise impact delta scope">
        <span className="badge deterministic">Assessment outcome scope</span>
        <h3>What this comparison can establish</h3>
        <p>
          ChangeOps compares two authoritative persisted assessment outcomes. It does not claim
          that policy changes were the sole cause when enterprise source facts differ between
          runs.
        </p>
        <details>
          <summary>Seeded demonstration scope</summary>
          <p>
            Both assessments use the same fictional enterprise catalog state. This milestone does
            not version or compare generalized enterprise snapshots.
          </p>
        </details>
      </aside>

      <div className="delta-summary" aria-label="Enterprise impact delta summary">
        <SummaryCount
          label="Worker-trip outcomes became affected"
          value={summary.workers_became_affected}
        />
        <SummaryCount
          label="Worker-trip outcomes no longer affected"
          value={summary.workers_no_longer_affected}
        />
        <SummaryCount
          label="Worker-trip outcomes remain affected"
          value={summary.workers_remained_affected}
        />
        <SummaryCount label="Findings introduced" value={summary.findings_introduced} />
        <SummaryCount label="Findings disappeared" value={summary.findings_disappeared} />
        <SummaryCount
          label="Enterprise impacts introduced"
          value={summary.enterprise_impacts_introduced}
        />
        <SummaryCount label="Enterprise impacts removed" value={summary.enterprise_impacts_removed} />
      </div>

      <DeltaSection
        title="Worker impact changes"
        count={delta.worker_deltas.length}
        breakdown={[
          `${summary.workers_became_affected} became affected`,
          `${summary.workers_no_longer_affected} no longer affected`,
          `${summary.workers_remained_affected} remain affected`,
        ]}
      >
        {delta.worker_deltas.map((item) => (
          <WorkerDeltaCard key={item.id} item={item} />
        ))}
      </DeltaSection>
      <DeltaSection
        title="Finding changes"
        count={delta.finding_deltas.length}
        breakdown={[
          `${summary.findings_introduced} introduced`,
          `${summary.findings_disappeared} disappeared`,
        ]}
      >
        {delta.finding_deltas.map((item) => (
          <FindingDeltaCard key={item.id} item={item} />
        ))}
      </DeltaSection>
      <DeltaSection
        title="Enterprise impact changes"
        count={delta.enterprise_impact_deltas.length}
        breakdown={[
          `${summary.enterprise_impacts_introduced} introduced`,
          `${summary.enterprise_impacts_removed} removed`,
        ]}
      >
        {delta.enterprise_impact_deltas.map((item) => (
          <EnterpriseImpactDeltaCard key={item.id} item={item} />
        ))}
      </DeltaSection>
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
  count,
  breakdown,
  children,
}: {
  title: string;
  count: number;
  breakdown: string[];
  children: ReactNode;
}) {
  return (
    <section className="delta-section">
      <div className="delta-group-heading">
        <div>
          <h3>{title}</h3>
          <p>{count} persisted delta records</p>
        </div>
        <ul aria-label={`${title} classification counts`}>
          {breakdown.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
      {count === 0 ? (
        <p className="empty-panel">No differences are recorded in this category.</p>
      ) : (
        <ol>{children}</ol>
      )}
    </section>
  );
}

function WorkerDeltaCard({ item }: { item: WorkerImpactDelta }) {
  const display = item.proposed?.display_name ?? item.baseline?.display_name ?? item.stable_identity;
  const tripId = item.proposed?.trip_id ?? item.baseline?.trip_id ?? "unknown trip";
  return (
    <li>
      <details className={`delta-item delta-item-${item.change_type}`}>
        <summary>
          <DeltaItemSummary
            changeType={item.change_type}
            title={display}
            reason={item.delta_reason_code}
            status={`${workerStatus(item.baseline)} → ${workerStatus(item.proposed)} · Trip ${tripId}`}
          />
        </summary>
        <div className="delta-item-body">
          <div className="delta-sides">
            <WorkerSide label="Baseline assessment" value={item.baseline} />
            <WorkerSide label="Proposed assessment" value={item.proposed} />
          </div>
          <DeltaItemLineage item={item} />
        </div>
      </details>
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
    <li>
      <details className={`delta-item delta-item-${item.change_type}`}>
        <summary>
          <DeltaItemSummary
            changeType={item.change_type}
            title={humanize(side?.finding_type ?? item.stable_identity)}
            reason={item.delta_reason_code}
            status={`${recordStatus(item.baseline)} → ${recordStatus(item.proposed)}`}
          />
        </summary>
        <div className="delta-item-body">
          <div className="delta-sides">
            <FindingSide label="Baseline finding" value={item.baseline} />
            <FindingSide label="Proposed finding" value={item.proposed} />
          </div>
          <DeltaItemLineage item={item} />
        </div>
      </details>
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
    <li>
      <details className={`delta-item delta-item-${item.change_type}`}>
        <summary>
          <DeltaItemSummary
            changeType={item.change_type}
            title={side?.display_name ?? item.stable_identity}
            reason={item.delta_reason_code}
            status={`${impactStatus(item.baseline)} → ${impactStatus(item.proposed)}`}
          />
        </summary>
        <div className="delta-item-body">
          <div className="delta-sides">
            <EnterpriseImpactSide label="Baseline impact" value={item.baseline} />
            <EnterpriseImpactSide label="Proposed impact" value={item.proposed} />
          </div>
          <DeltaItemLineage item={item} />
        </div>
      </details>
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

function DeltaItemSummary({
  changeType,
  title,
  reason,
  status,
}: {
  changeType: string;
  title: string;
  reason: string;
  status: string;
}) {
  return (
    <span className="delta-item-summary">
      <span className="change-symbol" aria-hidden="true">
        {changeSymbol(changeType)}
      </span>
      <span className="delta-item-title">
        <span className={`badge ${changeType}`}>{humanize(changeType)}</span>
        <strong>{title}</strong>
        <small>{status}</small>
      </span>
      <code>{reason}</code>
    </span>
  );
}

function DeltaItemLineage({
  item,
}: {
  item: WorkerImpactDelta | FindingImpactDelta | EnterpriseImpactDelta;
}) {
  return (
    <dl className="comparison delta-item-lineage">
      <div>
        <dt>Stable business identity</dt>
        <dd>{item.stable_identity}</dd>
      </div>
      <div>
        <dt>Baseline record lineage</dt>
        <dd>{item.baseline_record_id ?? "No matching record"}</dd>
      </div>
      <div>
        <dt>Proposed record lineage</dt>
        <dd>{item.proposed_record_id ?? "No matching record"}</dd>
      </div>
    </dl>
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

function ComparisonLineage({ comparison }: { comparison: PolicyComparison }) {
  const delta = comparison.impact_delta;
  return (
    <section className="journey-card comparison-lineage" aria-labelledby="lineage-heading">
      <p className="eyebrow">Immutable lineage</p>
      <h2 id="lineage-heading">Evidence and technical identity</h2>
      <details className="technical-disclosure">
        <summary>View comparison, extraction, assessment, and fingerprint lineage</summary>
        <div className="lineage-grid">
          <dl className="comparison">
            <div>
              <dt>Comparison ID</dt>
              <dd>{comparison.id}</dd>
            </div>
            <div>
              <dt>Comparison contract</dt>
              <dd>{comparison.comparison_contract_version}</dd>
            </div>
            <div>
              <dt>Comparison fingerprint</dt>
              <dd>{comparison.comparison_fingerprint}</dd>
            </div>
            <div>
              <dt>Created by</dt>
              <dd>{comparison.created_by}</dd>
            </div>
            <div>
              <dt>Created</dt>
              <dd>
                <time dateTime={comparison.created_at}>
                  {formatDateTime(comparison.created_at)}
                </time>
              </dd>
            </div>
          </dl>
          <dl className="comparison">
            <div>
              <dt>Baseline policy record</dt>
              <dd>{comparison.baseline.policy_change_id}</dd>
            </div>
            <div>
              <dt>Baseline accepted extraction</dt>
              <dd>{comparison.baseline.accepted_extraction_attempt_id}</dd>
            </div>
            <div>
              <dt>Proposed policy record</dt>
              <dd>{comparison.proposed.policy_change_id}</dd>
            </div>
            <div>
              <dt>Proposed accepted extraction</dt>
              <dd>{comparison.proposed.accepted_extraction_attempt_id}</dd>
            </div>
          </dl>
          {delta && (
            <dl className="comparison">
              <div>
                <dt>Baseline assessment</dt>
                <dd>{delta.baseline_assessment_id}</dd>
              </div>
              <div>
                <dt>Proposed assessment</dt>
                <dd>{delta.proposed_assessment_id}</dd>
              </div>
              <div>
                <dt>Delta contract</dt>
                <dd>{delta.impact_delta_contract_version}</dd>
              </div>
              <div>
                <dt>Delta fingerprint</dt>
                <dd>{delta.impact_delta_fingerprint}</dd>
              </div>
              <div>
                <dt>Delta created</dt>
                <dd>
                  <time dateTime={delta.created_at}>{formatDateTime(delta.created_at)}</time>
                </dd>
              </div>
            </dl>
          )}
        </div>
      </details>
    </section>
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
    <article className="journey-card comparison-source-card">
      <p className="eyebrow">{label}</p>
      <h3>{source.title}</h3>
      <dl className="comparison">
        <div>
          <dt>Effective</dt>
          <dd>{formatDate(source.effective_date)}</dd>
        </div>
        <div>
          <dt>Version</dt>
          <dd>{source.version}</dd>
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
  const label = value.replaceAll(".", " · ").replaceAll("_", " ");
  return label.replace(/^\w/, (letter) => letter.toUpperCase());
}

function countByChangeType(items: PolicyComparison["differences"]) {
  return items.reduce<Record<string, number>>((counts, item) => {
    counts[item.change_type] = (counts[item.change_type] ?? 0) + 1;
    return counts;
  }, {});
}

function workerStatus(value: WorkerImpactDelta["baseline"]) {
  return value ? humanize(value.classification) : "No matching record";
}

function recordStatus(value: unknown) {
  return value ? "Present" : "Not present";
}

function impactStatus(value: EnterpriseImpactDelta["baseline"]) {
  return value ? humanize(value.classification) : "Not present";
}

function changeSymbol(changeType: string) {
  if (["introduced", "became_affected", "added"].includes(changeType)) return "+";
  if (["removed", "disappeared", "no_longer_affected"].includes(changeType)) return "−";
  return "↔";
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
    timeZone: "UTC",
  }).format(new Date(value));
}
