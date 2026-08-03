import type { PolicyAnalysisJourney } from "@/lib/types";

export const journeyStepNames = [
  "Policy",
  "Analysis",
  "Clarification",
  "Assessment",
  "Interpretation",
  "Approval",
  "Execution",
] as const;

export type JourneyStepState =
  | "completed"
  | "current"
  | "available"
  | "not_required"
  | "blocked"
  | "failed"
  | "unavailable";

export function deriveJourneyStates(journey: PolicyAnalysisJourney): JourneyStepState[] {
  const { run, assessment, interpretation, approval_run: approval, execution } = journey;
  const pendingClarification = run.clarifications.some((item) => item.status === "pending");
  const answeredClarification = run.clarifications.some((item) => item.status === "answered");
  const analysisFailed = run.status === "failed" || run.status === "unsupported";

  const analysis: JourneyStepState = analysisFailed
    ? "failed"
    : run.latest_extraction_attempt_id
      ? "completed"
      : "current";
  const clarification: JourneyStepState = pendingClarification
    ? "current"
    : answeredClarification
      ? "completed"
      : run.status === "failed"
        ? "unavailable"
        : run.latest_extraction_attempt_id || run.status === "unsupported"
          ? "not_required"
          : "unavailable";
  const assessmentState: JourneyStepState = assessment
    ? "completed"
    : pendingClarification
      ? "blocked"
      : analysisFailed
        ? "unavailable"
        : run.current_step === "create_assessment"
          ? "current"
          : "unavailable";
  const interpretationState: JourneyStepState =
    interpretation.status === "available"
      ? "completed"
      : interpretation.status === "failed"
        ? "failed"
        : assessment
          ? "available"
          : "unavailable";
  const approvalState: JourneyStepState = !approval
    ? assessment
      ? "available"
      : "unavailable"
    : approval.status === "failed"
      ? "failed"
      : approval.status === "completed"
        ? "completed"
        : "current";
  const executionState: JourneyStepState =
    execution.status === "executed"
      ? "completed"
      : execution.status === "failed"
        ? "failed"
        : execution.status === "command_prepared"
          ? "current"
          : execution.status === "eligible"
            ? "available"
            : "unavailable";

  return [
    "completed",
    analysis,
    clarification,
    assessmentState,
    interpretationState,
    approvalState,
    executionState,
  ];
}

export function clarificationLabel(journey: PolicyAnalysisJourney) {
  const clarifications = journey.uncertainty.clarifications;
  if (clarifications.some((item) => item.status === "pending")) return "Clarification required";
  if (clarifications.some((item) => item.status === "answered")) return "Clarification completed";
  if (journey.run.status === "failed") return "Clarification unavailable";
  return "No clarification required";
}
