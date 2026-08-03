import Link from "next/link";
import type { PolicyAnalysisJourney } from "@/lib/types";
import { humanize } from "./formatters";

export function ApprovalHandoff({
  journey,
  busy,
  onOpen,
}: {
  journey: PolicyAnalysisJourney;
  busy: boolean;
  onOpen: () => void;
}) {
  const { assessment, run, approval_run: approvalRun, execution } = journey;
  return (
    <section className="journey-card approval-handoff" aria-labelledby="approval-heading">
      <div>
        <p className="eyebrow">Human governance</p>
        <h2 id="approval-heading">What needs approval?</h2>
        <p>
          Open the workbench to review each persisted proposal against its deterministic context
          and evidence. Approval records a decision; it does not execute the action.
        </p>
        {approvalRun && (
          <dl className="execution-summary">
            <div>
              <dt>Approval</dt>
              <dd>{humanize(approvalRun.status)}</dd>
            </div>
            <div>
              <dt>Execution</dt>
              <dd>{humanize(execution.status)}</dd>
            </div>
            <div>
              <dt>Commands</dt>
              <dd>{execution.command_count}</dd>
            </div>
            <div>
              <dt>Execution results</dt>
              <dd>{execution.result_count}</dd>
            </div>
          </dl>
        )}
      </div>
      {approvalRun ? (
        <Link className="button-link" href={`/approvals/${approvalRun.id}`}>
          Open approval workbench
        </Link>
      ) : (
        <button
          type="button"
          onClick={onOpen}
          disabled={!assessment || run.status !== "completed" || busy}
        >
          {busy ? "Creating…" : "Create approval run"}
        </button>
      )}
    </section>
  );
}
