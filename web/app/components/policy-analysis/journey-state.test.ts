import { describe, expect, it } from "vitest";
import type { PolicyAnalysisJourney } from "@/lib/types";
import { clarificationLabel, deriveJourneyStates } from "./journey-state";

function minimalJourney(
  overrides: Partial<PolicyAnalysisJourney> = {},
): PolicyAnalysisJourney {
  return {
    policy: {} as PolicyAnalysisJourney["policy"],
    run: {
      status: "completed",
      current_step: "terminal",
      latest_extraction_attempt_id: "attempt-1",
      clarifications: [],
    } as unknown as PolicyAnalysisJourney["run"],
    extraction: null,
    uncertainty: {
      extraction_findings: [],
      clarifications: [],
      legacy_assessment_questions: "omitted_schema_v1_fixture",
    },
    assessment: {} as PolicyAnalysisJourney["assessment"],
    enterprise_coverage: [],
    interpretation: {
      status: "not_created",
      failure_code: null,
      change_plan: null,
      resolved_references: [],
    },
    approval_run: null,
    execution: {
      status: "unavailable",
      command_count: 0,
      executed_command_count: 0,
      result_count: 0,
      replay_count: 0,
    },
    ...overrides,
  };
}

describe("journey state derivation", () => {
  it("marks omitted clarification as not required", () => {
    const journey = minimalJourney();
    expect(deriveJourneyStates(journey)[2]).toBe("not_required");
    expect(clarificationLabel(journey)).toBe("No clarification required");
  });

  it("blocks future analysis while clarification is pending", () => {
    const clarification = { status: "pending" } as PolicyAnalysisJourney["run"]["clarifications"][0];
    const journey = minimalJourney({
      run: {
        ...minimalJourney().run,
        status: "awaiting_clarification",
        clarifications: [clarification],
      },
      uncertainty: {
        ...minimalJourney().uncertainty,
        clarifications: [clarification],
      },
      assessment: null,
    });
    expect(deriveJourneyStates(journey)).toEqual([
      "completed",
      "completed",
      "current",
      "blocked",
      "unavailable",
      "unavailable",
      "unavailable",
    ]);
    expect(clarificationLabel(journey)).toBe("Clarification required");
  });

  it("distinguishes completed clarification and failed interpretation", () => {
    const clarification = {
      status: "answered",
    } as PolicyAnalysisJourney["run"]["clarifications"][0];
    const journey = minimalJourney({
      run: { ...minimalJourney().run, clarifications: [clarification] },
      uncertainty: {
        ...minimalJourney().uncertainty,
        clarifications: [clarification],
      },
      interpretation: {
        status: "failed",
        failure_code: "provider_failed",
        change_plan: null,
        resolved_references: [],
      },
    });
    expect(deriveJourneyStates(journey)[2]).toBe("completed");
    expect(deriveJourneyStates(journey)[4]).toBe("failed");
    expect(clarificationLabel(journey)).toBe("Clarification completed");
  });

  it("does not call clarification completed or unnecessary after analysis failure", () => {
    const journey = minimalJourney({
      run: {
        ...minimalJourney().run,
        status: "failed",
        failure_code: "retry_limit_exhausted",
      },
      assessment: null,
    });
    expect(deriveJourneyStates(journey)[2]).toBe("unavailable");
    expect(clarificationLabel(journey)).toBe("Clarification unavailable");
  });
});
