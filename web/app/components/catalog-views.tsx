import Link from "next/link";
import type {
  CatalogBrowse,
  CatalogObjectDetail,
  CatalogObjectSummary,
  CatalogObjectType,
  PolicyRuleReference,
} from "@/lib/types";

const CATEGORY_LABELS: Record<CatalogObjectType, string> = {
  enterprise_document: "Documents",
  enterprise_system: "Systems",
  training_course: "Training",
};

const OBJECT_LABELS: Record<CatalogObjectType, string> = {
  enterprise_document: "Document",
  enterprise_system: "System",
  training_course: "Training course",
};

const CATEGORY_ORDER: CatalogObjectType[] = [
  "enterprise_document",
  "enterprise_system",
  "training_course",
];

export function CatalogBrowseView({ catalog }: { catalog: CatalogBrowse }) {
  return (
    <main className="analysis-shell catalog-shell">
      <header className="catalog-hero">
        <div>
          <Link href="/" className="back-link">
            ← Return to policy analysis
          </Link>
          <p className="product-mark">ChangeOps</p>
          <p className="eyebrow">Enterprise Knowledge Catalog</p>
          <h1>What enterprise knowledge does ChangeOps use?</h1>
          <p className="lede">
            Browse the current typed records and the policy-scoped relationships ChangeOps uses
            during deterministic impact assessment.
          </p>
        </div>
        <aside className="catalog-context-notice" aria-label="Catalog authority boundary">
          <strong>{catalog.catalog_context.label}</strong>
          <p>
            This is fictional demonstration data. Object-level origin is not recorded; seeded
            relationship origin is available on each object detail.
          </p>
        </aside>
      </header>

      <nav className="catalog-category-nav" aria-label="Catalog categories">
        {CATEGORY_ORDER.map((type) => (
          <a key={type} href={`#${type}`}>
            <strong>{catalog.catalog_counts[type]}</strong>
            <span>{CATEGORY_LABELS[type]}</span>
          </a>
        ))}
      </nav>

      {CATEGORY_ORDER.map((type) => {
        const objects = catalog.objects.filter((item) => item.object_type === type);
        return (
          <section key={type} id={type} className="catalog-category" aria-labelledby={`${type}-heading`}>
            <div className="section-heading">
              <div>
                <p className="eyebrow">Primary catalog category</p>
                <h2 id={`${type}-heading`}>{CATEGORY_LABELS[type]}</h2>
              </div>
              <span className="quiet-label">{catalog.catalog_counts[type]} records</span>
            </div>
            <div className="catalog-object-grid">
              {objects.map((object) => (
                <CatalogObjectCard key={object.object_id} object={object} />
              ))}
            </div>
          </section>
        );
      })}

      <section className="journey-card assessment-context" aria-labelledby="context-heading">
        <p className="eyebrow">Assessment context</p>
        <h2 id="context-heading">Other authoritative inputs</h2>
        <p>
          These stored records help calculate impact. PR A keeps them as context counts and does
          not create personnel, team, or commitment detail pages.
        </p>
        <dl className="catalog-count-list">
          <Count label="Workers" value={catalog.assessment_context_counts.worker} />
          <Count label="Teams" value={catalog.assessment_context_counts.team} />
          <Count
            label="Customer commitments"
            value={catalog.assessment_context_counts.customer_commitment}
          />
        </dl>
      </section>
    </main>
  );
}

function CatalogObjectCard({ object }: { object: CatalogObjectSummary }) {
  return (
    <article className="journey-card catalog-object-card">
      <div className="section-heading">
        <span className="badge deterministic">{OBJECT_LABELS[object.object_type]}</span>
        <span className="quiet-label">{humanize(object.status.value ?? "not_recorded")}</span>
      </div>
      <h3>{object.display_name}</h3>
      <p>{object.description ?? summaryMetadata(object)}</p>
      <dl className="catalog-card-meta">
        <div>
          <dt>Stable identity</dt>
          <dd className="technical-value">{object.object_id}</dd>
        </div>
        <div>
          <dt>Source system</dt>
          <dd>{object.source_system ?? "Not recorded"}</dd>
        </div>
        <div>
          <dt>Policy relationships</dt>
          <dd>{object.relationship_count}</dd>
        </div>
      </dl>
      <Link
        href={`/catalog/${object.object_type}/${object.object_id}`}
        aria-label={`Open ${object.display_name} details`}
      >
        Open details
      </Link>
    </article>
  );
}

