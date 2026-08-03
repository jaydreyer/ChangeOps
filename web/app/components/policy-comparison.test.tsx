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
  it("shows semantic differences and deterministic operational consequences", () => {
    render(<PolicyComparisonView comparison={comparison} />);

    expect(screen.getByText("Current Travel Policy")).toBeInTheDocument();
    expect(screen.getByText("Proposed Travel Revision")).toBeInTheDocument();
    expect(screen.getByText("contractor")).toBeInTheDocument();
    expect(screen.getByText("Not present")).toBeInTheDocument();
    expect(screen.getByText("employees and contractors")).toBeInTheDocument();
    expect(screen.getByText("Operationally material")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "How did the persisted operational outcomes differ?" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Outcome comparison, not sole-cause proof" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /compares two authoritative persisted assessment outcomes.*does not prove that policy changes alone caused every difference/s,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /seeded demonstration evaluates both assessments against the same enterprise catalog state/,
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Marcus Lee")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Technology Operations" })).toBeInTheDocument();
    expect(screen.getByText("Technology Operations team record")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "AI explanation remains deferred" }),
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

  it("renders a stable state for historical comparisons without a persisted delta", () => {
    render(<PolicyComparisonView comparison={{ ...comparison, impact_delta: null }} />);

    expect(
      screen.getByRole("heading", { name: "Enterprise impact delta is unavailable" }),
    ).toBeInTheDocument();
  });
});
