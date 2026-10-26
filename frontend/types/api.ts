export interface AnalysisSummaryItem {
  id: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled" | string;
  overall_score: number | null;
  created_at: string;
  resume_id: string | null;
  resume_version_id: string | null;
  resume_title: string | null;
  job_description_id: string | null;
  job_title: string | null;
}

export interface CategoryScoreDetail {
  raw_score: number;
  weight: number;
  weighted_score: number;
  dimension_name: string;
  benchmark_target: number;
  gap: number;
}

export interface RiskIndicator {
  risk_type: string;
  severity: "low" | "medium" | "high" | "critical" | string;
  description: string;
  suggested_remedy: string;
}

export interface ScorePenaltyDetail {
  penalty_name: string;
  deduction: number;
  reason: string;
  offending_items: string[];
}

export interface ScoreReason {
  factor_name?: string;
  category?: string;
  impact: string;
  description?: string;
  explanation?: string;
  recommendation?: string | null;
  requirement_id?: string | null;
  evidence_id?: string | null;
}

export interface RecommendationDetail {
  id: string;
  agent_name: string;
  category: string;
  title: string;
  description: string;
  priority: string;
  requirement_id?: string | null;
  evidence_ids: string[];
  suggested_action: string;
}

export interface EvidenceTraceItem {
  evidence_id?: string | null;
  matched_claim: string;
  source_document: string | null;
  source_location: string | null;
  confidence: number;
  relationship_type?: string | null;
}

export interface RequirementTraceItem {
  requirement_id?: string | null;
  requirement_text: string;
  kind: "mandatory" | "preferred" | "nice_to_have" | "contextual" | string;
  matched_terms: string[];
  missing_terms: string[];
  status: "matched" | "partial" | "missing" | string;
  match_confidence: number;
  support_level: string;
  source_evidence_ids: string[];
}

export interface BaselineReportResponse {
  analysis_id: string;
  owner_id: string;
  resume_version_id: string;
  job_description_id: string;
  created_at: string;
  status: string;
  score_name: string;
  calculation_version: string;
  overall_score: number;
  overall_score_normalized: number;
  raw_weighted_score: number;
  total_penalty: number;
  category_scores: Record<string, CategoryScoreDetail>;
  strengths: string[];
  weaknesses: string[];
  mandatory_skill_gaps: string[];
  preferred_skill_gaps: string[];
  ats_risks: RiskIndicator[];
  unsupported_claims: string[];
  evidence_confidence: number;
  recommendations: RecommendationDetail[];
  evidence_references: EvidenceTraceItem[];
  requirement_coverage: RequirementTraceItem[];
  penalties: ScorePenaltyDetail[];
  reasons: ScoreReason[];
  traceability_map: Record<string, string[]>;
}

export interface RecommendationsResponse {
  analysis_id: string;
  total_recommendations: number;
  recommendations: RecommendationDetail[];
}

export interface ScoreBreakdownResponse {
  analysis_id: string;
  score_name: string;
  calculation_version: string;
  overall_score: number;
  overall_score_normalized: number;
  raw_weighted_score: number;
  total_penalty: number;
  category_scores: Record<string, CategoryScoreDetail>;
  penalties: ScorePenaltyDetail[];
  reasons: ScoreReason[];
}

export interface AgentRunRecord {
  id: string;
  analysis_id: string;
  request_id?: string | null;
  agent_name: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled" | string;
  start_time?: string | null;
  end_time?: string | null;
  duration_ms: number | null;
  retry_count: number;
  retrieval_count?: number;
  model_calls?: number;
  token_usage?: Record<string, any> | null;
  error?: string | null;
  recovery_status?: string | null;
  final_score?: number | null;
  created_at: string;
  output: any;
}

export interface AgentRunsResponse {
  analysis_id: string;
  total_runs: number;
  agent_runs: AgentRunRecord[];
}

export interface RequirementsCoverageResponse {
  analysis_id: string;
  total_requirements: number;
  matched_count: number;
  missing_count: number;
  requirements: RequirementTraceItem[];
}