export function CatalogObjectDetailView({ detail }: { detail: CatalogObjectDetail }) {
  const object = detail.object;
  return (
    <main className="analysis-shell catalog-shell">
      <Link href="/catalog" className="back-link">
        ← Back to enterprise knowledge
      </Link>
      <header className="catalog-detail-hero">
        <div>
          <p className="product-mark">ChangeOps</p>
          <p className="eyebrow">{OBJECT_LABELS[object.object_type]}</p>
          <h1>{object.display_name}</h1>
          <p className="lede">{object.description ?? "No description is recorded in the current catalog."}</p>
        </div>
        <span className="badge deterministic">{humanize(object.status.value ?? "not_recorded")}</span>
      </header>

      <section className="journey-card" aria-labelledby="catalog-facts-heading">
        <p className="eyebrow">Stored catalog facts</p>
        <h2 id="catalog-facts-heading">What ChangeOps currently records</h2>
        <dl className="catalog-fact-grid">
          <Fact label="Object type" value={OBJECT_LABELS[object.object_type]} />
          <Fact label="Status" value={humanize(object.status.value ?? "not_recorded")} />
          <Fact label="Source system" value={object.source_system ?? "Not recorded"} />
          <Fact label="Owner" value={object.owner ?? "Not recorded"} />
          {detailMetadata(object)}
        </dl>
        <div className="catalog-boundary-note">
          <strong>Catalog context: Seeded demonstration catalog</strong>
          <p>
            This dataset context is known from the bounded demo. Object-level creator, import,
            curation, and approval provenance are not recorded.
          </p>
        </div>
      </section>

      {object.object_type === "enterprise_document" && (
        <ExternalDocumentIdentity detail={detail} />
      )}

      <section className="catalog-category" aria-labelledby="relationships-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Explanatory relationships</p>
            <h2 id="relationships-heading">Why ChangeOps trusts these connections</h2>
          </div>
          <span className="quiet-label">{detail.relationships.length} persisted rows</span>
        </div>
        <p className="section-intro">
          Each connection is trusted as deterministic analyzer input because it is a persisted row
          in a typed dependency table with enforced foreign keys. Relationship origin is recorded
          separately and does not imply human approval.
        </p>
        <div className="catalog-relationship-list">
          {detail.relationships.map((relationship) => {
            const [policyId, ruleCode] = splitRuleKey(relationship.source.stable_key);
            return (
              <article className="journey-card catalog-relationship" key={relationship.relationship_id}>
                <div className="section-heading">
                  <span className="badge deterministic">Trusted enterprise relationship</span>
                  {relationship.impact_classification && (
                    <span className="quiet-label">{humanize(relationship.impact_classification)}</span>
                  )}
                </div>
                <h3>Relationship Provenance</h3>
                <dl className="catalog-relationship-summary">
                  <Fact
                    label="Relationship"
                    value={`${relationship.target.display_name} → ${relationship.source.display_name}`}
                  />
                  <Fact
                    label="Policy scope"
                    value={`${relationship.policy.title} · ${relationship.policy.version}`}
                  />
                  <Fact label="Relationship type" value={humanize(relationship.relationship_type)} />
                  <Fact label="Business explanation" value={relationship.explanation} />
                  <Fact label="Source" value={relationship.provenance.source_label} />
                  <Fact label="Trust level" value={humanize(relationship.trust.level)} />
                  <Fact
                    label="AI involvement"
                    value="None — AI did not create or infer this relationship."
                  />
                </dl>
                <p className="catalog-provenance-note">
                  Recorded by {relationship.provenance.owning_authority} on{" "}
                  {formatDateTime(relationship.provenance.recorded_at)}.
                </p>
                <Link href={`/catalog/policy-rules/${policyId}/${ruleCode}`}>
                  Explain this policy rule
                </Link>
                <details className="technical-disclosure">
                  <summary>Technical relationship details</summary>
                  <dl className="catalog-technical-grid">
                    <Fact label="Relationship row" value={relationship.relationship_id} technical />
                    <Fact label="Policy-scoped identity" value={relationship.source.stable_key} technical />
                    <Fact label="Relationship type" value={relationship.relationship_type} technical />
                    <Fact label="Provenance category" value={relationship.provenance.classification} technical />
                    <Fact label="Provenance reference" value={relationship.provenance.reference} technical />
                    <Fact label="Trust basis" value={relationship.trust.basis} technical />
                    <Fact label="Integrity basis" value={relationship.trust.integrity.join(", ")} technical />
                  </dl>
                </details>
              </article>
            );
          })}
        </div>
      </section>

      <section className="journey-card catalog-usage" aria-labelledby="usage-heading">
        <p className="eyebrow">How ChangeOps uses this</p>
        <h2 id="usage-heading">Deterministic assessment input</h2>
        <p>{detail.assessment_usage.statement}</p>
        <p className="status-message">
          Reading this catalog projection does not create an assessment or change assessment
          behavior.
        </p>
        <details className="technical-disclosure">
          <summary>Technical object identity</summary>
          <dl className="catalog-technical-grid">
            <Fact label="Stable identity" value={object.object_id} technical />
            <Fact label="Organization identity" value={object.organization_id} technical />
            <Fact label="Status basis" value={object.status.basis} technical />
            <Fact label="Record provenance" value={object.record_provenance.classification} technical />
          </dl>
        </details>
      </section>
    </main>
  );
}

