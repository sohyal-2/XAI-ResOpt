import type { AuthResponse, User } from "@/types/auth";
import type {
  AgentRunsResponse,
  AnalysisSummaryItem,
  BaselineReportResponse,
  CopilotChatResponse,
  DeterministicResumeDocument,
  EvidenceTraceResponse,
  ExternalSourceResponse,
  IngestionResponse,
  JobDescriptionResponse,
  RecommendationsResponse,
  RequirementsCoverageResponse,
  ResumeSummaryItem,
  ResumeValidationResult,
  ResumeVersionSummaryItem,
  ScoreBreakdownResponse,
  ClosedLoopOptimizationResponse,
  OptimizationIterationRecord,
  ProposedChangeItem,
} from "@/types/api";
import type { ReviewSessionResponse } from "@/features/review/types";

export type DependencyState = "ok" | "error";

export interface HealthResponse {
  status: "ok" | "degraded";
  database: DependencyState;
  redis: DependencyState;
  details?: Record<string, string> | null;
}

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getHeaders(token?: string | null): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  const activeToken = token || (typeof window !== "undefined" ? sessionStorage.getItem("xai-resopt.access-token") || localStorage.getItem("access_token") : null);
  if (activeToken) {
    headers["Authorization"] = `Bearer ${activeToken}`;
  }
  return headers;
}

async function parseResponse<T>(response: Response): Promise<T> {
  let body: any;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    let errorDetail: string | undefined;
    if (body && typeof body === "object") {
      if (typeof body.detail === "string") {
        errorDetail = body.detail;
      } else if (Array.isArray(body.detail)) {
        // FastAPI / Pydantic validation errors
        errorDetail = body.detail
          .map((item: any) => (item && typeof item.msg === "string" ? item.msg : JSON.stringify(item)))
          .join("; ");
      } else if (typeof body.message === "string") {
        errorDetail = body.message;
      }
    }
    throw new Error(errorDetail || `Request failed with status ${response.status}`);
  }

  return body as T;
}

