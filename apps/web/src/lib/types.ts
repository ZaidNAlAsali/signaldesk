export type Priority = "critical" | "high" | "medium" | "low";
export type CaseStatus = "new" | "analyzed" | "approved" | "overridden" | "rejected";
export type Category = "incident" | "access" | "procurement" | "compliance" | "service" | "other";

export interface Citation {
  policy_slug: string;
  policy_title: string;
  excerpt: string;
  score: number;
}

export interface Redaction {
  kind: string;
  placeholder: string;
}

export interface Analysis {
  id: string;
  case_id: string;
  provider: string;
  summary: string;
  category: Category;
  priority: Priority;
  risk_score: number;
  confidence: number;
  rationale: string;
  recommended_action: string;
  citations: Citation[];
  redactions: Redaction[];
  created_at: string;
}

export interface OpsCase {
  id: string;
  reference: string;
  title: string;
  description: string;
  requester: string;
  language: "en" | "ar";
  category: Category | null;
  priority: Priority | null;
  status: CaseStatus;
  created_at: string;
  updated_at: string;
  latest_analysis: Analysis | null;
}

export interface Analytics {
  total: number;
  by_status: Record<string, number>;
  by_priority: Record<string, number>;
  by_category: Record<string, number>;
  high_risk_open: number;
  average_confidence: number;
}

export interface AuditEvent {
  id: string;
  case_id: string;
  sequence: number;
  event_type: string;
  actor: string;
  payload: Record<string, unknown>;
  previous_hash: string;
  event_hash: string;
  created_at: string;
}

export interface AuditVerification {
  valid: boolean;
  event_count: number;
  first_invalid_event_id: string | null;
}

export interface NewCaseInput {
  title: string;
  description: string;
  requester: string;
  language: "en" | "ar";
}

export interface DecisionInput {
  action: "approve" | "override" | "reject";
  actor: string;
  note: string;
  category?: Category;
  priority?: Priority;
}
