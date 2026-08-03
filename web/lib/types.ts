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

export interface AnalysisPolicy {
  id: string;
  organization_id: string;
  organization_name: string;
  title: string;
  owner: string;
  version: string;
  effective_date: string;
  policy_text: string;
}

export interface AnalysisEntryPolicy extends AnalysisPolicy {
  comparison_readiness: {
    ready: boolean;
    status: string;
    accepted_extraction_attempt_id: string | null;
  };
}

export interface AnalysisRunSummary {
  id: string;
  policy_change_id: string;
  status: string;
  current_step: string;
  assessment_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface PolicyAnalysisEntry {
  policies: AnalysisEntryPolicy[];
  recent_runs: AnalysisRunSummary[];
  recent_comparisons: {
    id: string;
    baseline_policy_change_id: string;
    proposed_policy_change_id: string;
    difference_count: number;
    created_at: string;
  }[];
}

export interface PolicyComparison {
  id: string;
  organization_id: string;
  baseline: {
    policy_change_id: string;
    title: string;
    version: string;
    effective_date: string;
    accepted_extraction_attempt_id: string;
  };
  proposed: {
    policy_change_id: string;
    title: string;
    version: string;
    effective_date: string;
    accepted_extraction_attempt_id: string;
  };
  comparison_contract_version: string;
  comparison_fingerprint: string;
  difference_count: number;
  differences: {
    id: string;
    sequence: number;
    rule_identity: string;
    field_path: string;
    change_type: "added" | "removed" | "modified";
    baseline_value: unknown | null;
    proposed_value: unknown | null;
    material: true;
    reason_code: string;
    baseline_provenance: Record<string, unknown> | null;
    proposed_provenance: Record<string, unknown> | null;
  }[];
  impact_delta: {
    id: string;
    baseline_assessment_id: string;
    proposed_assessment_id: string;
    impact_delta_contract_version: "enterprise-impact-delta-v1";
    impact_delta_fingerprint: string;
    summary: {
      workers_became_affected: number;
      workers_no_longer_affected: number;
      workers_remained_affected: number;
      findings_introduced: number;
      findings_disappeared: number;
      enterprise_impacts_introduced: number;
      enterprise_impacts_removed: number;
    };
    worker_deltas: WorkerImpactDelta[];
    finding_deltas: FindingImpactDelta[];
    enterprise_impact_deltas: EnterpriseImpactDelta[];
    created_by: string;
    created_at: string;
  } | null;
  created_by: string;
  created_at: string;
}

export interface ImpactDeltaEvidence {
  record_id: string;
  evidence_key: string;
  evidence_type: string;
  source_type: string;
  source_id: string;
  label: string;
  snapshot: Record<string, unknown>;
}

export interface WorkerImpactDeltaSide {
  worker_id: string;
  display_name: string;
  trip_id: string;
  classification: "affected" | "unaffected";
  explanation: string;
  reason_codes: string[];
  evidence: ImpactDeltaEvidence[];
}

export interface WorkerImpactDelta {
  id: string;
  sequence: number;
  stable_identity: string;
  change_type: "became_affected" | "no_longer_affected" | "remained_affected";
  delta_reason_code: string;
  baseline_record_id: string | null;
  proposed_record_id: string | null;
  baseline: WorkerImpactDeltaSide | null;
  proposed: WorkerImpactDeltaSide | null;
}

export interface FindingImpactDeltaSide {
  worker_id: string;
  trip_id: string;
  finding_type: string;
  severity: string;
  rule_code: string;
  explanation: string;
  evidence: ImpactDeltaEvidence[];
}

export interface FindingImpactDelta {
  id: string;
  sequence: number;
  stable_identity: string;
  change_type: "introduced" | "disappeared";
  delta_reason_code: string;
  baseline_record_id: string | null;
  proposed_record_id: string | null;
  baseline: FindingImpactDeltaSide | null;
  proposed: FindingImpactDeltaSide | null;
}

export interface EnterpriseImpactDeltaSide {
  domain: string;
  object_type: string;
  source_key: string;
  display_name: string;
  classification: string;
  explanation: string;
  reason_code: string;
  evidence: ImpactDeltaEvidence[];
  relationship_path: {
    sequence: number;
    object_type: string;
    stable_key: string;
    display_label: string;
    relationship_to_next: string | null;
  }[];
}

export interface EnterpriseImpactDelta {
  id: string;
  sequence: number;
  stable_identity: string;
  change_type: "introduced" | "removed";
  delta_reason_code: string;
  baseline_record_id: string | null;
  proposed_record_id: string | null;
  baseline: EnterpriseImpactDeltaSide | null;
  proposed: EnterpriseImpactDeltaSide | null;
}

export interface AnalysisClarification {
  id: string;
  question_code: string;
  question_text: string;
  expected_answer_contract: {
    type?: string;
    allowed_values?: unknown[];
  };
  affected_fields: string[];
  status: "pending" | "answered" | "superseded";
  answer: Record<string, unknown> | null;
  responder_identity: string | null;
  answer_provenance: Record<string, unknown> | null;
  created_at: string;
  answered_at: string | null;
}

export interface AnalysisRun {
  id: string;
  organization_id: string;
  policy_change_id: string;
  status:
    | "pending"
    | "running"
    | "awaiting_clarification"
    | "completed"
    | "unsupported"
    | "failed";
  current_step: string;
  latest_extraction_attempt_id: string | null;
  assessment_id: string | null;
  retry_count: number;
  failure_code: string | null;
  failure_detail: string | null;
  accepted_rule_provenance: Record<string, unknown>[];
  clarifications: AnalysisClarification[];
  metadata: Record<string, string>;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface AnalysisExtraction {
  id: string;
  policy_change_id: string;
  policy_family: string | null;
  support_status: "supported" | "unsupported" | null;
  validation_outcome: "accepted" | "unsupported" | "validation_failed";
  candidate_rules: Record<string, unknown> | null;
  accepted_rules: Record<string, unknown> | null;
  provenance: {
    field_path: string;
    start: number;
    end: number;
    quote: string;
  }[];
  findings: {
    kind?: string;
    code?: string;
    message?: string;
    field_path?: string | null;
    provenance?: { field_path: string; start: number; end: number; quote: string };
  }[];
  validation_errors: { code: string; message: string; field_path: string | null }[];
  metadata: Record<string, string>;
  created_at: string;
}

export interface AnalysisAssessment {
  id: string;
  policy_change_id: string;
  status: "completed";
  analyzer_version: string;
  created_at: string;
  completed_at: string;
  summary: {
    affected_workers: number;
    unaffected_workers: number;
    manager_approvals_required: number;
    training_assignments_required: number;
    enterprise_impacts: number;
    impacts_by_domain: Record<string, number>;
  };
  worker_results: {
    worker: { id: string; name: string };
    trip_id: string;
    classification: "affected" | "unaffected";
    explanation: string;
    reason_codes: string[];
  }[];
  findings: {
    id: string;
    type: string;
    severity: string;
    rule_code: string;
    worker_id: string;
    explanation: string;
    evidence_ids: string[];
  }[];
  evidence: {
    id: string;
    type: string;
    source_type: string;
    source_id: string;
    label: string;
    snapshot: Record<string, unknown>;
  }[];
  enterprise_impacts: Record<
    string,
    {
      id: string;
      domain: string;
      object_type: string;
      source_key: string;
      display_name: string;
      classification: string;
      explanation: string;
      reason_code: string;
      evidence_ids: string[];
      relationship_path: {
        sequence: number;
        object_type: string;
        stable_key: string;
        display_label: string;
        relationship_to_next: string | null;
      }[];
      proposed_action_ids: string[];
      sort_key: string;
    }[]
  >;
  proposed_actions: {
    id: string;
    type: string;
    worker_id: string | null;
    enterprise_impact_id: string | null;
    target: { type: string; identifier: string };
    description: string;
    due_date: string | null;
    execution_status: "not_executed";
  }[];
}

export interface EnterpriseCoverageDomain {
  domain: "systems" | "documents" | "teams" | "customer_commitments";
  considered: number;
  affected: number;
  cleared: number;
  objects: {
    id: string;
    display_name: string;
    classification: "affected" | "cleared";
    impact_ids: string[];
  }[];
}

export interface ChangePlan {
  id: string;
  policy_analysis_run_id: string;
  impact_assessment_id: string;
  interpretation_attempt_id: string;
  schema_version: string;
  created_at: string;
  change_plan: {
    schema_version: string;
    summary: string;
    coverage_gaps: {
      finding_key: string;
      title: string;
      observed_limitation: string;
      why_it_matters: string;
      recommended_review_action: string;
      conclusion_type: "review_concern";
      policy_spans: {
        policy_change_id: string;
        start: number;
        end: number;
        quote: string;
      }[];
      impact_references: { assessment_id: string; impact_id: string }[];
      evidence_references: {
        assessment_id: string;
        evidence_key: string;
        impact_id: string | null;
        finding_id: string | null;
      }[];
      relationship_path_references: {
        assessment_id: string;
        impact_id: string;
        sequence: number;
      }[];
    }[];
  };
}

export interface PolicyAnalysisJourney {
  policy: AnalysisPolicy;
  run: AnalysisRun;
  extraction: AnalysisExtraction | null;
  uncertainty: {
    extraction_findings: AnalysisExtraction["findings"];
    clarifications: AnalysisClarification[];
    legacy_assessment_questions: "omitted_schema_v1_fixture";
  };
  assessment: AnalysisAssessment | null;
  enterprise_coverage: EnterpriseCoverageDomain[];
  interpretation: {
    status: "not_available" | "not_created" | "available" | "failed";
    failure_code: string | null;
    change_plan: ChangePlan | null;
    resolved_references: {
      finding_key: string;
      impacts: {
        impact_id: string;
        display_name: string;
        domain: string;
        classification: string;
        reason_code: string;
      }[];
      evidence: {
        evidence_key: string;
        label: string;
        evidence_type: string;
        source_type: string;
        source_id: string;
      }[];
      policy_spans: {
        policy_change_id: string;
        start: number;
        end: number;
        quote: string;
        validated_against_policy_snapshot: true;
      }[];
    }[];
  };
  approval_run: { id: string; status: string } | null;
  execution: {
    status: "unavailable" | "eligible" | "command_prepared" | "executed" | "failed";
    command_count: number;
    executed_command_count: number;
    result_count: number;
    replay_count: number;
  };
}
