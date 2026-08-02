export type ReviewStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "deferred"
  | "revision_requested";

export interface OriginalAction {
  proposed_action_id: string;
  assessment_id: string;
  finding_id: string | null;
  enterprise_impact_id: string | null;
  worker_id: string | null;
  action_type: string;
  target_type: string;
  target_identifier: string;
  description: string;
  due_date: string | null;
  execution_status: "not_executed";
}

export interface Decision {
  id: string;
  decision: Exclude<ReviewStatus, "pending">;
  reviewer_identity: string;
  reviewer_role: "reviewer" | "admin";
  rationale: string;
  edited_action: { description?: string; due_date?: string } | null;
  created_at: string;
}

export interface Review {
  id: string;
  status: ReviewStatus;
  original_action: OriginalAction;
  review_context: {
    finding_id: string | null;
    enterprise_impact_id: string | null;
    reason_code: string | null;
    evidence_keys: string[];
  };
  current_decision: Decision | null;
  effective_approved_action: OriginalAction | null;
  completed_at: string | null;
}

export interface Evidence {
  key: string;
  source_type:
    | "policy_quote"
    | "deterministic_finding"
    | "enterprise_impact"
    | "relationship_path";
  label: string;
  detail: string;
  policy_quote: string | null;
  reason_code: string | null;
  relationship_path: string[];
}

export interface WorkbenchItem {
  sequence: number;
  review: Review;
  evidence: Evidence[];
  finding: {
    id: string;
    finding_type: string;
    severity: string;
    rule_code: string;
    worker_id: string;
    explanation: string;
  } | null;
  enterprise_impact: {
    id: string;
    domain: string;
    object_type: string;
    source_key: string;
    display_name: string;
    classification: string;
    explanation: string;
    reason_code: string;
    relationship_path: {
      sequence: number;
      object_type: string;
      stable_key: string;
      display_label: string;
      relationship_to_next: string | null;
    }[];
  } | null;
}

export interface Workbench {
  run: {
    id: string;
    assessment_id: string;
    policy_analysis_run_id: string;
    status: "initializing" | "awaiting_decisions" | "completed" | "failed";
    current_step: string;
    summary: Record<
      "total" | "pending" | "approved" | "rejected" | "deferred" | "revision_requested",
      number
    >;
    failure_code: string | null;
    failure_message: string | null;
    transitions: {
      id: string;
      from_status: string | null;
      to_status: string;
      from_step: string | null;
      to_step: string;
      reason_code: string;
      trigger_type: string;
      actor_identity: string | null;
      created_at: string;
    }[];
  };
  assessment: {
    id: string;
    policy_change_id: string;
    completed_at: string;
    affected_worker_count: number;
    enterprise_impact_count: number;
    proposed_action_count: number;
  };
  items: WorkbenchItem[];
}

export interface ExecutionCommand {
  id: string;
  approval_run_id: string;
  action_review_id: string;
  action_review_decision_id: string;
  proposed_action_id: string;
  assessment_id: string;
  sequence: number;
  schema_version: "execution-command-v1";
  system: "learning";
  operation: "assign_training";
  target_type: string;
  target_identifier: string;
  parameters: Record<string, unknown>;
  effective_action: OriginalAction & { schema_version: "effective-approved-action-v1" };
  idempotency_key: string;
  status: "pending_execution";
  prepared_by: string;
  prepared_role: "admin";
  created_at: string;
  execution_state: "pending_execution" | "executed" | "execution_failed";
  execution_results: ExecutionResult[];
  execution_performed: boolean;
}

export interface SimulatedLearningAssignment {
  id: string;
  worker_id: string;
  training_course_id: string;
  source_execution_command_id: string;
  source_approved_action_id: string;
  assignment_status: "assigned";
  assigned_at: string;
  created_at: string;
}

export interface ExecutionResult {
  id: string;
  execution_command_id: string;
  status: "succeeded" | "already_applied" | "rejected_unsupported" | "failed_validation";
  outcome_code: string;
  message: string;
  command_idempotency_key: string;
  attempted_by: string;
  attempted_role: "admin";
  created_at: string;
  learning_assignment: SimulatedLearningAssignment | null;
}

export interface ExecutionPreparation {
  approval_run_id: string;
  approved_action_count: number;
  eligible_action_count: number;
  prepared_command_count: number;
  unsupported_approved_action_count: number;
  commands: ExecutionCommand[];
  unsupported_items: {
    sequence: number;
    action_review_id: string;
    proposed_action_id: string;
    action_type: string;
    target_type: string;
    target_identifier: string;
    reason_code: "unsupported_action_type" | "unsupported_target_type";
    reason: string;
  }[];
  execution_performed: boolean;
}

export interface ApiError {
  code: string;
  message: string;
}
