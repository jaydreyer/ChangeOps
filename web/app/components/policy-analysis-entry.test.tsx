import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PolicyAnalysisEntryView } from "./policy-analysis-entry";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

const entry = {
  policies: [
    {
      id: "policy-travel",
      organization_id: "org-acme",
      organization_name: "Acme Global",
      title: "International Business Travel",
      owner: "People Operations",
      version: "2",
      effective_date: "2026-09-01",
      policy_text: "Travelers must complete training.",
      comparison_readiness: {
        ready: true,
        status: "ready",
        accepted_extraction_attempt_id: "attempt-1",
      },
    },
    {
      id: "policy-proposed",
      organization_id: "org-acme",
      organization_name: "Acme Global",
      title: "Proposed International Business Travel",
      owner: "People Operations",
      version: "proposed-draft",
      effective_date: "2026-10-01",
      policy_text: "Employees must complete training.",
      comparison_readiness: {
        ready: true,
        status: "ready",
        accepted_extraction_attempt_id: "attempt-2",
      },
    },
  ],
  recent_comparisons: [],
  recent_runs: [
    {
      id: "run-1",
      policy_change_id: "policy-travel",
      status: "completed",
      current_step: "terminal",
      assessment_id: "assessment-1",
      created_at: "2026-08-01T12:00:00Z",
      updated_at: "2026-08-01T12:01:00Z",
    },
  ],
};

describe("policy analysis entry", () => {
  beforeEach(() => {
    push.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the golden policy and opens a recent durable run", () => {
    render(<PolicyAnalysisEntryView entry={entry} />);

    expect(screen.getAllByText("International Business Travel")).not.toHaveLength(0);
    expect(screen.getByText("Travelers must complete training.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open analysis" })).toHaveAttribute(
      "href",
      "/policy-analyses/run-1",
    );
    expect(screen.getByText("Aug 1, 2026, 12:01 PM")).toBeInTheDocument();
    expect(screen.getByText("Aug 1, 2026, 12:01 PM").closest("time")).toHaveAttribute(
      "dateTime",
      "2026-08-01T12:01:00Z",
    );
  });

  it("starts a run, exits pending state, and opens the authoritative persisted run", async () => {
    const user = userEvent.setup();
    const navigateToRun = vi.fn();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "run-2" }), {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    );
    render(<PolicyAnalysisEntryView entry={entry} navigateToRun={navigateToRun} />);

    await user.click(screen.getByRole("button", { name: "Start new analysis" }));

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/policy-analysis-runs",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ policy_change_id: "policy-travel" }),
      }),
    );
    expect(navigateToRun).toHaveBeenCalledWith("/policy-analyses/run-2");
    expect(screen.queryByRole("button", { name: "Analyzing policy…" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open completed analysis" })).toHaveAttribute(
      "href",
      "/policy-analyses/run-2",
    );
  });

  it("retries persisted-run navigation without creating a duplicate analysis", async () => {
    const user = userEvent.setup();
    const navigateToRun = vi
      .fn()
      .mockImplementationOnce(() => {
        throw new Error("navigation failed");
      })
      .mockImplementationOnce(() => undefined);
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "run-2" }), {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    );
    render(<PolicyAnalysisEntryView entry={entry} navigateToRun={navigateToRun} />);

    await user.click(screen.getByRole("button", { name: "Start new analysis" }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "The analysis was persisted, but automatic navigation failed.",
    );

    await user.click(screen.getByRole("button", { name: "Retry opening analysis" }));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(navigateToRun).toHaveBeenCalledTimes(2);
    expect(navigateToRun).toHaveBeenLastCalledWith("/policy-analyses/run-2");
  });

  it("reconciles an uncertain response against authoritative persisted runs", async () => {
    const user = userEvent.setup();
    const navigateToRun = vi.fn();
    const authoritativeEntry = {
      ...entry,
      recent_runs: [
        {
          ...entry.recent_runs[0],
          id: "run-2",
          policy_change_id: "policy-travel",
        },
        ...entry.recent_runs,
      ],
    };
    vi.spyOn(globalThis, "fetch")
      .mockRejectedValueOnce(new Error("proxy response interrupted"))
      .mockResolvedValueOnce(
        new Response(JSON.stringify(authoritativeEntry), {
          status: 200,
          headers: { "content-type": "application/json" },
        }),
      );
    render(<PolicyAnalysisEntryView entry={entry} navigateToRun={navigateToRun} />);

    await user.click(screen.getByRole("button", { name: "Start new analysis" }));

    expect(fetch).toHaveBeenCalledTimes(2);
    expect(fetch).toHaveBeenLastCalledWith(
      "/api/v1/policy-analysis-entry",
      expect.objectContaining({ method: "GET", cache: "no-store" }),
    );
    expect(navigateToRun).toHaveBeenCalledWith("/policy-analyses/run-2");
  });

  it("shows an explicit non-duplicating recovery state when reconciliation fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("api unavailable"));
    render(<PolicyAnalysisEntryView entry={entry} navigateToRun={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Start new analysis" }));

    expect(screen.getByRole("alert")).toHaveTextContent(
      "The request outcome could not be confirmed. Recovery did not send another analysis request.",
    );
    expect(
      screen.getByRole("button", { name: "Check for persisted analysis" }),
    ).toBeInTheDocument();
  });

  it("creates a deterministic comparison from the selected ready policies", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "comparison-1" }), {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    );
    render(<PolicyAnalysisEntryView entry={entry} />);

    await user.click(screen.getByRole("button", { name: "Compare policy versions" }));

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/policy-comparisons",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          "X-ChangeOps-Actor": "portfolio-reviewer",
        }),
      }),
    );
    expect(push).toHaveBeenCalledWith("/policy-comparisons/comparison-1");
  });

  it("presents pending clarification as policy readiness, not lineage integrity", () => {
    const notReadyEntry = {
      ...entry,
      policies: entry.policies.map((policy) =>
        policy.id === "policy-proposed"
          ? {
              ...policy,
              comparison_readiness: {
                ready: false,
                status: "policy_not_ready",
                accepted_extraction_attempt_id: null,
              },
            }
          : policy,
      ),
    };

    render(<PolicyAnalysisEntryView entry={notReadyEntry} />);

    expect(
      screen.getByRole("heading", { name: "Compare policy versions" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Comparison becomes available after both policies have accepted, validated rules and completed assessments.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Not ready · analysis incomplete or clarification pending"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Compare policy versions" })).toBeDisabled();
  });
});
