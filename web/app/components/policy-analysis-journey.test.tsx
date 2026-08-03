import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PolicyAnalysisJourneyView } from "./policy-analysis-journey";
import type { PolicyAnalysisJourney } from "@/lib/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

const journey: PolicyAnalysisJourney = {
  policy: {
    id: "policy-travel",
    organization_id: "org-acme",
    organization_name: "Acme Global",
    title: "International Business Travel",
    owner: "People Operations",
    version: "2",
    effective_date: "2026-09-01",
    policy_text: "U.S.-based employees must complete training.",
  },
  run: {
    id: "run-1",
    organization_id: "org-acme",
    policy_change_id: "policy-travel",
    status: "completed",
    current_step: "terminal",
    latest_extraction_attempt_id: "attempt-1",
    assessment_id: "assessment-1",
    retry_count: 0,
    failure_code: null,
    failure_detail: null,
    accepted_rule_provenance: [],
    clarifications: [],
    metadata: {},
    created_at: "2026-08-01T12:00:00Z",
    updated_at: "2026-08-01T12:01:00Z",
    completed_at: "2026-08-01T12:01:00Z",
  },
  extraction: {
    id: "attempt-1",
    policy_change_id: "policy-travel",
    policy_family: "international_travel",
    support_status: "supported",
    validation_outcome: "accepted",
    candidate_rules: {
      kind: "international_travel",
      worker_scope: { assigned_work_country: "US" },
    },
    accepted_rules: { kind: "international_travel" },
    provenance: [
      {
        field_path: "candidate_rules.worker_scope.assigned_work_country",
        start: 0,
        end: 10,
        quote: "U.S.-based",
      },
    ],
    findings: [],
    validation_errors: [],
    metadata: {},
    created_at: "2026-08-01T12:00:30Z",
  },
  uncertainty: {
    extraction_findings: [],
    clarifications: [],
    legacy_assessment_questions: "omitted_schema_v1_fixture",
  },
  assessment: {
    id: "assessment-1",
    policy_change_id: "policy-travel",
    status: "completed",
    analyzer_version: "v1",
    created_at: "2026-08-01T12:01:00Z",
    completed_at: "2026-08-01T12:01:00Z",
    summary: {
      affected_workers: 1,
      unaffected_workers: 1,
      manager_approvals_required: 1,
      training_assignments_required: 1,
      enterprise_impacts: 1,
      impacts_by_domain: { systems: 1 },
    },
    worker_results: [
      {
        worker: { id: "worker-1", name: "Sarah Johnson" },
        trip_id: "trip-1",
        classification: "affected",
        explanation: "Trip is in scope.",
        reason_codes: ["TRIP_IN_SCOPE"],
      },
      {
        worker: { id: "worker-2", name: "Priya Shah" },
        trip_id: "trip-2",
        classification: "unaffected",
        explanation: "Destination is excluded.",
        reason_codes: ["DESTINATION_EXCLUDED"],
      },
    ],
    findings: [],
    evidence: [
      {
        id: "evidence-1",
        type: "system",
        source_type: "enterprise_system",
        source_id: "system-1",
        label: "Travel workflow",
        snapshot: { active: true },
      },
    ],
    enterprise_impacts: {
      systems: [
        {
          id: "impact-1",
          domain: "systems",
          object_type: "enterprise_system",
          source_key: "system-1",
          display_name: "Acme Travel",
          classification: "operationally_affected",
          explanation: "Approval workflow changed.",
          reason_code: "SYSTEM_SUPPORTS_CHANGED_APPROVAL_PROCESS",
          evidence_ids: ["evidence-1"],
          relationship_path: [
            {
              sequence: 0,
              object_type: "policy_change",
              stable_key: "policy-travel",
              display_label: "Travel policy",
              relationship_to_next: "affects",
            },
          ],
          proposed_action_ids: ["action-1"],
          sort_key: "systems:system-1",
        },
      ],
    },
    proposed_actions: [
      {
        id: "action-1",
        type: "review_system_workflow",
        worker_id: null,
        enterprise_impact_id: "impact-1",
        target: { type: "enterprise_system", identifier: "system-1" },
        description: "Review the travel workflow.",
        due_date: null,
        execution_status: "not_executed",
      },
    ],
  },
  enterprise_coverage: [
    {
      domain: "systems",
      considered: 2,
      affected: 1,
      cleared: 1,
      objects: [
        {
          id: "system-1",
          display_name: "Acme Travel",
          classification: "affected",
          impact_ids: ["impact-1"],
        },
        {
          id: "system-2",
          display_name: "Acme Expense",
          classification: "cleared",
          impact_ids: [],
        },
      ],
    },
  ],
  interpretation: {
    status: "available",
    failure_code: null,
    change_plan: {
      id: "plan-1",
      policy_analysis_run_id: "run-1",
      impact_assessment_id: "assessment-1",
      interpretation_attempt_id: "interpretation-1",
      schema_version: "policy-interpretation-v1",
      created_at: "2026-08-01T12:02:00Z",
      change_plan: {
        schema_version: "policy-interpretation-v1",
        summary: "Review one grounded concern.",
        coverage_gaps: [
          {
            finding_key: "scope-gap",
            title: "Review scope definition",
            observed_limitation: "Scope terminology needs review.",
            why_it_matters: "Worker classification depends on scope.",
            recommended_review_action: "Review with the policy owner.",
            conclusion_type: "review_concern",
            policy_spans: [
              { policy_change_id: "policy-travel", start: 0, end: 10, quote: "U.S.-based" },
            ],
            impact_references: [{ assessment_id: "assessment-1", impact_id: "impact-1" }],
            evidence_references: [
              {
                assessment_id: "assessment-1",
                evidence_key: "system:system-1",
                impact_id: "impact-1",
                finding_id: null,
              },
            ],
            relationship_path_references: [],
          },
        ],
      },
    },
    resolved_references: [
      {
        finding_key: "scope-gap",
        impacts: [
          {
            impact_id: "impact-1",
            display_name: "Acme Travel",
            domain: "systems",
            classification: "operationally_affected",
            reason_code: "SYSTEM_SUPPORTS_CHANGED_APPROVAL_PROCESS",
          },
        ],
        evidence: [
          {
            evidence_key: "system:system-1",
            label: "Travel workflow",
            evidence_type: "system",
            source_type: "enterprise_system",
            source_id: "system-1",
          },
        ],
        policy_spans: [
          {
            policy_change_id: "policy-travel",
            start: 0,
            end: 10,
            quote: "U.S.-based",
            validated_against_policy_snapshot: true,
          },
        ],
      },
    ],
  },
  approval_run: null,
  execution: {
    status: "unavailable",
    command_count: 0,
    executed_command_count: 0,
    result_count: 0,
    replay_count: 0,
  },
};

