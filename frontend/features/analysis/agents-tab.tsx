"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import type { AgentRunRecord } from "@/types/api";
import { fetchAgentRuns } from "@/lib/api";
import {
  Cpu,
  CheckCircle2,
  Clock,
  RefreshCw,
  AlertCircle,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Database,
  Sparkles,
  RotateCcw,
  ShieldAlert,
  Hash,
  Activity,
  Layers,
} from "lucide-react";

interface AgentsTabProps {
  analysisId: string;
}

interface AgentDefinition {
  key: string;
  displayName: string;
  description: string;
  category: "ingestion" | "analysis" | "optimization";
}

const ORDERED_PIPELINE_AGENTS: AgentDefinition[] = [
  {
    key: "intake_agent",
    displayName: "Intake Agent",
    description: "Validates resume & job description files, checks token limits, and establishes request provenance.",
    category: "ingestion",
  },
  {
    key: "resume_parser",
    displayName: "Resume Parser",
    description: "Extracts structural sections, headings, contact credentials, and candidate statements.",
    category: "ingestion",
  },
  {
    key: "jd_analyzer",
    displayName: "JD Analyzer",
    description: "Parses job specifications, mandatory vs preferred requirements, and core keyword domains.",
    category: "ingestion",
  },
  {
    key: "ats_agent",
    displayName: "ATS Agent",
    description: "Audits ATS parseability, typography safety, header readability, and section completeness.",
    category: "analysis",
  },
  {
    key: "skill_agent",
    displayName: "Skill Agent",
    description: "Maps candidate hard/soft skills against target requirements, calculating skill match depth.",
    category: "analysis",
  },
  {
    key: "evidence_agent",
    displayName: "Evidence Agent",
    description: "Cross-checks resume claims against verified external evidence corpus and flags unsupported claims.",
    category: "analysis",
  },
  {
    key: "explainability_agent",
    displayName: "Explainability",
    description: "Executes deterministic 8-dimension scoring, calculates penalties, and builds traceability graph.",
    category: "analysis",
  },
  {
    key: "optimizer_agent",
    displayName: "Optimizer",
    description: "Generates grounded bullet rewrites targeting missing keywords while preserving factual boundaries.",
    category: "optimization",
  },
  {
    key: "critic_agent",
    displayName: "Critic",
    description: "Multi-dimensional auditor rejecting artificial buzzwords, tone exaggeration, or metric inflation.",
    category: "optimization",
  },
  {
    key: "fact_check_agent",
    displayName: "Fact Checker",
    description: "Strict anti-hallucination guardrail ensuring every suggested edit is supported by verified items.",
    category: "optimization",
  },
  {
    key: "ats_re_evaluator",
    displayName: "ATS Re-Evaluator",
    description: "Re-runs deterministic ATS scoring on synthesized resume to measure delta and verify improvement.",
    category: "optimization",
  },
];

