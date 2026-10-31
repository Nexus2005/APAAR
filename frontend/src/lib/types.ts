export type Role =
  | "institution_operator"
  | "institution_admin"
  | "central_reviewer"
  | "verifier"
  | "student"
  | "sysadmin";

export interface InstitutionRef {
  id: number;
  code: string;
  name: string;
  short_name: string;
  state: string;
}

export interface User {
  id: number;
  email: string;
  name: string;
  role: Role;
  institution: InstitutionRef | null;
  person_id: number | null;
}

export interface MeResponse {
  user: User;
  csrf_token: string;
  demo_mode: boolean;
  demo_accounts: { email: string; label: string; role: Role }[];
  simulated: boolean;
}

export interface IntakeRow {
  programme_id: number;
  programme_code: string;
  programme_name: string;
  level: string;
  academic_year: string;
  approved_intake: number;
  regular_admitted: number;
  seat_categories: Record<string, number>;
  headroom: number;
  utilisation_pct: number;
  status: "green" | "amber" | "red" | "unconfigured";
}

export interface FindingSummary {
  id: number;
  ref: string;
  rule_code: string;
  severity: "blocker" | "warning" | "risk" | "info";
  title: string;
  what_checks: string;
  why_matters: string;
  institution_id: number;
  institution_name?: string | null;
  institution_code?: string | null;
  enrolment_id: number | null;
  evidence: Record<string, unknown>;
  explanation: string;
  recommended_action: string;
  policy_assumption: string | null;
  status: "open" | "in_review" | "resolved" | "dismissed" | "escalated";
  created_at: string;
  updated_at: string;
  history?: FindingHistory[];
  allowed_actions?: string[];
}

export interface FindingHistory {
  action: string;
  label: string;
  comment: string;
  actor: string;
  at: string;
}

export interface UploadBatch {
  id: number;
  ref: string;
  filename: string;
  status: string;
  uploaded_at: string;
  total_rows: number;
  accepted_rows: number;
  rejected_rows: number;
  findings_raised: number;
  mapping: Record<string, unknown>;
}

export interface InstitutionDashboard {
  institution: {
    id: number;
    aicte_code: string;
    name: string;
    short_name: string;
    state: string;
    region: string;
    city: string;
  };
  kpis: {
    total_admitted: number;
    open_findings: number;
    severity_counts: Record<string, number>;
    apaar_readiness_pct: number;
    apaar_linked: number;
    apaar_pending_declined: number;
    apaar_missing: number;
    seats_left: number;
    approved_intake: number;
    regular_admitted: number;
    utilisation_pct: number;
  };
  intake: IntakeRow[];
  uploads: {
    id: number;
    ref: string;
    filename: string;
    uploaded_at: string;
    total_rows: number;
    accepted_rows: number;
    rejected_rows: number;
    pending_lane_rows: number;
    status: string;
  }[];
  findings: FindingSummary[];
  trend: { month: string; admitted: number }[];
  assumptions: {
    policy_version: number;
    seat_caps: Record<string, { cap_pct_of_approved: number | null; status: string }>;
  };
  simulated: boolean;
}

export interface CentralInstitutionRow {
  institution_id: number;
  code: string;
  name: string;
  short_name: string;
  state: string;
  region: string;
  enrolments: number;
  open_findings: number;
  risk_findings: number;
  approved_intake: number;
  regular_admitted: number;
  utilisation_pct: number;
  readiness_pct: number;
  anomaly_score: number | null;
  anomaly_rank: number | null;
  anomaly_flagged: boolean;
}

export interface Anomaly {
  institution_id: number;
  institution_code: string;
  institution_name: string;
  state: string;
  score: number;
  rank: number;
  flagged: boolean;
  features: Record<string, number>;
  peer_medians: Record<string, number>;
  reasons: string[];
  method: string;
}

export interface CentralDashboard {
  kpis: {
    institutions: number;
    enrolments: number;
    programmes_over_intake: number;
    open_risk_findings: number;
    escalated: number;
    anomalies_flagged: number;
  };
  states: {
    state: string;
    institutions: number;
    enrolments: number;
    approved_intake: number;
    regular_admitted: number;
    utilisation_pct: number;
  }[];
  institutions: CentralInstitutionRow[];
  over_intake: (IntakeRow & { institution_code: string; institution_name: string; state: string })[];
  anomalies: Anomaly[];
  escalations: FindingSummary[];
  policy: {
    version: number;
    effective_from: string;
    seat_caps: Record<string, { label: string; cap_pct_of_approved: number | null; status: string; source: string }>;
  };
  simulated: boolean;
}

export interface DuplicateLink {
  id: number;
  match_type: string;
  score: number;
  whitelisted_reason: string | null;
  a: {
    enrolment_ref: string;
    institution: string;
    institution_code: string;
    programme: string;
    programme_name: string;
    academic_year: string;
    admission_date: string;
    seat_category: string;
    student: string;
    dob: string;
    apaar_masked: string;
    status: string;
  };
  b: DuplicateLink["a"];
  created_at: string;
}

export interface CredentialRow {
  credential_id: string;
  enrolment_ref: string | null;
  student: string | null;
  apaar_masked: string | null;
  status: "valid" | "revoked";
  issued_at: string;
  revoked_at: string | null;
  revoke_reason: string | null;
  institution: string | null;
  verify_path: string;
}

export interface VerifyResult {
  status: "VALID" | "REVOKED" | "TAMPERED" | "NOT_FOUND";
  credential_id: string;
  message: string;
  simulated: boolean;
  credential?: {
    claims?: Record<string, string>;
    issuer?: { name?: string; institution_code?: string };
    issuedAt?: string;
    disclaimers?: string;
    disclaimer?: string;
    subject?: { enrolment_ref?: string };
  };
  issuer_name?: string | null;
  issuer_code?: string | null;
  issued_at?: string;
  revoked_at?: string | null;
  revoke_reason?: string | null;
  signature_valid?: boolean;
}

export interface ConsentRequest {
  id: number;
  verifier_name: string;
  fields: string[];
  purpose: string;
  status: "pending" | "approved" | "denied" | "expired";
  created_at: string;
  decided_at: string | null;
  expires_at: string;
  student_display: string | null;
}

export interface AuditEntry {
  seq: number;
  actor: string;
  action: string;
  resource: string;
  detail: Record<string, unknown>;
  at: string;
  prev_hash: string;
  hash: string;
}

export interface EnrolmentRow {
  id: number;
  enrolment_ref: string;
  student: string;
  apaar_masked: string;
  apaar_status: string;
  programme: string;
  programme_code: string;
  institution: string;
  institution_code: string;
  academic_year: string;
  seat_category: string;
  admission_date: string;
  status: string;
}