describe("policy analysis journey", () => {
  it("renders AI proposals, deterministic results, coverage, and grounded citations separately", () => {
    render(<PolicyAnalysisJourneyView initialJourney={journey} />);

    expect(screen.getByText("AI suggested rules")).toBeInTheDocument();
    expect(screen.getAllByText("System-calculated").length).toBeGreaterThan(0);
    expect(
      screen.getByRole("heading", { name: "What did this analysis establish?" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "What policy are we evaluating?" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "What rules did ChangeOps identify?" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Who and what is affected?" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "What enterprise records were evaluated?" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Why are they affected?" })).toBeInTheDocument();
    expect(screen.getByText("Sarah Johnson")).toBeInTheDocument();
    expect(screen.getByText("Priya Shah")).toBeInTheDocument();
    expect(screen.getByText("Acme Expense")).toBeInTheDocument();
    expect(screen.getByText("Review scope definition")).toBeInTheDocument();
    expect(screen.getByText(/system:system-1/)).toBeInTheDocument();
    expect(screen.getAllByText("Travel workflow").length).toBeGreaterThan(1);
    expect(screen.getAllByText("Acme Travel").length).toBeGreaterThan(1);
    expect(screen.getByText(/Validated against the policy snapshot/)).toBeInTheDocument();
    expect(screen.getByTitle("impact-1")).toHaveTextContent("impact-1");
    expect(screen.getByText("No clarification required")).toBeInTheDocument();
    const proposedActions = screen.getByRole("heading", { name: "What should change?" }).closest(
      "section",
    );
    expect(proposedActions).not.toBeNull();
    expect(within(proposedActions!).getByText("System-proposed")).toBeInTheDocument();
    expect(within(proposedActions!).queryByText("AI proposal")).not.toBeInTheDocument();
    expect(
      screen.getByText("View exact policy provenance (1 records)").closest("details"),
    ).not.toHaveAttribute("open");
    expect(
      screen.getByText("View persisted grounding and lineage").closest("details"),
    ).not.toHaveAttribute("open");
    expect(
      screen.getAllByText("View deterministic reason codes")[0].closest("details"),
    ).not.toHaveAttribute("open");
    expect(screen.getByRole("button", { name: "Create approval run" })).toBeEnabled();
  });

  it("does not present legacy assessment fixture questions as model uncertainty", () => {
    render(<PolicyAnalysisJourneyView initialJourney={journey} />);

    expect(
      screen.getByText(/Legacy seeded assessment questions are intentionally omitted/),
    ).toBeInTheDocument();
    expect(screen.queryByText("How long does the training remain valid?")).not.toBeInTheDocument();
  });

  it("renders the supported pending clarification interaction", () => {
    const pending: PolicyAnalysisJourney = {
      ...journey,
      run: {
        ...journey.run,
        status: "awaiting_clarification",
        assessment_id: null,
        completed_at: null,
      },
      uncertainty: {
        extraction_findings: [],
        legacy_assessment_questions: "omitted_schema_v1_fixture",
        clarifications: [
          {
            id: "clarification-1",
            question_code: "confirm_booking_exception",
            question_text: "Confirm that pre-effective bookings are exempt.",
            expected_answer_contract: { type: "literal", allowed_values: [true] },
            affected_fields: [
              "candidate_rules.manager_approval.booking_before_effective_date_is_exempt",
            ],
            status: "pending",
            answer: null,
            responder_identity: null,
            answer_provenance: null,
            created_at: "2026-08-01T12:00:45Z",
            answered_at: null,
          },
        ],
      },
      assessment: null,
      enterprise_coverage: [],
      interpretation: {
        status: "not_available",
        failure_code: null,
        change_plan: null,
        resolved_references: [],
      },
      approval_run: null,
    };

    render(<PolicyAnalysisJourneyView initialJourney={pending} />);

    expect(
      screen.getByText("Confirm that pre-effective bookings are exempt."),
    ).toBeInTheDocument();
    expect(screen.getByText("[true]")).toBeInTheDocument();
    expect(screen.getByText("Clarification required")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Confirm and resume analysis" }),
    ).toBeEnabled();
    expect(screen.getByText("View clarification contract").closest("details")).not.toHaveAttribute(
      "open",
    );
  });

  it("shows a terminal unsupported run without enabling approval", () => {
    const unsupported: PolicyAnalysisJourney = {
      ...journey,
      run: {
        ...journey.run,
        status: "unsupported",
        assessment_id: null,
        failure_code: "unsupported_policy_family",
        failure_detail: null,
      },
      extraction: {
        ...journey.extraction!,
        support_status: "unsupported",
        validation_outcome: "unsupported",
        accepted_rules: null,
      },
      assessment: null,
      enterprise_coverage: [],
      interpretation: {
        status: "not_available",
        failure_code: null,
        change_plan: null,
        resolved_references: [],
      },
      approval_run: null,
    };

    render(<PolicyAnalysisJourneyView initialJourney={unsupported} />);

    expect(screen.getByText("Analysis could not complete")).toBeInTheDocument();
    expect(
      screen.getByText(
        "The persisted workflow stopped before an impact assessment was created. No proposed actions were created.",
      ),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Unsupported", { selector: ".badge" })).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Create approval run" })).toBeDisabled();
    const workflow = screen.getByRole("navigation", { name: "ChangeOps workflow" });
    expect(within(workflow).getByText("Analysis").closest("li")).toHaveClass("failed");
    expect(within(workflow).getByText("Assessment").closest("li")).toHaveClass("unavailable");
  });

  it("explains validation failure plainly and keeps internal records collapsed", () => {
    const failed: PolicyAnalysisJourney = {
      ...journey,
      run: {
        ...journey.run,
        status: "failed",
        assessment_id: null,
        failure_code: "extraction_validation_failed",
        failure_detail: "duplicate_provenance",
      },
      extraction: {
        ...journey.extraction!,
        validation_outcome: "validation_failed",
        accepted_rules: null,
        validation_errors: [
          {
            code: "duplicate_provenance",
            message: "Each material field must have exactly one provenance span.",
            field_path:
              "candidate_rules.manager_approval.booking_before_effective_date_is_exempt",
          },
        ],
      },
      assessment: null,
      enterprise_coverage: [],
      interpretation: {
        status: "not_available",
        failure_code: null,
        change_plan: null,
        resolved_references: [],
      },
      approval_run: null,
    };

    render(<PolicyAnalysisJourneyView initialJourney={failed} />);

    expect(
      screen.getByText(
        "ChangeOps identified proposed policy rules, but their supporting policy evidence did not pass deterministic validation. No impact assessment or proposed actions were created.",
      ),
    ).toBeInTheDocument();
    const validationMessages = screen.getAllByText(
      "Each material field must have exactly one provenance span.",
    );
    expect(validationMessages).toHaveLength(2);
    expect(validationMessages[0]).toBeVisible();
    expect(validationMessages[1].closest("details")).not.toHaveAttribute("open");
    expect(
      screen.queryByText(
        "These values come directly from the accepted extraction and immutable assessment. Use the sections below to inspect their supporting explanations and evidence.",
      ),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(
        "No immutable assessment was created. The persisted rule-validation result and unavailable downstream outcomes are shown below.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("View technical failure details").closest("details")).not.toHaveAttribute(
      "open",
    );
    expect(
      screen.getByText("View deterministic validation records").closest("details"),
    ).not.toHaveAttribute("open");
    for (const code of screen.getAllByText("duplicate_provenance")) {
      expect(code.closest("details")).not.toHaveAttribute("open");
    }
  });

  it("does not conflate completed approval, prepared commands, and execution", () => {
    const prepared: PolicyAnalysisJourney = {
      ...journey,
      approval_run: { id: "approval-1", status: "completed" },
      execution: {
        status: "command_prepared",
        command_count: 1,
        executed_command_count: 0,
        result_count: 0,
        replay_count: 0,
      },
    };

    render(<PolicyAnalysisJourneyView initialJourney={prepared} />);

    expect(screen.getByText("Command prepared")).toBeInTheDocument();
    const workflow = screen.getByRole("navigation", { name: "ChangeOps workflow" });
    expect(within(workflow).getByText("Approval").closest("li")).toHaveClass("completed");
    expect(within(workflow).getByText("Execution").closest("li")).toHaveClass("current");
  });
});