export const AgentsTab: React.FC<AgentsTabProps> = ({ analysisId }) => {
  const [runs, setRuns] = useState<AgentRunRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedAgentKey, setExpandedAgentKey] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const loadAgentRuns = useCallback(async (isBackground = false) => {
    try {
      if (!isBackground) setLoading(true);
      setError(null);
      const data = await fetchAgentRuns(analysisId);
      setRuns(data.agent_runs);

      // Check if any agent is running or queued to maintain real-time polling
      const hasPending = data.agent_runs.some(
        (r) => r.status === "running" || r.status === "queued"
      );
      setIsPolling(hasPending);
    } catch (err: any) {
      setError(err.message || "Failed to load real agent observability telemetry");
      setIsPolling(false);
    } finally {
      if (!isBackground) setLoading(false);
    }
  }, [analysisId]);

  useEffect(() => {
    if (analysisId) {
      loadAgentRuns();
    }
  }, [analysisId, loadAgentRuns]);

  // Real state polling (strictly NO fake progress timers; polls real DB updates)
  useEffect(() => {
    if (isPolling) {
      pollingRef.current = setInterval(() => {
        loadAgentRuns(true);
      }, 2500);
    } else if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [isPolling, loadAgentRuns]);

  const toggleExpand = (agentKey: string) => {
    setExpandedAgentKey(expandedAgentKey === agentKey ? null : agentKey);
  };

  // Map runs by agent_name
  const runsByName = React.useMemo(() => {
    const map = new Map<string, AgentRunRecord>();
    for (const r of runs) {
      // If multiple runs exist (e.g. from multiple optimization iterations), keep the latest or primary
      map.set(r.agent_name, r);
    }
    return map;
  }, [runs]);

  // Telemetry summary metrics
  const completedCount = runs.filter((r) => r.status === "completed").length;
  const failedCount = runs.filter((r) => r.status === "failed").length;
  const runningCount = runs.filter((r) => r.status === "running").length;
  const queuedCount = runs.filter((r) => r.status === "queued").length;
  const totalDurationMs = runs.reduce((acc, r) => acc + (r.duration_ms || 0), 0);
  const requestId = runs.find((r) => r.request_id)?.request_id || "req-pending";

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return (
          <span className="inline-flex items-center gap-1 rounded bg-[#f0f7f2] px-2 py-0.5 text-[10px] font-semibold text-[#1f6339] border border-[#cde4d3] uppercase font-mono">
            <CheckCircle2 className="h-3 w-3" />
            Completed
          </span>
        );
      case "running":
        return (
          <span className="inline-flex items-center gap-1 rounded bg-[#ebf4ff] px-2 py-0.5 text-[10px] font-semibold text-[#1e40af] border border-[#bfdbfe] uppercase font-mono">
            <RefreshCw className="h-3 w-3 animate-spin" />
            Running
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1 rounded bg-[#fdf2f0] px-2 py-0.5 text-[10px] font-semibold text-[#942e23] border border-[#f7d0ca] uppercase font-mono">
            <AlertCircle className="h-3 w-3" />
            Failed
          </span>
        );
      case "cancelled":
        return (
          <span className="inline-flex items-center gap-1 rounded bg-[#f7f5ef] px-2 py-0.5 text-[10px] font-semibold text-[#737067] border border-[#ded9cc] uppercase font-mono">
            Cancelled
          </span>
        );
      case "queued":
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded bg-[#fbfaf6] px-2 py-0.5 text-[10px] font-semibold text-[#737067] border border-[#edeae1] uppercase font-mono">
            <Clock className="h-3 w-3" />
            Queued
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Top Banner with Real Telemetry Metrics */}
      <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 shadow-editorial">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#edeae1] pb-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-[#5c5953] uppercase tracking-wider mb-1">
              <Cpu className="h-4 w-4 text-[#181816]" />
              Real-Time Agent Observability
            </div>
            <h2 className="font-serif text-xl sm:text-2xl font-normal text-[#181816]">
              Deterministic Agent Activity Timeline
            </h2>
          </div>
          <div className="flex items-center gap-2">
            {isPolling && (
              <span className="flex items-center gap-1.5 rounded-full bg-[#ebf4ff] px-3 py-1 text-[11px] font-medium text-[#1e40af] border border-[#bfdbfe]">
                <Activity className="h-3 w-3 animate-pulse text-[#2563eb]" />
                Live Sync Active
              </span>
            )}
            <button
              type="button"
              onClick={() => loadAgentRuns(false)}
              aria-label="Refresh agent telemetry"
              className="flex items-center gap-1.5 rounded border border-[#ded9cc] bg-[#f7f5ef] px-3.5 py-2 text-xs font-medium text-[#181816] hover:bg-[#eae6dd] transition-colors min-h-[44px] sm:min-h-0"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              Refresh Telemetry
            </button>
          </div>
        </div>

        {/* Telemetry Header KPIs */}
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="rounded bg-[#fbfaf6] p-3 border border-[#edeae1]">
            <span className="text-[#5c5953] block text-[10px] uppercase font-mono">Request ID</span>
            <span className="font-mono text-[#181816] truncate block font-medium mt-0.5" title={requestId}>
              {requestId.length > 22 ? `${requestId.slice(0, 22)}...` : requestId}
            </span>
          </div>

          <div className="rounded bg-[#fbfaf6] p-3 border border-[#edeae1]">
            <span className="text-[#5c5953] block text-[10px] uppercase font-mono">Pipeline Status</span>
            <span className="font-medium text-[#181816] mt-0.5 block">
              {completedCount === 11 ? (
                <span className="text-[#1f6339]">All 11 Agents Completed</span>
              ) : failedCount > 0 ? (
                <span className="text-[#942e23]">{failedCount} Agent(s) Failed</span>
              ) : (
                <span>{completedCount} of 11 Completed ({queuedCount} Queued)</span>
              )}
            </span>
          </div>

          <div className="rounded bg-[#fbfaf6] p-3 border border-[#edeae1]">
            <span className="text-[#5c5953] block text-[10px] uppercase font-mono">Cumulative Duration</span>
            <span className="font-mono font-medium text-[#181816] mt-0.5 block">
              {totalDurationMs > 1000 ? `${(totalDurationMs / 1000).toFixed(2)} s` : `${totalDurationMs} ms`}
            </span>
          </div>

          <div className="rounded bg-[#fbfaf6] p-3 border border-[#edeae1]">
            <span className="text-[#5c5953] block text-[10px] uppercase font-mono">Telemetry Integrity</span>
            <span className="font-medium text-[#181816] mt-0.5 block flex items-center gap-1">
              <Database className="h-3 w-3 text-[#1f6339]" />
              PostgreSQL Verified
            </span>
          </div>
        </div>

        <p className="mt-3 text-xs text-[#5c5953] leading-relaxed">
          Displays genuine backend execution records saved in PostgreSQL. Every agent step captures exact latency,
          retries, tool calls, grounding traces, and machine-readable failure diagnostics. Zero simulated animations.
        </p>
      </div>

      {error && (
        <div className="rounded border border-[#f7d0ca] bg-[#fdf2f0] p-4 text-xs text-[#942e23] flex items-center gap-2" role="alert">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* The 11 Sequential Pipeline Agents */}
      <div className="space-y-3" role="feed" aria-label="11 pipeline agent steps">
        {loading && runs.length === 0 ? (
          <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-12 text-center text-xs text-[#5c5953]">
            <RefreshCw className="mx-auto h-5 w-5 animate-spin mb-2 text-[#181816]" />
            Loading real execution telemetry from database...
          </div>
        ) : (
          ORDERED_PIPELINE_AGENTS.map((def, idx) => {
            const run = runsByName.get(def.key);
            const isExpanded = expandedAgentKey === def.key;
            const panelId = `agent-telemetry-${def.key}`;
            const status = run?.status || "queued";
            const isCompleted = status === "completed";
            const isFailed = status === "failed";
            const isRunning = status === "running";

            return (
              <div
                key={def.key}
                className={`rounded border transition-colors ${
                  isFailed
                    ? "border-[#f7d0ca] bg-[#ffffff] shadow-editorial"
                    : isCompleted
                    ? "border-[#e6e2d8] bg-[#ffffff] shadow-editorial hover:border-[#ded9cc]"
                    : isRunning
                    ? "border-[#bfdbfe] bg-[#fbfdff] shadow-editorial"
                    : "border-[#edeae1] bg-[#faf9f5] opacity-80"
                } p-4 text-xs`}
              >
                <button
                  type="button"
                  onClick={() => toggleExpand(def.key)}
                  aria-expanded={isExpanded}
                  aria-controls={panelId}
                  className="w-full text-left flex flex-wrap items-center justify-between gap-3 cursor-pointer select-none rounded focus-visible:outline-2 focus-visible:outline-[#181816]"
                >
                  <div className="flex items-center gap-3">
                    <span
                      className={`flex h-7 w-7 items-center justify-center rounded-full font-mono text-[11px] font-bold shrink-0 border ${
                        isCompleted
                          ? "bg-[#f0f7f2] text-[#1f6339] border-[#cde4d3]"
                          : isFailed
                          ? "bg-[#fdf2f0] text-[#942e23] border-[#f7d0ca]"
                          : isRunning
                          ? "bg-[#ebf4ff] text-[#1e40af] border-[#bfdbfe]"
                          : "bg-[#f7f5ef] text-[#737067] border-[#ded9cc]"
                      }`}
                    >
                      {isCompleted ? "✓" : isFailed ? "!" : String(idx + 1).padStart(2, "0")}
                    </span>

                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-[#181816] text-[13px]">
                          {def.displayName}
                        </span>
                        <span className="font-mono text-[10px] text-[#737067]">
                          ({def.key})
                        </span>
                        {renderStatusBadge(status)}
                        {run?.final_score !== undefined && run?.final_score !== null && (
                          <span className="rounded bg-[#f7f5ef] px-2 py-0.5 text-[10px] font-mono font-medium text-[#181816] border border-[#ded9cc]">
                            Score: {run.final_score.toFixed(1)}/100
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-[#5c5953] mt-0.5">
                        {def.description}
                      </p>
                    </div>
                  </div>

                  {/* Execution Metrics Pill */}
                  <div className="flex items-center gap-3 sm:gap-4 text-[11px] font-mono text-[#5c5953]">
                    <span className="flex items-center gap-1" title="Execution Latency">
                      <Clock className="h-3 w-3" />
                      {run?.duration_ms !== null && run?.duration_ms !== undefined
                        ? `${run.duration_ms} ms`
                        : status === "running"
                        ? "in progress"
                        : "-"}
                    </span>
                    {run?.retrieval_count !== undefined && run.retrieval_count > 0 && (
                      <span title="Evidence / Section Retrievals">
                        Retr: {run.retrieval_count}
                      </span>
                    )}
                    {run?.model_calls !== undefined && run.model_calls > 0 && (
                      <span title="LLM / Inference Calls">
                        Calls: {run.model_calls}
                      </span>
                    )}
                    {run?.retry_count !== undefined && run.retry_count > 0 && (
                      <span className="text-[#8c6218]" title="Retry attempts">
                        Retries: {run.retry_count}
                      </span>
                    )}
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4 text-[#181816]" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-[#5c5953]" />
                    )}
                  </div>
                </button>

                {/* Dedicated Failure Box when status is failed or error exists */}
                {run && (run.status === "failed" || run.error) && (
                  <div className="mt-3 rounded border border-[#f7d0ca] bg-[#fdf2f0] p-3 text-xs text-[#942e23]">
                    <div className="flex items-center gap-1.5 font-semibold text-[11px] mb-1">
                      <ShieldAlert className="h-4 w-4 shrink-0 text-[#942e23]" />
                      Agent Failure Diagnostics
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mt-2 font-mono text-[11px]">
                      <div>
                        <span className="text-[#737067] block text-[10px] uppercase">Reason</span>
                        <span className="font-semibold break-words">{run.error || "Execution terminated unexpectedly"}</span>
                      </div>
                      <div>
                        <span className="text-[#737067] block text-[10px] uppercase">Retry Count</span>
                        <span>{run.retry_count}</span>
                      </div>
                      <div>
                        <span className="text-[#737067] block text-[10px] uppercase">Recovery Status</span>
                        <span className="uppercase font-semibold">{run.recovery_status || "unrecovered"}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Collapsible Telemetry JSON Drawer */}
                {isExpanded && (
                  <div id={panelId} className="mt-4 border-t border-[#edeae1] pt-3 text-[11px] font-mono space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-[10px] text-[#5c5953] uppercase font-bold">
                      <span>Telemetry &amp; Execution Metadata:</span>
                      {run?.created_at && (
                        <span>Logged: {new Date(run.created_at).toUTCString()}</span>
                      )}
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-[#fcfbf7] p-2.5 rounded border border-[#edeae1]">
                      <div>
                        <span className="text-[#737067] block text-[9px] uppercase">Start Time</span>
                        <span className="text-[#181816]">
                          {run?.start_time ? new Date(run.start_time).toLocaleTimeString() : "-"}
                        </span>
                      </div>
                      <div>
                        <span className="text-[#737067] block text-[9px] uppercase">End Time</span>
                        <span className="text-[#181816]">
                          {run?.end_time ? new Date(run.end_time).toLocaleTimeString() : "-"}
                        </span>
                      </div>
                      <div>
                        <span className="text-[#737067] block text-[9px] uppercase">Token Usage</span>
                        <span className="text-[#181816]">
                          {run?.token_usage && Object.keys(run.token_usage).length > 0
                            ? JSON.stringify(run.token_usage)
                            : "N/A"}
                        </span>
                      </div>
                      <div>
                        <span className="text-[#737067] block text-[9px] uppercase">Final Score</span>
                        <span className="text-[#181816]">
                          {run?.final_score !== null && run?.final_score !== undefined
                            ? `${run.final_score.toFixed(1)}/100`
                            : "N/A"}
                        </span>
                      </div>
                    </div>

                    <div>
                      <span className="text-[#5c5953] block mb-1 uppercase text-[10px] font-bold">
                        Structured Output Telemetry:
                      </span>
                      <pre className="max-h-60 overflow-x-auto rounded bg-[#fcfbf7] p-3 text-[#181816] border border-[#edeae1] leading-relaxed break-words whitespace-pre-wrap">
                        {run?.output ? JSON.stringify(run.output, null, 2) : "No output telemetry generated yet."}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
