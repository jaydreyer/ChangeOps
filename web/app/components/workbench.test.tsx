import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ExecutionPreparation, Workbench } from "@/lib/types";
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

function workbenchWithCompletedFirstItem(): Workbench {
  const pending = workbench();
  const completed = workbench("approved").items[0];
  const nextPending = {
    ...pending.items[0],
    sequence: 1,
    review: {
      ...pending.items[0].review,
      id: "review-2",
      original_action: {
        ...pending.items[0].review.original_action,
        proposed_action_id: "action-2",
        description: "Assign the next required training.",
      },
    },
  };
  return {
    ...pending,
    run: {
      ...pending.run,
      summary: {
        ...pending.run.summary,
        total: 2,
        pending: 1,
        approved: 1,
      },
    },
    items: [completed, nextPending],
  };
}

function preparation(
  prepared = false,
  executed = false,
  replay = false,
): ExecutionPreparation {
  const assignment = {
    id: "assignment-1",
    worker_id: "worker-1",
    training_course_id: "international-travel-security",
    source_execution_command_id: "command-1",
    source_approved_action_id: "action-1",
    assignment_status: "assigned" as const,
    assigned_at: "2026-08-02T12:05:00Z",
    created_at: "2026-08-02T12:05:00Z",
  };
  const executionResults = executed
    ? [
        {
          id: "result-1",
          execution_command_id: "command-1",
          status: "succeeded" as const,
          outcome_code: "training_assignment_created",
          message: "The simulated learning system assigned the training item.",
          command_idempotency_key: "abcdef0123456789abcdef0123456789",
          attempted_by: "operator@example.com",
          attempted_role: "admin" as const,
          created_at: "2026-08-02T12:05:00Z",
          learning_assignment: assignment,
        },
        ...(replay
          ? [
              {
                id: "result-2",
                execution_command_id: "command-1",
                status: "already_applied" as const,
                outcome_code: "training_assignment_already_applied",
                message:
                  "This command already created the simulated training assignment.",
                command_idempotency_key: "abcdef0123456789abcdef0123456789",
                attempted_by: "operator@example.com",
                attempted_role: "admin" as const,
                created_at: "2026-08-02T12:06:00Z",
                learning_assignment: assignment,
              },
            ]
          : []),
      ]
    : [];
  return {
    approval_run_id: "run-1",
    approved_action_count: 2,
    eligible_action_count: 1,
    prepared_command_count: prepared ? 1 : 0,
    unsupported_approved_action_count: 1,
    commands: prepared
      ? [
          {
            id: "command-1",
            approval_run_id: "run-1",
            action_review_id: "review-1",
            action_review_decision_id: "decision-1",
            proposed_action_id: "action-1",
            assessment_id: "assessment-1",
            sequence: 0,
            schema_version: "execution-command-v1",
            system: "learning",
            operation: "assign_training",
            target_type: "worker",
            target_identifier: "worker-1",
            parameters: { course_identifier: "international-travel-security" },
            effective_action: {
              ...originalAction,
              schema_version: "effective-approved-action-v1",
              target_type: "worker",
              target_identifier: "worker-1",
              description: "Assign revised training.",
            },
            idempotency_key: "abcdef0123456789abcdef0123456789",
            status: "pending_execution",
            prepared_by: "operator@example.com",
            prepared_role: "admin",
            created_at: "2026-08-02T12:00:00Z",
            execution_state: executed ? "executed" : "pending_execution",
            execution_results: executionResults,
            execution_performed: executed,
          },
        ]
      : [],
    unsupported_items: [
      {
        sequence: 1,
        action_review_id: "review-2",
        proposed_action_id: "action-2",
        action_type: "review_team_travel",
        target_type: "team",
        target_identifier: "team-1",
        reason_code: "unsupported_action_type",
        reason: "Action type 'review_team_travel' has no execution mapping.",
      },
    ],
    execution_performed: executed,
  };
}

