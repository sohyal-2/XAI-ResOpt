export interface EvidenceSummary {
  id: string;
  text: string;
  source_uri?: string;
  location?: string;
  confidence: number;
}

export interface TraceNode {
  recommendation_text?: string;
  change_before: string;
  change_after: string;
  claim_text?: string;
  claim_status?: string;
  evidence_text?: string;
  original_source?: string;
  source_location?: string;
}

export interface ChangeReviewItem {
  change_id: string;
  section: string;
  change_type: string;
  before_text: string;
  after_text: string;
  why_changed: string;
  evidence: EvidenceSummary[];
  evidence_ids: string[];
  confidence: number;
  risk: "low" | "medium" | "high";
  supported_status: "SUPPORTED" | "PARTIALLY_SUPPORTED" | "UNSUPPORTED" | "CONTRADICTED";
  decision: "pending" | "accepted" | "rejected" | "edited";
  manual_text?: string | null;
  is_manual: boolean;
  trace_chain?: TraceNode;
}

export interface ReviewSessionResponse {
  analysis_id: string;
  status: string;
  total_changes: number;
  accepted_count: number;
  rejected_count: number;
  edited_count: number;
  pending_count: number;
  unresolved_unsupported_claims: Array<{
    id: string;
    text: string;
    status: string;
    confidence: number;
  }>;
  unsupported_claims_count: number;
  can_finalize: boolean;
  changes: ChangeReviewItem[];
}

export interface FinalizeReviewResponse {
  analysis_id: string;
  new_resume_version_id: string;
  version_number: number;
  finalized_resume_text: string;
  changes_applied_count: number;
  manual_edits_count: number;
  rejected_count: number;
  trace_summary: Array<{
    change_id: string;
    type: string;
    before: string;
    after?: string;
    is_manual: boolean;
  }>;
}
