import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
  impact_delta: {
    id: "impact-delta-1",
    baseline_assessment_id: "assessment-baseline",
    proposed_assessment_id: "assessment-proposed",
    impact_delta_contract_version: "enterprise-impact-delta-v1",
    impact_delta_fingerprint: "b".repeat(64),
    summary: {
      workers_became_affected: 0,
      workers_no_longer_affected: 1,
      workers_remained_affected: 0,
      findings_introduced: 0,
      findings_disappeared: 1,
      enterprise_impacts_introduced: 0,
      enterprise_impacts_removed: 1,
    },
    worker_deltas: [
      {
        id: "worker-delta-1",
        sequence: 1,
        stable_identity: "worker:worker-marcus:trip:trip-marcus",
        change_type: "no_longer_affected",
        delta_reason_code: "WORKER_NO_LONGER_AFFECTED",
        baseline_record_id: "baseline-worker-result",
        proposed_record_id: "proposed-worker-result",
        baseline: {
          worker_id: "worker-marcus",
          display_name: "Marcus Lee",
          trip_id: "trip-marcus",
          classification: "affected",
          explanation: "Marcus was covered as a contractor.",
          reason_codes: ["WORKER_IN_SCOPE"],
          evidence: [],
        },
        proposed: {
          worker_id: "worker-marcus",
          display_name: "Marcus Lee",
          trip_id: "trip-marcus",
          classification: "unaffected",
          explanation: "Marcus is outside the employee-only scope.",
          reason_codes: ["WORKER_TYPE_OUT_OF_SCOPE"],
          evidence: [],
        },
      },
    ],
    finding_deltas: [
      {
        id: "finding-delta-1",
        sequence: 2,
        stable_identity: "finding:worker-marcus:trip-marcus:training",
        change_type: "disappeared",
        delta_reason_code: "FINDING_DISAPPEARED",
        baseline_record_id: "baseline-finding",
        proposed_record_id: null,
        baseline: {
          worker_id: "worker-marcus",
          trip_id: "trip-marcus",
          finding_type: "manager_approval_required",
          severity: "action_required",
          rule_code: "MANAGER_APPROVAL_REQUIRED",
          explanation: "Manager approval was required.",
          evidence: [],
        },
        proposed: null,
      },
    ],
    enterprise_impact_deltas: [
      {
        id: "enterprise-impact-delta-1",
        sequence: 3,
        stable_identity: "enterprise_impact:teams:team:technology",
        change_type: "removed",
        delta_reason_code: "ENTERPRISE_IMPACT_REMOVED",
        baseline_record_id: "baseline-impact",
        proposed_record_id: null,
        baseline: {
          domain: "teams",
          object_type: "team",
          source_key: "team-technology",
          display_name: "Technology Operations",
          classification: "operationally_affected",
          explanation: "The team contained an affected worker.",
          reason_code: "TEAM_HAS_AFFECTED_WORKERS",
          evidence: [
            {
              record_id: "evidence-1",
              evidence_key: "team:team-technology",
              evidence_type: "team_record",
              source_type: "team",
              source_id: "team-technology",
              label: "Technology Operations team record",
              snapshot: { team_id: "team-technology" },
            },
          ],
          relationship_path: [
            {
              sequence: 0,
              object_type: "team",
              stable_key: "team-technology",
              display_label: "Technology Operations",
              relationship_to_next: null,
            },
          ],
        },
        proposed: null,
      },
    ],
    created_by: "reviewer@example.test",
    created_at: "2026-08-03T12:00:00Z",
  },
  created_by: "reviewer@example.test",
  created_at: "2026-08-03T12:00:00Z",
};

