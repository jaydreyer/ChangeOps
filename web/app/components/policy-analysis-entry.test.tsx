import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
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
    },
  ],
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
  it("shows the golden policy and opens a recent durable run", () => {
    render(<PolicyAnalysisEntryView entry={entry} />);

    expect(screen.getByText("International Business Travel")).toBeInTheDocument();
    expect(screen.getByText("Travelers must complete training.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open analysis" })).toHaveAttribute(
      "href",
      "/policy-analyses/run-1",
    );
  });

  it("starts a run and navigates without inventing progress", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ id: "run-2" }), {
        status: 201,
        headers: { "content-type": "application/json" },
      }),
    );
    render(<PolicyAnalysisEntryView entry={entry} />);

    await user.click(screen.getByRole("button", { name: "Start new analysis" }));

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/policy-analysis-runs",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ policy_change_id: "policy-travel" }),
      }),
    );
    expect(push).toHaveBeenCalledWith("/policy-analyses/run-2");
  });
});
