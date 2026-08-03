import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PolicyComparisonView } from "./policy-comparison";
import type { PolicyComparison } from "@/lib/types";

const comparison: PolicyComparison = {
  id: "comparison-1",
  organization_id: "org-acme",
  baseline: {
    policy_change_id: "baseline",
    title: "Current Travel Policy",
    version: "current",
    effective_date: "2026-09-01",
    accepted_extraction_attempt_id: "attempt-baseline",
  },
  proposed: {
    policy_change_id: "proposed",
    title: "Proposed Travel Revision",
    version: "proposed",
    effective_date: "2026-10-01",
    accepted_extraction_attempt_id: "attempt-proposed",
  },
  comparison_contract_version: "international-travel-policy-comparison-v1",
  comparison_fingerprint: "a".repeat(64),
  difference_count: 1,
  differences: [
    {
      id: "difference-1",
      sequence: 1,
      rule_identity: "worker_scope.worker_types:contractor",
      field_path: "worker_scope.worker_types",
      change_type: "removed",
      baseline_value: "contractor",
      proposed_value: null,
      material: true,
      reason_code: "WORKER_TYPE_REMOVED",
      baseline_provenance: {
        source: "policy_text",
        quote: "employees and contractors",
        start: 10,
        end: 35,
      },
      proposed_provenance: null,
    },
  ],
  created_by: "reviewer@example.test",
  created_at: "2026-08-03T12:00:00Z",
};

describe("policy comparison", () => {
  it("shows sources, ordered semantic values, provenance, and the impact-delta boundary", () => {
    render(<PolicyComparisonView comparison={comparison} />);

    expect(screen.getByText("Current Travel Policy")).toBeInTheDocument();
    expect(screen.getByText("Proposed Travel Revision")).toBeInTheDocument();
    expect(screen.getByText("contractor")).toBeInTheDocument();
    expect(screen.getByText("Not present")).toBeInTheDocument();
    expect(screen.getByText("employees and contractors")).toBeInTheDocument();
    expect(screen.getByText("Operationally material")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "Enterprise impact delta has not been calculated",
      }),
    ).toBeInTheDocument();
  });

  it("renders the empty semantic comparison state", () => {
    render(
      <PolicyComparisonView
        comparison={{ ...comparison, difference_count: 0, differences: [] }}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "No operational semantic differences" }),
    ).toBeInTheDocument();
  });
});