function ExternalDocumentIdentity({ detail }: { detail: CatalogObjectDetail }) {
  const source = detail.external_source;
  return (
    <section className="journey-card catalog-external-source" aria-labelledby="external-source-heading">
      <p className="eyebrow">Read-only external source</p>
      <h2 id="external-source-heading">Confluence document identity</h2>
      {source ? (
        <>
          <div className="section-heading">
            <p>
              This ChangeOps document corresponds to a validated page in an external enterprise
              knowledge system. ChangeOps preserves its own stable catalog identity.
            </p>
            <span className="badge deterministic">{humanize(source.external_status)}</span>
          </div>
          <dl className="catalog-fact-grid">
            <Fact label="Source provider" value={source.provider_label} />
            <Fact label="External page ID" value={source.external_page_id} technical />
            <Fact label="Space" value={`${source.space_key} · ${source.space_id}`} />
            <Fact label="Version" value={String(source.external_version)} />
            <Fact label="Status" value={humanize(source.external_status)} />
            <Fact label="Last refreshed" value={formatDateTime(source.refreshed_at)} />
          </dl>
          {!["success", "already_current"].includes(source.last_refresh_result) && (
            <div className="catalog-stale-notice" role="status">
              <strong>Last refresh failed; showing last-known-good metadata.</strong>
              <p>{source.last_refresh_message}</p>
            </div>
          )}
          <a href={source.canonical_url} target="_blank" rel="noreferrer">
            Open in Confluence
          </a>
          <details className="technical-disclosure">
            <summary>Technical source details</summary>
            <dl className="catalog-technical-grid">
              <Fact label="Imported title" value={source.external_title} />
              <Fact label="Source updated" value={formatDateTime(source.source_updated_at)} />
              <Fact label="First imported" value={formatDateTime(source.imported_at)} />
              <Fact label="Last refresh result" value={humanize(source.last_refresh_result)} />
              <Fact label="Source fingerprint" value={source.source_fingerprint} technical />
            </dl>
          </details>
        </>
      ) : (
        <div className="catalog-unavailable-source" role="status">
          <strong>Confluence metadata has not been imported.</strong>
          <p>
            The ChangeOps catalog record remains available. Configure the selected page and run
            the explicit refresh API to validate and import its read-only external identity.
          </p>
        </div>
      )}
    </section>
  );
}

