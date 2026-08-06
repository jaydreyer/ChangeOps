import Link from "next/link";
import type { AuditTimeline as AuditTimelineType, AuditTimelineEntry } from "@/lib/types";
import { humanize } from "./policy-analysis/formatters";

const actorLabels = {
  ai_assisted: "AI-assisted",
  deterministic_system: "Deterministic system",
  human: "Human",
  external_system: "External system",
} as const;

export function AuditTimeline({
  timeline,
  errorMessage,
}: {
  timeline: AuditTimelineType | null;
  errorMessage?: string;
}) {
  return (
    <section className="journey-card audit-timeline" aria-labelledby="audit-timeline-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">One traceable journey</p>
          <h2 id="audit-timeline-heading">Audit timeline</h2>
          <p className="section-intro">
            This read-only view is derived from authoritative persisted records. Each entry names
            the durable artifact that proves it.
          </p>
        </div>
        <span className="badge deterministic">Read projection</span>
      </div>

      {errorMessage ? (
        <p className="error audit-timeline-message" role="alert">
          {errorMessage}
        </p>
      ) : timeline && timeline.entries.length > 0 ? (
        <ol className="audit-entry-list">
          {timeline.entries.map((entry) => (
            <AuditEntry key={entry.entry_key} entry={entry} />
          ))}
        </ol>
      ) : (
        <p className="audit-timeline-message">
          No authoritative lifecycle records are available for this journey yet.
        </p>
      )}
    </section>
  );
}

function AuditEntry({ entry }: { entry: AuditTimelineEntry }) {
  const metadata = Object.entries(entry.metadata);
  return (
    <li className={`audit-entry actor-${entry.actor_category}`}>
      <div className="audit-entry-marker" aria-hidden="true" />
      <article>
        <div className="audit-entry-heading">
          <div>
            <time dateTime={entry.occurred_at}>{formatTimestamp(entry.occurred_at)}</time>
            <h3>{entry.title}</h3>
          </div>
          <div className="audit-labels" aria-label="Actor and outcome">
            <span className={`badge audit-actor ${entry.actor_category}`}>
              {actorLabels[entry.actor_category]}
            </span>
            <span className={`badge audit-outcome outcome-${entry.outcome}`}>
              {humanize(entry.outcome)}
            </span>
          </div>
        </div>
        {entry.actor_identity && (
          <p className="audit-identity">
            Performed or requested by <strong>{entry.actor_identity}</strong>
          </p>
        )}
        <p>{entry.description}</p>
        <div className="audit-artifact">
          <span>Authoritative artifact</span>
          {entry.artifact.href ? (
            <ArtifactLink entry={entry} />
          ) : (
            <code>
              {humanize(entry.artifact.artifact_type)} · {entry.artifact.artifact_id}
            </code>
          )}
        </div>
        {metadata.length > 0 && (
          <details className="technical-disclosure audit-metadata">
            <summary>View supporting details</summary>
            <dl className="identifiers">
              {metadata.map(([key, value]) => (
                <div key={key}>
                  <dt>{humanize(key)}</dt>
                  <dd>{formatMetadata(value)}</dd>
                </div>
              ))}
            </dl>
          </details>
        )}
      </article>
    </li>
  );
}

function ArtifactLink({ entry }: { entry: AuditTimelineEntry }) {
  const label = `${humanize(entry.artifact.artifact_type)} · ${entry.artifact.artifact_id}`;
  if (entry.artifact.href?.startsWith("http")) {
    return (
      <a href={entry.artifact.href} target="_blank" rel="noreferrer">
        <code>{label}</code>
        <span className="visually-hidden"> (opens in a new tab)</span>
      </a>
    );
  }
  return (
    <Link href={entry.artifact.href ?? "#"}>
      <code>{label}</code>
    </Link>
  );
}

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  }).format(new Date(value));
}

function formatMetadata(value: unknown): string {
  if (Array.isArray(value)) return value.join(", ");
  if (value !== null && typeof value === "object") return JSON.stringify(value);
  return String(value);
}
