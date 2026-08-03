import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PolicyComparisonPage from "./page";
import { getPolicyComparison } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  getPolicyComparison: vi.fn(),
}));

vi.mock("@/app/components/policy-comparison", () => ({
  PolicyComparisonView: () => <div>Policy comparison detail</div>,
}));

describe("policy comparison page", () => {
  it("loads a persisted comparison", async () => {
    vi.mocked(getPolicyComparison).mockResolvedValue({ id: "comparison-1" } as never);

    render(
      await PolicyComparisonPage({
        params: Promise.resolve({ comparisonId: "comparison-1" }),
      }),
    );

    expect(getPolicyComparison).toHaveBeenCalledWith("comparison-1");
    expect(screen.getByText("Policy comparison detail")).toBeInTheDocument();
  });

  it("renders a stable retrieval error", async () => {
    vi.mocked(getPolicyComparison).mockRejectedValue(
      new Error("policy_comparison_not_found|Policy comparison was not found."),
    );

    render(
      await PolicyComparisonPage({
        params: Promise.resolve({ comparisonId: "missing" }),
      }),
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Policy comparison was not found.");
  });
});
