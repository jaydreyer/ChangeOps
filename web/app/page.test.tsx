import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import HomePage from "./page";
import { getPolicyAnalysisEntry } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  getPolicyAnalysisEntry: vi.fn(),
}));

vi.mock("./components/policy-analysis-entry", () => ({
  PolicyAnalysisEntryView: () => <div>Policy analysis entry</div>,
}));

describe("home page", () => {
  it("loads the product-facing policy analysis entry", async () => {
    vi.mocked(getPolicyAnalysisEntry).mockResolvedValue({ policies: [], recent_runs: [] });

    render(await HomePage());

    expect(screen.getByText("Policy analysis entry")).toBeInTheDocument();
  });

  it("renders a safe API failure", async () => {
    vi.mocked(getPolicyAnalysisEntry).mockRejectedValue(
      new Error("api_unavailable|The ChangeOps API is unavailable."),
    );

    render(await HomePage());

    expect(screen.getByRole("alert")).toHaveTextContent("The ChangeOps API is unavailable.");
  });
});