describe("approval workbench", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    refresh.mockReset();
  });

  it("renders authoritative counts, provenance, guided review sections, and approval boundary", () => {
    render(<WorkbenchView initialWorkbench={workbench()} />);

    expect(screen.getByRole("heading", { name: "Review proposed actions" })).toBeInTheDocument();
    expect(
      screen.getByText(
        "You are reviewing 1 proposed action. Approval records a decision; it does not execute the action.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Pending", { selector: "dt" }).nextElementSibling).toHaveTextContent("1");
    expect(screen.getByText("AI proposal")).toBeInTheDocument();
    expect(screen.getAllByText("Deterministic conclusion").length).toBeGreaterThan(0);
    expect(screen.getByText("Policy source")).toBeInTheDocument();
    expect(screen.getAllByText("Human decision").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "What is being proposed?" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Why is it being proposed?" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "What evidence supports it?" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Record your decision" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Record terminal decision" })).toBeInTheDocument();
    expect(screen.getByText("View persisted evidence").closest("details")).not.toHaveAttribute(
      "open",
    );
  });

  it("keeps the first pending item open and preserves guided section order", () => {
    const { container } = render(
      <WorkbenchView initialWorkbench={workbenchWithCompletedFirstItem()} />,
    );

    const cards = container.querySelectorAll("details.review-card");
    expect(cards).toHaveLength(2);
    expect(cards[0]).not.toHaveAttribute("open");
    expect(cards[1]).toHaveAttribute("open");

    const currentCard = within(cards[1] as HTMLElement);
    const proposed = currentCard.getByRole("heading", { name: "What is being proposed?" });
    const why = currentCard.getByRole("heading", { name: "Why is it being proposed?" });
    const evidence = currentCard.getByRole("heading", { name: "What evidence supports it?" });
    const decision = currentCard.getByRole("heading", { name: "Record your decision" });
    expect(proposed.compareDocumentPosition(why) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(why.compareDocumentPosition(evidence) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(
      evidence.compareDocumentPosition(decision) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
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

    const summary = screen.getByText("Recorded decision").closest("section");
    expect(summary).not.toBeNull();
    expect(within(summary!).getByText("Training is required.")).toBeInTheDocument();
    expect(within(summary!).getByText("Assign revised training.")).toBeInTheDocument();
    expect(screen.getByText("Review is complete. Approval alone did not execute any action.")).toBeInTheDocument();
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

  it("shows execution preparation only after approval completes", () => {
    const { rerender } = render(
      <WorkbenchView
        initialWorkbench={workbench()}
        initialPreparation={preparation()}
      />,
    );
    expect(screen.queryByText("Execution Preparation")).not.toBeInTheDocument();

    rerender(
      <WorkbenchView
        initialWorkbench={workbench("approved")}
        initialPreparation={preparation()}
      />,
    );
    expect(screen.getByText("Carry out approved actions")).toBeInTheDocument();
    expect(screen.getByText("Preparable").nextElementSibling).toHaveTextContent("1");
    expect(screen.getByText("Approved actions requiring manual follow-up")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Automated execution is not available for these action types. Their approved records remain visible for follow-up outside ChangeOps.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Review team travel")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Execute/ })).not.toBeInTheDocument();
  });

  it("places execution after completed approval reviews and shows authoritative stage fields", () => {
    render(
      <WorkbenchView
        initialWorkbench={workbench("approved")}
        initialPreparation={preparation()}
      />,
    );

    const reviews = screen.getByRole("heading", { name: "Review each proposed action" });
    const execution = screen.getByRole("heading", { name: "Carry out approved actions" });
    expect(
      reviews.compareDocumentPosition(execution) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.getByText("Authorization").nextElementSibling).toHaveTextContent("Completed");
    expect(screen.getByText("Commands").nextElementSibling).toHaveTextContent("Not prepared");
    expect(screen.getByText("Execution request").nextElementSibling).toHaveTextContent(
      "Not requested",
    );
  });

  it("prepares commands and refreshes authoritative state", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(preparation(true)), { status: 201 }),
    );
    render(
      <WorkbenchView
        initialWorkbench={workbench("approved")}
        initialPreparation={preparation()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Prepare execution commands" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      method: "POST",
      headers: {
        "X-ChangeOps-Actor": "reviewer@example.com",
        "X-ChangeOps-Role": "admin",
      },
    });
    expect(refresh).toHaveBeenCalled();
  });

  it("shows prepared command details and an explicit supported execution control", () => {
    render(
      <WorkbenchView
        initialWorkbench={workbench("approved")}
        initialPreparation={preparation(true)}
      />,
    );

    expect(
      screen.getByText("Authorized operations awaiting an explicit request"),
    ).toBeInTheDocument();
    expect(screen.getByText("Assign revised training.", { selector: ".command-card strong" })).toBeInTheDocument();
    expect(screen.getByText("abcdef0123456789abcdef0123456789").closest("details")).not.toHaveAttribute(
      "open",
    );
    expect(screen.getByText("Pending execution", { selector: "span" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Execute training assignment" }),
    ).toBeInTheDocument();
    expect(screen.getByText("international-travel-security")).toBeInTheDocument();
    expect(screen.getByText("View command contract and lineage").closest("details")).not.toHaveAttribute(
      "open",
    );
    const unsupported = screen
      .getByText("Approved actions requiring manual follow-up")
      .closest(".unsupported-list");
    expect(unsupported).not.toBeNull();
    expect(
      within(unsupported as HTMLElement).getByText(
        "Manual follow-up required. No automated execution is available.",
      ),
    ).toBeInTheDocument();
    const limitation = within(unsupported as HTMLElement)
      .getByText("View execution limitation details")
      .closest("details");
    expect(limitation).not.toHaveAttribute("open");
    expect(within(limitation as HTMLElement).getByText("Unsupported action type")).toBeInTheDocument();
    expect(
      within(limitation as HTMLElement).getByText(
        "Action type 'review_team_travel' has no execution mapping.",
      ),
    ).toBeInTheDocument();
    expect(within(unsupported as HTMLElement).queryByRole("button")).not.toBeInTheDocument();
  });

  it("executes a supported command and reloads authoritative result state", async () => {
    const user = userEvent.setup();
    const execution = preparation(true, true).commands[0].execution_results[0];
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(execution), { status: 201 }),
    );
    render(
      <WorkbenchView
        initialWorkbench={workbench("approved")}
        initialPreparation={preparation(true)}
      />,
    );

    await user.click(
      screen.getByRole("button", { name: "Execute training assignment" }),
    );

    await waitFor(() => expect(fetchMock).toHaveBeenCalledOnce());
    expect(fetchMock.mock.calls[0]).toEqual([
      "/api/v1/execution-commands/command-1/execute",
      {
        method: "POST",
        headers: {
          "X-ChangeOps-Actor": "reviewer@example.com",
          "X-ChangeOps-Role": "admin",
        },
      },
    ]);
    expect(await screen.findByText(/Execution succeeded/)).toBeInTheDocument();
    expect(refresh).toHaveBeenCalled();
  });

  it("displays the durable assignment and makes replay safety explicit", () => {
    render(
      <WorkbenchView
        initialWorkbench={workbench("approved")}
        initialPreparation={preparation(true, true, true)}
      />,
    );

    expect(screen.getByText("Execution attempted", { selector: "span" })).toBeInTheDocument();
    expect(screen.getByText("Executed", { selector: "span" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Execute again safely" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Succeeded")).toBeInTheDocument();
    expect(screen.getByText("Already applied")).toBeInTheDocument();
    expect(screen.getAllByText(/assignment-1/)).toHaveLength(2);
    expect(
      screen.getByText(/already created the simulated training assignment/),
    ).toBeInTheDocument();
    for (const disclosure of screen.getAllByText("View result audit details")) {
      expect(disclosure.closest("details")).not.toHaveAttribute("open");
    }
  });

  it("renders an authoritative failed execution state without changing the execution control", () => {
    const failed = preparation(true);
    failed.execution_performed = true;
    failed.commands[0] = {
      ...failed.commands[0],
      execution_state: "execution_failed",
      execution_performed: true,
      execution_results: [
        {
          id: "result-failed",
          execution_command_id: "command-1",
          status: "failed_validation",
          outcome_code: "invalid_execution_command_payload",
          message: "The assign-training command payload is malformed.",
          command_idempotency_key: "abcdef0123456789abcdef0123456789",
          attempted_by: "operator@example.com",
          attempted_role: "admin",
          created_at: "2026-08-02T12:05:00Z",
          learning_assignment: null,
        },
      ],
    };

    render(
      <WorkbenchView
        initialWorkbench={workbench("approved")}
        initialPreparation={failed}
      />,
    );

    expect(screen.getByText("Execution failed", { selector: ".badge" })).toBeInTheDocument();
    expect(screen.getByText("Failed validation")).toBeInTheDocument();
    expect(screen.getByText("The assign-training command payload is malformed.")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Execute training assignment" }),
    ).toBeInTheDocument();
  });

  it("reconciles an ambiguous preparation response by refreshing", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("connection closed"));
    render(
      <WorkbenchView
        initialWorkbench={workbench("approved")}
        initialPreparation={preparation()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Prepare execution commands" }));

    expect(
      await screen.findByText(/Preparation response was ambiguous/),
    ).toBeInTheDocument();
    expect(refresh).toHaveBeenCalled();
  });
});