export function PolicyRuleReferenceView({ reference }: { reference: PolicyRuleReference }) {
  return (
    <main className="analysis-shell catalog-shell">
      <Link href="/catalog" className="back-link">
        ← Back to enterprise knowledge
      </Link>
      <header className="catalog-detail-hero">
        <div>
          <p className="product-mark">ChangeOps</p>
          <p className="eyebrow">Policy-scoped rule reference</p>
          <h1>{reference.rule_code}</h1>
          <p className="lede">
            This reference belongs to {reference.policy.title}, version {reference.policy.version}.
            It is resolved from persisted dependency rows, not from a standalone rule table.
          </p>
        </div>
        <span className="badge deterministic">Deterministic use</span>
      </header>

      <section className="journey-card" aria-labelledby="mapping-heading">
        <p className="eyebrow">Normalized presentation mapping</p>
        <h2 id="mapping-heading">Current structured-rule connection</h2>
        {reference.structured_rule_reference.mapping_status === "supported" ? (
          <p>
            ChangeOps presents this code as <strong>{reference.structured_rule_reference.label}</strong>
            {" "}at structured field <code>{reference.structured_rule_reference.field_path}</code>.
          </p>
        ) : (
          <p>
            This persisted code has no known structured-rule presentation mapping. ChangeOps keeps
            the code visible and does not guess.
          </p>
        )}
        <p className="catalog-boundary-note">
          This mapping is explanatory adapter logic. The authoritative relationship facts remain
          the typed dependency rows listed below.
        </p>
      </section>

      <section className="catalog-category" aria-labelledby="connected-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Persisted dependency rows</p>
            <h2 id="connected-heading">Connected enterprise knowledge</h2>
          </div>
          <span className="quiet-label">{reference.relationships.length} rows</span>
        </div>
        <div className="catalog-object-grid">
          {reference.relationships.map((relationship) => (
            <article className="journey-card catalog-object-card" key={relationship.relationship_id}>
              <span className="badge deterministic">{OBJECT_LABELS[relationship.target_type]}</span>
              <h3>{relationship.target_name}</h3>
              <p>{humanize(relationship.relationship_type)}</p>
              <Link href={relationship.target_href}>Open catalog object</Link>
              <details className="technical-disclosure">
                <summary>Technical row identity</summary>
                <p className="technical-value">{relationship.relationship_id}</p>
              </details>
            </article>
          ))}
        </div>
      </section>

      <details className="technical-disclosure catalog-rule-technical">
        <summary>Policy-rule authority boundary</summary>
        <dl className="catalog-technical-grid">
          <Fact label="Stable policy-scoped key" value={reference.stable_key} technical />
          <Fact label="Standalone persisted rule" value="No" />
          <Fact label="Relationship source" value={reference.authority_boundary.relationship_source} technical />
          <Fact label="Assessment use" value={reference.authority_boundary.assessment_use} technical />
        </dl>
      </details>
    </main>
  );
}

export function CatalogUnavailable({ message }: { message: string }) {
  return (
    <main className="analysis-shell catalog-shell">
      <Link href="/" className="back-link">
        ← Return to policy analysis
      </Link>
      <section className="journey-card failure-panel">
        <p className="eyebrow">Enterprise knowledge unavailable</p>
        <h1>Unable to load the catalog</h1>
        <p className="error" role="alert">{message}</p>
      </section>
    </main>
  );
}

function detailMetadata(object: CatalogObjectSummary) {
  if (object.object_type === "enterprise_document") {
    return (
      <>
        <Fact label="Document type" value={humanize(object.metadata.document_type)} />
        <Fact label="Version" value={object.metadata.version} />
      </>
    );
  }
  if (object.object_type === "enterprise_system") {
    return <Fact label="System type" value={humanize(object.metadata.system_type)} />;
  }
  return (
    <>
      <Fact label="Course code" value={object.metadata.course_code} />
      <Fact label="Completion records" value={String(object.metadata.completion_record_count)} />
    </>
  );
}

function summaryMetadata(object: CatalogObjectSummary): string {
  if (object.object_type === "enterprise_document") {
    return `${humanize(object.metadata.document_type)} · version ${object.metadata.version}`;
  }
  if (object.object_type === "enterprise_system") return humanize(object.metadata.system_type);
  return `Course ${object.metadata.course_code}`;
}

function Fact({
  label,
  value,
  technical = false,
}: {
  label: string;
  value: string;
  technical?: boolean;
}) {
  return (
    <div>
      <dt>{label}</dt>
      <dd className={technical ? "technical-value" : undefined}>{value}</dd>
    </div>
  );
}

function Count({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function splitRuleKey(stableKey: string): [string, string] {
  const separator = stableKey.indexOf(":");
  return [stableKey.slice(0, separator), stableKey.slice(separator + 1)];
}

function humanize(value: string): string {
  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}
