"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { parseApiError } from "@/lib/api";
import type { PolicyAnalysisEntry } from "@/lib/types";

const ANALYSIS_REQUEST_TIMEOUT_MS = 270_000;

type PersistedRunNavigation = {
  id: string;
  href: string;
};

function navigateBrowserToRun(href: string) {
  window.location.assign(href);
}

export function PolicyAnalysisEntryView({
  entry,
  navigateToRun = navigateBrowserToRun,
}: {
  entry: PolicyAnalysisEntry;
  navigateToRun?: (href: string) => void;
}) {
  const router = useRouter();
  const submissionInFlight = useRef(false);
  const initialRunIds = useRef(new Set(entry.recent_runs.map((run) => run.id)));
  const [selectedPolicyId, setSelectedPolicyId] = useState(entry.policies[0]?.id ?? "");
  const [starting, setStarting] = useState(false);
  const [checkingPersistedRun, setCheckingPersistedRun] = useState(false);
  const [uncertainPolicyId, setUncertainPolicyId] = useState("");
  const [persistedRun, setPersistedRun] = useState<PersistedRunNavigation | null>(null);
  const [baselinePolicyId, setBaselinePolicyId] = useState(entry.policies.at(-1)?.id ?? "");
  const [proposedPolicyId, setProposedPolicyId] = useState(entry.policies[0]?.id ?? "");
  const [comparisonActor, setComparisonActor] = useState("portfolio-reviewer");
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState("");
  const [comparisonError, setComparisonError] = useState("");
  const policy = entry.policies.find((item) => item.id === selectedPolicyId);
  const baselinePolicy = entry.policies.find((item) => item.id === baselinePolicyId);
  const proposedPolicy = entry.policies.find((item) => item.id === proposedPolicyId);
  const comparisonReady =
    baselinePolicyId !== proposedPolicyId &&
    baselinePolicy?.comparison_readiness.ready === true &&
    proposedPolicy?.comparison_readiness.ready === true &&
    comparisonActor.trim().length > 0;

  async function startAnalysis() {
    if (submissionInFlight.current || !selectedPolicyId) return;
    submissionInFlight.current = true;
    const requestedPolicyId = selectedPolicyId;
    setStarting(true);
    setError("");
    setUncertainPolicyId("");
    setPersistedRun(null);
    const controller = new AbortController();
    const timeoutId = window.setTimeout(
      () => controller.abort("analysis_request_timeout"),
      ANALYSIS_REQUEST_TIMEOUT_MS,
    );
    try {
      const response = await fetch("/api/v1/policy-analysis-runs", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ policy_change_id: requestedPolicyId }),
        signal: controller.signal,
      });
      if (!response.ok) {
        if (response.status >= 500) {
          await reconcilePersistedRun(requestedPolicyId);
          return;
        }
        const apiError = await parseApiError(response);
        setError(apiError.message);
        return;
      }
      const run = (await response.json()) as { id: string };
      openPersistedRun(run.id);
    } catch {
      await reconcilePersistedRun(requestedPolicyId);
    } finally {
      window.clearTimeout(timeoutId);
      submissionInFlight.current = false;
      setStarting(false);
    }
  }

  function openPersistedRun(runId: string) {
    const navigation = {
      id: runId,
      href: `/policy-analyses/${runId}`,
    };
    setPersistedRun(navigation);
    setUncertainPolicyId("");
    setError("");
    try {
      navigateToRun(navigation.href);
    } catch {
      setError(
        "The analysis was persisted, but automatic navigation failed. Open the authoritative run below.",
      );
    }
  }

  async function reconcilePersistedRun(policyId = uncertainPolicyId) {
    if (!policyId || checkingPersistedRun) return;
    setCheckingPersistedRun(true);
    setUncertainPolicyId(policyId);
    setError("");
    try {
      const response = await fetch("/api/v1/policy-analysis-entry", {
        method: "GET",
        cache: "no-store",
      });
      if (!response.ok) {
        throw new Error("authoritative_entry_unavailable");
      }
      const authoritativeEntry = (await response.json()) as PolicyAnalysisEntry;
      const run = authoritativeEntry.recent_runs.find(
        (item) => item.policy_change_id === policyId && !initialRunIds.current.has(item.id),
      );
      if (run) {
        openPersistedRun(run.id);
        return;
      }
      setError(
        "The request outcome is not confirmed yet. Recovery did not send another analysis request. Check again for the persisted run.",
      );
    } catch {
      setError(
        "The request outcome could not be confirmed. Recovery did not send another analysis request. Check the API, then check again for the persisted run.",
      );
    } finally {
      setCheckingPersistedRun(false);
    }
  }

  async function comparePolicies() {
    setComparing(true);
    setComparisonError("");
    try {
      const response = await fetch("/api/v1/policy-comparisons", {
        method: "POST",
        headers: {
          "content-type": "application/json",
          "X-ChangeOps-Actor": comparisonActor.trim(),
        },
        body: JSON.stringify({
          baseline_policy_change_id: baselinePolicyId,
          proposed_policy_change_id: proposedPolicyId,
        }),
      });
      if (!response.ok) {
        const apiError = await parseApiError(response);
        setComparisonError(apiError.message);
        return;
      }
      const comparison = (await response.json()) as { id: string };
      router.push(`/policy-comparisons/${comparison.id}`);
    } catch {
      setComparisonError(
        "The ChangeOps API is unavailable. Check that the local stack is running.",
      );
    } finally {
      setComparing(false);
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
              disabled={starting}
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
              disabled={starting || !selectedPolicyId || persistedRun !== null}
            >
              {starting ? "Analyzing policy…" : "Start new analysis"}
            </button>
            <p className="honest-pending">
              Analysis runs synchronously. This button waits for the authoritative workflow
              response; it does not simulate progress.
            </p>
            <div aria-live="polite">
              {persistedRun && (
                <p className="analysis-navigation-status">
                  Analysis persisted. Opening the authoritative run.{" "}
                  <a href={persistedRun.href}>Open completed analysis</a>
                  <button type="button" onClick={() => openPersistedRun(persistedRun.id)}>
                    Retry opening analysis
                  </button>
                </p>
              )}
              {uncertainPolicyId && !persistedRun && (
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => reconcilePersistedRun()}
                  disabled={checkingPersistedRun}
                >
                  {checkingPersistedRun
                    ? "Checking authoritative state…"
                    : "Check for persisted analysis"}
                </button>
              )}
            </div>
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
                        {humanize(run.current_step)} ·{" "}
                        <time dateTime={run.updated_at}>{formatDateTime(run.updated_at)}</time>
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

      {entry.policies.length > 0 && (
        <section className="journey-card comparison-entry" aria-labelledby="comparison-heading">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Deterministic policy comparison</p>
              <h2 id="comparison-heading">Compare policy versions</h2>
            </div>
            <span className="badge deterministic">No AI comparison</span>
          </div>
          <p>
            Comparison becomes available after both policies have accepted, validated rules and
            completed assessments.
          </p>
          <div className="comparison-selectors">
            <label>
              Baseline policy
              <select
                value={baselinePolicyId}
                onChange={(event) => setBaselinePolicyId(event.target.value)}
              >
                {entry.policies.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.title}
                  </option>
                ))}
              </select>
              {baselinePolicy && <Readiness policy={baselinePolicy} />}
            </label>
            <label>
              Proposed revision
              <select
                value={proposedPolicyId}
                onChange={(event) => setProposedPolicyId(event.target.value)}
              >
                {entry.policies.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.title}
                  </option>
                ))}
              </select>
              {proposedPolicy && <Readiness policy={proposedPolicy} />}
            </label>
            <label>
              Comparison initiated by
              <input
                value={comparisonActor}
                onChange={(event) => setComparisonActor(event.target.value)}
              />
            </label>
          </div>
          <button type="button" onClick={comparePolicies} disabled={!comparisonReady || comparing}>
            {comparing ? "Comparing policy versions…" : "Compare policy versions"}
          </button>
          {baselinePolicyId === proposedPolicyId && (
            <p className="error">Choose two distinct policy source records.</p>
          )}
          {comparisonError && (
            <p className="error" role="alert">
              {comparisonError}
            </p>
          )}
          <p className="honest-pending">
            Deterministic code compares accepted policy semantics and the two persisted assessment
            outcomes. AI does not calculate the comparison.
          </p>
          <div className="comparison-history">
            <h3>Recent comparisons</h3>
            {entry.recent_comparisons.length === 0 ? (
              <p>No policy comparison has been created yet.</p>
            ) : (
              <ol className="run-list">
                {entry.recent_comparisons.map((comparison) => (
                  <li key={comparison.id}>
                    <span>{comparison.difference_count} semantic differences</span>
                    <Link href={`/policy-comparisons/${comparison.id}`}>Open comparison</Link>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </section>
      )}
    </main>
  );
}

function Readiness({ policy }: { policy: PolicyAnalysisEntry["policies"][number] }) {
  return (
    <small className={policy.comparison_readiness.ready ? "ready" : "not-ready"}>
      {policy.comparison_readiness.ready
        ? "Ready · accepted extraction validated"
        : `Not ready · ${readinessLabel(policy.comparison_readiness.status)}`}
    </small>
  );
}

function readinessLabel(status: string) {
  if (status === "policy_not_ready") {
    return "analysis incomplete or clarification pending";
  }
  return humanize(status);
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
    timeZone: "UTC",
  }).format(new Date(value));
}