describe("policy comparison", () => {
  it("prioritizes policy changes before the response-derived operational story", () => {
    const { container } = render(<PolicyComparisonView comparison={comparison} />);

    expect(
      screen.getByRole("link", { name: "← All policy analyses and comparisons" }),
    ).toHaveAttribute("href", "/");
    expect(screen.getByText("ChangeOps")).toBeInTheDocument();
    expect(screen.getByText("Authoritative comparison")).toBeInTheDocument();
    expect(screen.getByText("Immutable persisted record")).toBeInTheDocument();
    expect(screen.getByText("Initiated by reviewer@example.test")).toBeInTheDocument();
    expect(screen.getByText("View comparison identity").closest("details")).not.toHaveAttribute(
      "open",
    );
    expect(screen.getByText("Current Travel Policy")).toBeInTheDocument();
    expect(screen.getByText("Proposed Travel Revision")).toBeInTheDocument();
    expect(screen.getByText("contractor")).toBeInTheDocument();
    expect(screen.getByText("employees and contractors")).toBeInTheDocument();
    expect(screen.getByText("Operationally material")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "What policy obligations changed" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Change summary" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Operational impact changes" }),
    ).toBeInTheDocument();

    const policyChanges = container.querySelector("#policy-changes-heading");
    const changeSummary = container.querySelector("#change-summary-heading");
    const operationalChanges = screen.getByRole("heading", { name: "Operational impact changes" });
    expect(policyChanges).not.toBeNull();
    expect(changeSummary).not.toBeNull();
    expect(
      policyChanges!.compareDocumentPosition(changeSummary!) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      changeSummary!.compareDocumentPosition(operationalChanges) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();

    expect(screen.getByText("Policy obligations changed").closest("li")).toHaveTextContent(
      "0 added · 1 removed · 0 modified",
    );
    expect(screen.getByText("Worker-trip outcomes in the delta").closest("li")).toHaveTextContent(
      "1 no longer affected",
    );
    expect(screen.getByText("Finding differences").closest("li")).toHaveTextContent(
      "1 disappeared",
    );
    expect(screen.getByText("Enterprise impact differences").closest("li")).toHaveTextContent(
      "1 removed",
    );
    const ruleEvidence = screen
      .getByText("View accepted rule evidence and identity")
      .closest("details");
    expect(ruleEvidence).not.toHaveAttribute("open");
    expect(within(ruleEvidence as HTMLElement).getByText("WORKER_TYPE_REMOVED")).toBeInTheDocument();
    expect(
      within(ruleEvidence as HTMLElement).getByText("employees and contractors"),
    ).toBeInTheDocument();
  });

  it("keeps causal scope visible and audit details collapsed until independently opened", async () => {
    const user = userEvent.setup();
    render(<PolicyComparisonView comparison={comparison} />);

    expect(
      screen.getByRole("heading", { name: "What this comparison can establish" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /compares two authoritative persisted assessment outcomes.*does not claim that policy changes were the sole cause/s,
      ),
    ).toBeInTheDocument();
    const seededScope = screen.getByText("Seeded demonstration scope").closest("details");
    expect(seededScope).not.toHaveAttribute("open");

    const workerItem = screen.getByText("Marcus Lee").closest("details");
    const impactTitle = screen.getByText("Technology Operations", {
      selector: ".delta-item-title > strong",
    });
    const impactItem = impactTitle.closest("details");
    expect(workerItem).not.toHaveAttribute("open");
    expect(impactItem).not.toHaveAttribute("open");
    expect(screen.getByText("No longer affected")).toBeInTheDocument();
    expect(screen.getByText("WORKER_NO_LONGER_AFFECTED")).toBeInTheDocument();
    expect(screen.getByText("Affected → Unaffected · Trip trip-marcus")).toBeInTheDocument();
    expect(
      screen.getByLabelText("Worker impact changes classification counts"),
    ).toHaveTextContent("0 became affected1 no longer affected0 remain affected");
    expect(screen.getByLabelText("Finding changes classification counts")).toHaveTextContent(
      "0 introduced1 disappeared",
    );
    expect(
      screen.getByLabelText("Enterprise impact changes classification counts"),
    ).toHaveTextContent("0 introduced1 removed");

    await user.click(impactTitle.closest("summary") as HTMLElement);

    expect(impactItem).toHaveAttribute("open");
    expect(workerItem).not.toHaveAttribute("open");
    expect(
      screen.getByText("Technology Operations", { selector: ".relationship-path" }),
    ).toBeVisible();
    expect(
      screen.getByText("enterprise_impact:teams:team:technology"),
    ).toBeVisible();

    await user.click(screen.getByText("1 authoritative evidence records"));
    expect(screen.getByText("Technology Operations team record")).toBeVisible();
    expect(
      screen.getByRole("heading", { name: "AI explanation remains deferred" }),
    ).toBeInTheDocument();
  });

  it("renders accurate group totals and zero-count states", () => {
    const emptyDelta = {
      ...comparison.impact_delta!,
      summary: {
        workers_became_affected: 0,
        workers_no_longer_affected: 0,
        workers_remained_affected: 0,
        findings_introduced: 0,
        findings_disappeared: 0,
        enterprise_impacts_introduced: 0,
        enterprise_impacts_removed: 0,
      },
      worker_deltas: [],
      finding_deltas: [],
      enterprise_impact_deltas: [],
    };
    render(
      <PolicyComparisonView
        comparison={{
          ...comparison,
          difference_count: 0,
          differences: [],
          impact_delta: emptyDelta,
        }}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "No operational semantic differences" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Policy obligations changed").closest("li")).toHaveTextContent("0");
    expect(screen.getByText("Worker-trip outcomes in the delta").closest("li")).toHaveTextContent(
      "0 became affected · 0 no longer affected · 0 remain affected",
    );
    expect(screen.getByText("Worker impact changes")).toBeInTheDocument();
    expect(screen.getByText("Finding changes")).toBeInTheDocument();
    expect(screen.getByText("Enterprise impact changes")).toBeInTheDocument();
    expect(screen.getAllByText("No differences are recorded in this category.")).toHaveLength(3);
  });

  it("renders a stable state for historical comparisons without a persisted delta", () => {
    render(<PolicyComparisonView comparison={{ ...comparison, impact_delta: null }} />);

    expect(
      screen.getByRole("heading", { name: "Enterprise impact delta is unavailable" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("View comparison, extraction, assessment, and fingerprint lineage"),
    ).toBeInTheDocument();
  });
});
