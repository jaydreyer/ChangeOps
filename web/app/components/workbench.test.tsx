import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Workbench } from "@/lib/types";
import { WorkbenchView } from "./workbench";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh, push: vi.fn() }),
}));

const originalAction = {
  proposed_action_id: "action-1",
  assessment_id: "assessment-1",
  finding_id: "finding-1",
  enterprise_impact_id: null,
  worker_id: "worker-1",
  action_type: "training_assignment",
  target_type: "training_course",
  target_identifier: "course-1",
  description: "Assign required training.",
  due_date: "2026-08-15",
  execution_status: "not_executed" as const,
};

function workbench(status: "pending" | "approved" = "pending"): Workbench {
  const terminal = status === "approved";
  return {
    run: {
      id: "run-1",
      assessment_id: "assessment-1",
      policy_analysis_run_id: "analysis-1",
      status: terminal ? "completed" : "awaiting_decisions",
      current_step: terminal ? "finalize" : "await_decisions",
      summary: {
        total: 1,
        pending: terminal ? 0 : 1,
        approved: terminal ? 1 : 0,
        rejected: 0,
        deferred: 0,
        revision_requested: 0,
      },
      failure_code: null,
      failure_message: null,
      transitions: [],
    },
    assessment: {
      id: "assessment-1",
      policy_change_id: "policy-1",
      completed_at: "2026-08-01T12:00:00Z",
      affected_worker_count: 1,
      enterprise_impact_count: 1,
      proposed_action_count: 1,
    },
    items: [
      {
        sequence: 0,
        review: {
          id: "review-1",
          status,
          original_action: originalAction,
          review_context: {
            finding_id: "finding-1",
            enterprise_impact_id: null,
            reason_code: "TRAINING_REQUIRED",
            evidence_keys: ["policy:training"],
          },
          current_decision: terminal
            ? {
                id: "decision-1",
                decision: "approved",
                reviewer_identity: "reviewer@example.com",
                reviewer_role: "reviewer",
                rationale: "Training is required.",
                edited_action: { description: "Assign revised training." },
                created_at: "2026-08-01T13:00:00Z",
              }
            : null,
          effective_approved_action: terminal
            ? { ...originalAction, description: "Assign revised training." }
            : null,
          completed_at: terminal ? "2026-08-01T13:00:00Z" : null,
        },
        evidence: [
          {
            key: "policy:training",
            source_type: "policy_quote",
            label: "Policy security-training rule",
            detail: "course identifier: course-1",
            policy_quote: "Workers must complete security training.",
            reason_code: "TRAINING_REQUIRED",
            relationship_path: [],
          },
        ],
        finding: {
          id: "finding-1",
          finding_type: "training_required",
          severity: "action_required",
          rule_code: "TRAINING_REQUIRED",
          worker_id: "worker-1",
          explanation: "The worker has not completed required training.",
        },
        enterprise_impact: null,
      },
    ],
  };
}

describe("approval workbench", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    refresh.mockReset();
  });

  it("renders authoritative counts, provenance, a pending form, and execution notice", () => {
    render(<WorkbenchView initialWorkbench={workbench()} />);

    expect(screen.getByText("Human Approval Workbench")).toBeInTheDocument();
    expect(screen.getByText("Pending", { selector: "dt" }).nextElementSibling).toHaveTextContent("1");
    expect(screen.getByText("AI proposal")).toBeInTheDocument();
    expect(screen.getAllByText("Deterministic conclusion").length).toBeGreaterThan(0);
    expect(screen.getByText("Policy source")).toBeInTheDocument();
    expect(screen.getByText("Human decision")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Record terminal decision" })).toBeInTheDocument();
    expect(
      screen.getByText("Approval records a human decision. It does not execute the action."),
    ).toBeInTheDocument();
  });

  it("requires rationale before submitting", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch");
    render(<WorkbenchView initialWorkbench={workbench()} />);

    await user.type(screen.getByLabelText(/Rationale/), "   ");
    await user.click(screen.getByRole("button", { name: "Record terminal decision" }));

    expect(screen.getByText("Rationale is required for every human decision.")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("submits approval with only permitted edited fields", async () => {
    const user = userEvent.setup();
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify({ status: "approved" }), { status: 201 }));
    render(<WorkbenchView initialWorkbench={workbench()} />);

    await user.clear(screen.getByLabelText("Approved description"));
    await user.type(screen.getByLabelText("Approved description"), "Assign revised training.");
    await user.type(screen.getByLabelText(/Rationale/), "The revised wording is clearer.");
    await user.click(screen.getByRole("button", { name: "Record terminal decision" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    const request = fetchMock.mock.calls[0][1] as RequestInit;
    expect(JSON.parse(request.body as string)).toEqual({
      decision: "approved",
      rationale: "The revised wording is clearer.",
      edited_action: { description: "Assign revised training." },
    });
    expect(refresh).toHaveBeenCalled();
  });

  it("hides edit fields and submits no edits for rejection", async () => {
    const user = userEvent.setup();
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify({ status: "rejected" }), { status: 201 }));
    render(<WorkbenchView initialWorkbench={workbench()} />);

    await user.click(screen.getByLabelText("Rejected"));
    expect(screen.queryByLabelText("Approved description")).not.toBeInTheDocument();
    await user.type(screen.getByLabelText(/Rationale/), "This action is not required.");
    await user.click(screen.getByRole("button", { name: "Record terminal decision" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    const request = fetchMock.mock.calls[0][1] as RequestInit;
    expect(JSON.parse(request.body as string)).toEqual({
      decision: "rejected",
      rationale: "This action is not required.",
    });
  });

  it("renders a terminal decision, edited comparison, and unexecuted completion state", () => {
    render(<WorkbenchView initialWorkbench={workbench("approved")} />);

    const summary = screen.getByText("Persisted human decision").closest("section");
    expect(summary).not.toBeNull();
    expect(within(summary!).getByText("Training is required.")).toBeInTheDocument();
    expect(within(summary!).getByText("Assign revised training.")).toBeInTheDocument();
    expect(screen.getByText("Review is complete. Approved actions remain unexecuted.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Record terminal decision" })).not.toBeInTheDocument();
  });

  it("reloads and explains an already-decided conflict", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: {
            code: "action_review_already_decided",
            message: "This action review already has a terminal decision.",
          },
        }),
        { status: 409, headers: { "content-type": "application/json" } },
      ),
    );
    render(<WorkbenchView initialWorkbench={workbench()} />);
    await user.type(screen.getByLabelText(/Rationale/), "My decision.");
    await user.click(screen.getByRole("button", { name: "Record terminal decision" }));

    expect(
      await screen.findByText(/Another committed decision already completed this review/),
    ).toBeInTheDocument();
    expect(refresh).toHaveBeenCalled();
  });
});
