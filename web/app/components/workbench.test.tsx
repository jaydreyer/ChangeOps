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
          jira_issue: null,
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
                jira_issue: null,
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
    expect(screen.getByText("Execution Preparation")).toBeInTheDocument();
    expect(screen.getByText("Preparable").nextElementSibling).toHaveTextContent("1");
    expect(screen.getByText("Unsupported approved actions")).toBeInTheDocument();
    expect(screen.getByText("Review team travel")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Execute/ })).not.toBeInTheDocument();
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

    expect(screen.getByText("Immutable prepared commands")).toBeInTheDocument();
    expect(screen.getByText("Learning · Assign training")).toBeInTheDocument();
    expect(screen.getByText("Assign revised training.", { selector: ".command-card p" })).toBeInTheDocument();
    expect(screen.getByText(/abcdef012345…/)).toBeInTheDocument();
    expect(screen.getByText("Pending execution", { selector: "span" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Execute training assignment" }),
    ).toBeInTheDocument();
    expect(screen.getByText("international-travel-security")).toBeInTheDocument();
    const unsupported = screen
      .getByText("Unsupported approved actions")
      .closest(".unsupported-list");
    expect(unsupported).not.toBeNull();
    expect(within(unsupported as HTMLElement).queryByRole("button")).not.toBeInTheDocument();
  });

  it("shows a prepared Jira task and its immutable external receipt", () => {
    const jiraPreparation = preparation(true, true);
    const command = jiraPreparation.commands[0];
    command.system = "jira";
    command.operation = "create_issue";
    command.target_type = "enterprise_document";
    command.target_identifier = "document-policy";
    command.parameters = {
      summary: "Operational remediation: International Business Travel Policy",
      comparison_id: "comparison-1",
    };
    command.execution_results[0].learning_assignment = null;
    command.execution_results[0].jira_issue = {
      id: "jira-receipt-1",
      issue_id: "10101",
      issue_key: "ECM-42",
      api_url: "https://acme.atlassian.net/rest/api/3/issue/10101",
      browse_url: "https://acme.atlassian.net/browse/ECM-42",
      project_id_or_key: "ECM",
      execution_command_id: "command-1",
      created_at: "2026-08-02T12:05:00Z",
    };

    render(
      <WorkbenchView
        initialWorkbench={workbench("approved")}
        initialPreparation={jiraPreparation}
      />,
    );

    expect(screen.getByText("Jira · Create issue")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Execute again safely" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "ECM-42" })).toHaveAttribute(
      "href",
      "https://acme.atlassian.net/browse/ECM-42",
    );
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