export interface EvidenceTraceResponse {
  analysis_id: string;
  total_evidence_items: number;
  evidence_confidence_score: number;
  unsupported_claims: string[];
  evidence_items: EvidenceTraceItem[];
}

export interface CopilotCitation {
  id?: string | null;
  text: string;
  source: string;
  confidence: number;
  support_status: string;
}

export interface CopilotChatResponse {
  response: string;
  citations: CopilotCitation[];
  support_label: string;
  suggested_actions: string[];
}

export interface ResumeSummaryItem {
  id: string;
  title: string;
  created_at: string;
  versions_count: number;
  latest_version_id: string | null;
  latest_version_number: number | null;
  is_final: boolean;
}

export interface ResumeVersionSummaryItem {
  id: string;
  resume_id: string;
  version_number: number;
  is_final: boolean;
  source_uri: string | null;
  created_at: string;
  content_preview: string | null;
}

export interface ResumeContactBlock {
  name: string;
  email: string;
  phone?: string | null;
  location?: string | null;
  linkedin?: string | null;
  github?: string | null;
  portfolio?: string | null;
}

export interface ResumeItemBlock {
  title?: string | null;
  organization?: string | null;
  date_range?: string | null;
  location?: string | null;
  bullets: string[];
  raw_text?: string | null;
}

export interface ResumeSectionBlock {
  section_key: string;
  heading: string;
  items: ResumeItemBlock[];
}

export interface ResumeRenderConfig {
  font_family: string;
  font_size_pt: number;
  heading_size_pt: number;
  margins_inch: number;
  line_spacing: number;
  section_order: string[];
  show_dividers: boolean;
}

export interface DeterministicResumeDocument {
  resume_version_id?: string | null;
  header: ResumeContactBlock;
  sections: ResumeSectionBlock[];
  config: ResumeRenderConfig;
}

export interface ResumeValidationResult {
  is_valid: boolean;
  issues: string[];
  validated_rules: string[];
}

export interface IngestionResponse {
  id: string;
  source: string;
  item_count: number;
  items: any[];
}

export interface JobDescriptionResponse {
  id: string;
  title: string;
  source: string;
  requirement_count: number;
  seniority_indicators: string[];
  keywords: any[];
  requirements: any[];
  years_of_experience?: number | null;
  mandatory_skills: any[];
  preferred_skills: any[];
  nice_to_have_skills: any[];
  responsibilities: string[];
  education_requirements: string[];
  certifications: string[];
  domain_knowledge: string[];
  tooling: any[];
  soft_skills: string[];
  implied_requirements: string[];
}

export interface ExternalSourceResponse {
  id: string;
  source_type: string;
  uri: string;
  item_count: number;
}


// ----------------------------------------------------
// Closed-Loop Multi-Agent Optimization
// ----------------------------------------------------
export interface ProposedChangeItem {
  change_id: string;
  section: string;
  change_type: string;
  before_text: string;
  after_text: string;
  reason: string;
  evidence_ids: string[];
  risk_level: "low" | "medium" | "high" | string;
  support_status: "SUPPORTED" | "PARTIALLY_SUPPORTED" | "UNSUPPORTED" | string;
  target_requirement_ids?: string[];
}

export interface OptimizationIterationRecord {
  iteration_number: number;
  score: number;
  score_delta: number;
  changes: ProposedChangeItem[];
  accepted_changes: ProposedChangeItem[];
  rejected_changes: ProposedChangeItem[];
  validation_issues: string[];
  evidence_used: string[];
  timestamp: string;
}

export interface ClosedLoopOptimizationResponse {
  analysis_id: string;
  total_iterations: number;
  baseline_score: number;
  final_score: number;
  score: number;
  overall_delta: number;
  score_delta: number;
  improved: boolean;
  before_score: number;
  after_score: number;
  delta: number;
  remaining_gaps: string[];
  new_risks: string[];
  optimized_resume_text: string;
  optimized_version_id?: string | null;
  iterations: OptimizationIterationRecord[];
  status?: string;
}
