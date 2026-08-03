"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { parseApiError } from "@/lib/api";
import type { AnalysisClarification, PolicyAnalysisJourney } from "@/lib/types";
import { ApprovalHandoff } from "./policy-analysis/approval-handoff";
import { AssessmentSections } from "./policy-analysis/assessment-sections";
import { ClarificationSection } from "./policy-analysis/clarification-section";
import { ExtractionSection } from "./policy-analysis/extraction-section";
import { formatDate, humanize } from "./policy-analysis/formatters";
import { InterpretationSection } from "./policy-analysis/interpretation-section";
import { JourneyNavigation } from "./policy-analysis/journey-navigation";
import { PolicySection } from "./policy-analysis/policy-section";

type Mutation = "clarification" | "interpretation" | "approval";

export function PolicyAnalysisJourneyView({
  initialJourney,
}: {
  initialJourney: PolicyAnalysisJourney;
}) {
  const router = useRouter();
  const [actor, setActor] = useState("reviewer@example.com");
  const [busy, setBusy] = useState<Mutation | null>(null);
  const [message, setMessage] = useState("");
  const { policy, run, extraction, assessment } = initialJourney;

  async function answerClarification(clarification: AnalysisClarification) {
    await mutate(
      "clarification",
      `/api/v1/policy-analysis-runs/${run.id}/clarifications/${clarification.id}/answer`,
      {
        body: JSON.stringify({ value: true, responder_identity: actor }),
        success: "Clarification recorded. The same durable analysis run resumed.",
      },
    );
  }

  async function createInterpretation() {
    if (!assessment) return;
    await mutate("interpretation", `/api/v1/impact-assessments/${assessment.id}/change-plans`, {
      success: "Grounded interpretation persisted. Reloaded the authoritative change plan.",
      unavailable:
        "The interpretation response was unavailable. Reload to reconcile persisted state.",
    });
  }

  async function openApproval() {
    if (!assessment) return;
    setBusy("approval");
    setMessage("");
    try {
      const response = await fetch(`/api/v1/impact-assessments/${assessment.id}/approval-run`, {
        method: "POST",
      });
      if (!response.ok) {
        const error = await parseApiError(response);
        setMessage(error.message);
        return;
      }
      const approval = (await response.json()) as { id: string };
      router.push(`/approvals/${approval.id}`);
    } catch {
      setMessage("The ChangeOps API is unavailable. Check that the local stack is running.");
    } finally {
      setBusy(null);
    }
  }

  async function mutate(
    mutation: Exclude<Mutation, "approval">,
    url: string,
    options: { body?: string; success: string; unavailable?: string },
  ) {
    setBusy(mutation);
    setMessage("");
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: options.body ? { "content-type": "application/json" } : undefined,
        body: options.body,
      });
      if (!response.ok) {
        const error = await parseApiError(response);
        setMessage(error.message);
        return;
      }
      setMessage(options.success);
      router.refresh();
    } catch {
      setMessage(
        options.unavailable ??
          "The ChangeOps API is unavailable. Check that the local stack is running.",
      );
    } finally {
      setBusy(null);
    }
  }

  return (
    <main className="analysis-shell">
      <header className="analysis-hero">
        <div>
          <Link href="/" className="back-link">
            ← Policy analyses
          </Link>
          <p className="eyebrow">Policy analysis journey</p>
          <h1>{policy.title}</h1>
          <p className="lede">
            {policy.organization_name} · Effective {formatDate(policy.effective_date)}
          </p>
        </div>
        <dl className="identifiers">
          <div>
            <dt>Analysis run</dt>
            <dd>{run.id}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>
              <span className={`badge status-${run.status}`}>{humanize(run.status)}</span>
            </dd>
          </div>
        </dl>
      </header>

      <JourneyNavigation journey={initialJourney} />

      {run.failure_code && (
        <section className="failure-panel" aria-labelledby="analysis-failure-heading">
          <h2 id="analysis-failure-heading">Analysis did not complete</h2>
          <p>
            <code>{run.failure_code}</code> — The persisted workflow stopped safely at{" "}
            {humanize(run.current_step)}.
          </p>
        </section>
      )}
      {message && (
        <p className={message.includes("unavailable") ? "error" : "status-message"} role="status">
          {message}
        </p>
      )}

      <PolicySection policy={policy} />
      <ExtractionSection extraction={extraction} />
      <ClarificationSection
        journey={initialJourney}
        actor={actor}
        busy={busy === "clarification"}
        onActorChange={setActor}
        onAnswer={answerClarification}
      />
      <AssessmentSections
        assessment={assessment}
        coverage={initialJourney.enterprise_coverage}
      />
      <InterpretationSection
        journey={initialJourney}
        busy={busy === "interpretation"}
        onCreate={createInterpretation}
      />
      <ApprovalHandoff
        journey={initialJourney}
        busy={busy === "approval"}
        onOpen={openApproval}
      />
    </main>
  );
}
