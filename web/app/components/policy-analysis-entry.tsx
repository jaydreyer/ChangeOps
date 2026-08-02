"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { parseApiError } from "@/lib/api";
import type { PolicyAnalysisEntry } from "@/lib/types";

export function PolicyAnalysisEntryView({ entry }: { entry: PolicyAnalysisEntry }) {
  const router = useRouter();
  const [selectedPolicyId, setSelectedPolicyId] = useState(entry.policies[0]?.id ?? "");
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");
  const policy = entry.policies.find((item) => item.id === selectedPolicyId);

  async function startAnalysis() {
    setStarting(true);
    setError("");
    try {
      const response = await fetch("/api/v1/policy-analysis-runs", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ policy_change_id: selectedPolicyId }),
      });
      if (!response.ok) {
        const apiError = await parseApiError(response);
        setError(apiError.message);
        return;
      }
      const run = (await response.json()) as { id: string };
      router.push(`/policy-analyses/${run.id}`);
    } catch {
      setError("The ChangeOps API is unavailable. Check that the local stack is running.");
    } finally {
      setStarting(false);
    }
  }

  return (
    <main className="analysis-shell">
      <header className="analysis-hero">
        <div>
          <p className="eyebrow">ChangeOps · governed policy intelligence</p>
          <h1>Trace a policy from language to controlled action</h1>
          <p className="lede">
            Inspect what AI proposed, what deterministic validation accepted, who and what was
            affected, and which actions still require human approval.
          </p>
        </div>
        <div className="boundary-legend" aria-label="Decision boundaries">
          <span className="badge ai_proposal">AI proposal</span>
          <span className="badge deterministic">Deterministic conclusion</span>
          <span className="badge human_input">Human input</span>
        </div>
      </header>

      {entry.policies.length === 0 ? (
        <section className="empty-panel">
          <h2>No policy is available</h2>
          <p>Load the seeded golden scenario before starting an analysis.</p>
        </section>
      ) : (
        <section className="policy-entry-grid">
          <article className="journey-card policy-card">
            <p className="eyebrow">Golden scenario</p>
            <label htmlFor="policy-selector">Policy to analyze</label>
            <select
              id="policy-selector"
              value={selectedPolicyId}
              onChange={(event) => setSelectedPolicyId(event.target.value)}
            >
              {entry.policies.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.title}
                </option>
              ))}
            </select>
            {policy && (
              <>
                <dl className="policy-meta">
                  <div>
                    <dt>Organization</dt>
                    <dd>{policy.organization_name}</dd>
                  </div>
                  <div>
                    <dt>Effective</dt>
                    <dd>{formatDate(policy.effective_date)}</dd>
                  </div>
                  <div>
                    <dt>Owner</dt>
                    <dd>{policy.owner}</dd>
                  </div>
                  <div>
                    <dt>Version</dt>
                    <dd>{policy.version}</dd>
                  </div>
                </dl>
                <blockquote className="policy-text">{policy.policy_text}</blockquote>
              </>
            )}
            <button
              type="button"
              onClick={startAnalysis}
              disabled={starting || !selectedPolicyId}
            >
              {starting ? "Analyzing policy…" : "Start new analysis"}
            </button>
            <p className="honest-pending">
              Analysis runs synchronously. This button waits for the authoritative workflow
              response; it does not simulate progress.
            </p>
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
          </article>

          <section className="journey-card" aria-labelledby="recent-runs-heading">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Durable workflow history</p>
                <h2 id="recent-runs-heading">Recent analyses</h2>
              </div>
              <span>{entry.recent_runs.length} runs</span>
            </div>
            {entry.recent_runs.length === 0 ? (
              <p>No analysis has been started yet.</p>
            ) : (
              <ol className="run-list">
                {entry.recent_runs.map((run) => (
                  <li key={run.id}>
                    <div>
                      <strong>{humanize(run.status)}</strong>
                      <small>
                        {humanize(run.current_step)} · {formatDateTime(run.updated_at)}
                      </small>
                    </div>
                    <Link href={`/policy-analyses/${run.id}`}>Open analysis</Link>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </section>
      )}
    </main>
  );
}

function humanize(value: string) {
  return value.replaceAll("_", " ").replace(/^\w/, (letter) => letter.toUpperCase());
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