// ----------------------------------------------------
// Health & System
// ----------------------------------------------------
export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${apiUrl}/api/health`, { cache: "no-store" });
  return parseResponse<HealthResponse>(response);
}

// ----------------------------------------------------
// Authentication
// ----------------------------------------------------
export async function signup(email: string, fullName: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${apiUrl}/api/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, full_name: fullName, password }),
  });
  return parseResponse<AuthResponse>(response);
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${apiUrl}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return parseResponse<AuthResponse>(response);
}

export async function logout(token: string): Promise<void> {
  const response = await fetch(`${apiUrl}/api/auth/logout`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok && response.status !== 401) throw new Error(`Request failed with status ${response.status}`);
}

export async function fetchCurrentUser(token: string): Promise<User> {
  const response = await fetch(`${apiUrl}/api/me`, { headers: { Authorization: `Bearer ${token}` } });
  return parseResponse<User>(response);
}

// ----------------------------------------------------
// Document Ingestion
// ----------------------------------------------------
export async function ingestResume(file: File, token?: string | null): Promise<IngestionResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const activeToken = token || (typeof window !== "undefined" ? sessionStorage.getItem("xai-resopt.access-token") : null);
  const response = await fetch(`${apiUrl}/api/ingestion/resumes`, {
    method: "POST",
    headers: activeToken ? { Authorization: `Bearer ${activeToken}` } : {},
    body: formData,
  });
  return parseResponse<IngestionResponse>(response);
}

export async function ingestJobDescription(
  data: { text?: string; title?: string; url?: string; file?: File },
  token?: string | null
): Promise<JobDescriptionResponse> {
  const formData = new FormData();
  if (data.text) formData.append("text", data.text);
  if (data.title) formData.append("title", data.title);
  if (data.url) formData.append("url", data.url);
  if (data.file) formData.append("file", data.file);

  const activeToken = token || (typeof window !== "undefined" ? sessionStorage.getItem("xai-resopt.access-token") : null);
  const response = await fetch(`${apiUrl}/api/ingestion/job-descriptions`, {
    method: "POST",
    headers: activeToken ? { Authorization: `Bearer ${activeToken}` } : {},
    body: formData,
  });
  return parseResponse<JobDescriptionResponse>(response);
}

export async function ingestExternalSource(
  url: string,
  sourceType: "github" | "portfolio",
  token?: string | null
): Promise<ExternalSourceResponse> {
  const formData = new FormData();
  formData.append("url", url);
  formData.append("source_type", sourceType);

  const activeToken = token || (typeof window !== "undefined" ? sessionStorage.getItem("xai-resopt.access-token") : null);
  const response = await fetch(`${apiUrl}/api/ingestion/external`, {
    method: "POST",
    headers: activeToken ? { Authorization: `Bearer ${activeToken}` } : {},
    body: formData,
  });
  return parseResponse<ExternalSourceResponse>(response);
}

// ----------------------------------------------------
// Analyses
// ----------------------------------------------------
export async function fetchAnalyses(token?: string | null): Promise<AnalysisSummaryItem[]> {
  const response = await fetch(`${apiUrl}/api/analysis`, {
    headers: getHeaders(token),
    cache: "no-store",
  });
  return parseResponse<AnalysisSummaryItem[]>(response);
}

export async function fetchAnalysisSummary(analysisId: string, token?: string | null): Promise<AnalysisSummaryItem> {
  const response = await fetch(`${apiUrl}/api/analysis/${analysisId}/summary`, {
    headers: getHeaders(token),
    cache: "no-store",
  });
  return parseResponse<AnalysisSummaryItem>(response);
}

export async function triggerBaselineAnalysis(
  payload: { resume_id?: string; resume_version_id?: string; job_description_id?: string },
  token?: string | null
): Promise<BaselineReportResponse> {
  const response = await fetch(`${apiUrl}/api/analysis/baseline`, {
    method: "POST",
    headers: getHeaders(token),
    body: JSON.stringify(payload),
  });
  return parseResponse<BaselineReportResponse>(response);
}

export async function deleteAnalysis(analysisId: string, token?: string | null): Promise<void> {
  const response = await fetch(`${apiUrl}/api/analysis/${analysisId}`, {
    method: "DELETE",
    headers: getHeaders(token),
  });
  if (!response.ok && response.status !== 204) {
    throw new Error(`Failed to delete analysis: ${response.status}`);
  }
}

export async function fetchBaselineReport(analysisId: string, token?: string | null): Promise<BaselineReportResponse> {
  const response = await fetch(`${apiUrl}/api/analysis/${analysisId}/baseline`, {
    headers: getHeaders(token),
    cache: "no-store",
  });
  return parseResponse<BaselineReportResponse>(response);
}

export async function fetchScoreBreakdown(analysisId: string, token?: string | null): Promise<ScoreBreakdownResponse> {
  const response = await fetch(`${apiUrl}/api/analysis/${analysisId}/score`, {
    headers: getHeaders(token),
    cache: "no-store",
  });
  return parseResponse<ScoreBreakdownResponse>(response);
}

export async function fetchAgentRuns(analysisId: string, token?: string | null): Promise<AgentRunsResponse> {
  const response = await fetch(`${apiUrl}/api/analysis/${analysisId}/agent-runs`, {
    headers: getHeaders(token),
    cache: "no-store",
  });
  return parseResponse<AgentRunsResponse>(response);
}

export async function fetchRecommendations(analysisId: string, token?: string | null): Promise<RecommendationsResponse> {
  const response = await fetch(`${apiUrl}/api/analysis/${analysisId}/recommendations`, {
    headers: getHeaders(token),
    cache: "no-store",
  });
  return parseResponse<RecommendationsResponse>(response);
}

export async function fetchRequirementsCoverage(analysisId: string, token?: string | null): Promise<RequirementsCoverageResponse> {
  const response = await fetch(`${apiUrl}/api/analysis/${analysisId}/requirements`, {
    headers: getHeaders(token),
    cache: "no-store",
  });
  return parseResponse<RequirementsCoverageResponse>(response);
}

export async function fetchEvidenceTrace(analysisId: string, token?: string | null): Promise<EvidenceTraceResponse> {
  const response = await fetch(`${apiUrl}/api/analysis/${analysisId}/evidence`, {
    headers: getHeaders(token),
    cache: "no-store",
  });
  return parseResponse<EvidenceTraceResponse>(response);
}

export async function triggerOptimization(
  analysisId: string,
  token?: string | null
): Promise<ClosedLoopOptimizationResponse> {
  const response = await fetch(`${apiUrl}/api/analysis/${analysisId}/optimize`, {
    method: "POST",
    headers: getHeaders(token),
    body: JSON.stringify({}),
  });
  return parseResponse<ClosedLoopOptimizationResponse>(response);
}

export async function fetchOptimizationHistory(
  analysisId: string,
  token?: string | null
): Promise<OptimizationIterationRecord[]> {
  const response = await fetch(`${apiUrl}/api/analysis/${analysisId}/optimizations`, {
    headers: getHeaders(token),
    cache: "no-store",
  });
  return parseResponse<OptimizationIterationRecord[]>(response);
}

export async function fetchLatestOptimization(
  analysisId: string,
  token?: string | null
): Promise<ClosedLoopOptimizationResponse> {
  const response = await fetch(`${apiUrl}/api/analysis/${analysisId}/optimizations/latest`, {
    headers: getHeaders(token),
    cache: "no-store",
  });
  return parseResponse<ClosedLoopOptimizationResponse>(response);
}

export async function sendCopilotQuery(
  analysisId: string,
  message: string,
  token?: string | null
): Promise<CopilotChatResponse> {
  const response = await fetch(`${apiUrl}/api/analysis/${analysisId}/chat`, {
    method: "POST",
    headers: getHeaders(token),
    body: JSON.stringify({ message }),
  });
  return parseResponse<CopilotChatResponse>(response);
}

// ----------------------------------------------------
// Human Review
// ----------------------------------------------------
export async function fetchReviewSession(analysisId: string, token?: string | null): Promise<ReviewSessionResponse> {
  const response = await fetch(`${apiUrl}/api/analysis/${analysisId}/review`, {
    headers: getHeaders(token),
    cache: "no-store",
  });
  return parseResponse<ReviewSessionResponse>(response);
}

export async function submitReviewDecisions(
  analysisId: string,
  decisions: Array<{ change_id: string; action: string; manual_text?: string }>,
  token?: string | null
): Promise<ReviewSessionResponse> {
  const response = await fetch(`${apiUrl}/api/analysis/${analysisId}/review/decisions`, {
    method: "POST",
    headers: getHeaders(token),
    body: JSON.stringify({ decisions }),
  });
  return parseResponse<ReviewSessionResponse>(response);
}

export async function acceptAllSafeChanges(analysisId: string, token?: string | null): Promise<ReviewSessionResponse> {
  const response = await fetch(`${apiUrl}/api/analysis/${analysisId}/review/accept-all-safe`, {
    method: "POST",
    headers: getHeaders(token),
  });
  return parseResponse<ReviewSessionResponse>(response);
}

export async function reRunReviewOptimization(analysisId: string, token?: string | null): Promise<any> {
  const response = await fetch(`${apiUrl}/api/analysis/${analysisId}/review/re-optimize`, {
    method: "POST",
    headers: getHeaders(token),
  });
  return parseResponse<any>(response);
}

export async function finalizeHumanReview(
  analysisId: string,
  forceUnresolved: boolean = false,
  notes?: string,
  token?: string | null
): Promise<any> {
  const response = await fetch(`${apiUrl}/api/analysis/${analysisId}/review/finalize`, {
    method: "POST",
    headers: getHeaders(token),
    body: JSON.stringify({ force_unresolved_claims: forceUnresolved, notes }),
  });
  return parseResponse<any>(response);
}

// ----------------------------------------------------
// Resumes & Rendering
// ----------------------------------------------------
export async function fetchResumes(token?: string | null): Promise<ResumeSummaryItem[]> {
  const response = await fetch(`${apiUrl}/api/resumes`, {
    headers: getHeaders(token),
    cache: "no-store",
  });
  return parseResponse<ResumeSummaryItem[]>(response);
}

export async function fetchResumeVersions(resumeId: string, token?: string | null): Promise<ResumeVersionSummaryItem[]> {
  const response = await fetch(`${apiUrl}/api/resumes/${resumeId}/versions`, {
    headers: getHeaders(token),
    cache: "no-store",
  });
  return parseResponse<ResumeVersionSummaryItem[]>(response);
}

export async function validateResumeVersion(versionId: string, token?: string | null): Promise<ResumeValidationResult> {
  const response = await fetch(`${apiUrl}/api/resumes/versions/${versionId}/validate`, {
    headers: getHeaders(token),
    cache: "no-store",
  });
  return parseResponse<ResumeValidationResult>(response);
}

export async function previewResumeVersion(
  versionId: string,
  font: string = "Helvetica",
  margins: number = 0.6,
  token?: string | null
): Promise<DeterministicResumeDocument> {
  const response = await fetch(
    `${apiUrl}/api/resumes/versions/${versionId}/preview?font_family=${encodeURIComponent(font)}&margins_inch=${margins}`,
    {
      headers: getHeaders(token),
      cache: "no-store",
    }
  );
  return parseResponse<DeterministicResumeDocument>(response);
}

export function getActiveToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem("xai-resopt.access-token") || localStorage.getItem("access_token");
}

export function getResumePdfExportUrl(
  versionId: string,
  font: string = "Helvetica",
  margins: number = 0.6,
  token?: string | null
): string {
  const activeToken = token || getActiveToken();
  const tokenParam = activeToken ? `&token=${encodeURIComponent(activeToken)}` : "";
  return `${apiUrl}/api/resumes/versions/${versionId}/export/pdf?font_family=${encodeURIComponent(font)}&margins_inch=${margins}${tokenParam}`;
}

export function getResumeDocxExportUrl(
  versionId: string,
  font: string = "Helvetica",
  margins: number = 0.6,
  token?: string | null
): string {
  const activeToken = token || getActiveToken();
  const tokenParam = activeToken ? `&token=${encodeURIComponent(activeToken)}` : "";
  return `${apiUrl}/api/resumes/versions/${versionId}/export/docx?font_family=${encodeURIComponent(font)}&margins_inch=${margins}${tokenParam}`;
}

export async function downloadResumePdf(
  versionId: string,
  filename: string = "Resume.pdf",
  font: string = "Helvetica",
  margins: number = 0.6,
  token?: string | null
): Promise<void> {
  const activeToken = token || getActiveToken();
  const url = `${apiUrl}/api/resumes/versions/${versionId}/export/pdf?font_family=${encodeURIComponent(font)}&margins_inch=${margins}`;
  const response = await fetch(url, {
    headers: getHeaders(activeToken),
  });
  if (!response.ok) {
    let errorDetail = `Export failed with status ${response.status}`;
    try {
      const err = await response.json();
      if (err?.detail) {
        errorDetail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
      }
    } catch {}
    throw new Error(errorDetail);
  }
  const blob = await response.blob();
  const blobUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(blobUrl);
}

export async function downloadResumeDocx(
  versionId: string,
  filename: string = "Resume.docx",
  font: string = "Helvetica",
  margins: number = 0.6,
  token?: string | null
): Promise<void> {
  const activeToken = token || getActiveToken();
  const url = `${apiUrl}/api/resumes/versions/${versionId}/export/docx?font_family=${encodeURIComponent(font)}&margins_inch=${margins}`;
  const response = await fetch(url, {
    headers: getHeaders(activeToken),
  });
  if (!response.ok) {
    let errorDetail = `Export failed with status ${response.status}`;
    try {
      const err = await response.json();
      if (err?.detail) {
        errorDetail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
      }
    } catch {}
    throw new Error(errorDetail);
  }
  const blob = await response.blob();
  const blobUrl = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = blobUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(blobUrl);
}

// ----------------------------------------------------
// Evidence & Claims
// ----------------------------------------------------
export async function fetchGlobalEvidence(limit: number = 50, token?: string | null): Promise<any[]> {
  const response = await fetch(`${apiUrl}/api/evidence?limit=${limit}`, {
    headers: getHeaders(token),
    cache: "no-store",
  });
  return parseResponse<any[]>(response);
}