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

export interface ApiError {
  code: string;
  message: string;
}
