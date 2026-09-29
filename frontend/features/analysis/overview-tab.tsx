"use client";

import React from "react";
import type { BaselineReportResponse } from "@/types/api";
import {
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  TrendingUp,
  FileText,
  Layers,
  Sparkles,
} from "lucide-react";

interface OverviewTabProps {
  report: BaselineReportResponse;
  onNavigateTab: (tab: string) => void;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({ report, onNavigateTab }) => {
  const catScores = report.category_scores || {};
  const dimensions = [
    { key: "keyword_coverage", name: "Keyword Coverage", desc: "Lexical terminology matching JD requirements" },
    { key: "semantic_similarity", name: "Semantic Match", desc: "Vector similarity across skills and context" },
    { key: "requirement_coverage", name: "Requirement Coverage", desc: "Mandatory and preferred qualifications" },
    { key: "evidence_confidence", name: "Evidence Confidence", desc: "Factual backing for resume assertions" },
    { key: "experience_alignment", name: "Experience Alignment", desc: "Seniority and scope relevance" },
    { key: "formatting_safety", name: "ATS Formatting Safety", desc: "Single-column parsability and headings" },
    { key: "section_completeness", name: "Section Completeness", desc: "All mandatory resume sections present" },
    { key: "skill_match", name: "Skill Match", desc: "Core technical and tooling competence" },
  ];

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Top Executive Score Banner */}
      <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 shadow-editorial">
        <div className="flex flex-wrap items-center justify-between gap-4 sm:gap-6 border-b border-[#edeae1] pb-5 sm:pb-6">
          <div>
            <span className="font-mono text-xs uppercase tracking-wider text-[#5c5953]">
              {report.score_name}
            </span>
            <div className="mt-1 flex flex-wrap items-baseline gap-3">
              <h2 className="font-serif text-4xl sm:text-5xl font-normal text-[#181816]">
                {report.overall_score.toFixed(1)}%
              </h2>
              <span className="text-xs text-[#5c5953]">
                Normalized: <span className="font-mono font-medium text-[#181816]">{report.overall_score_normalized.toFixed(3)}</span>
              </span>
            </div>
            <p className="mt-2 text-xs text-[#5c5953] max-w-lg leading-relaxed">
              Deterministic multi-dimensional rating calculated by transparent scoring formula. Zero arbitrary LLM output.
            </p>
          </div>

          <div className="flex flex-col items-start sm:items-end gap-2">
            <span className="rounded bg-[#f0f7f2] border border-[#cde4d3] px-3 py-1 text-xs font-semibold text-[#1f6339] flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5" />
              Verified Factual Baseline
            </span>
            <span className="font-mono text-[11px] text-[#5c5953]">
              Formula: {report.calculation_version}
            </span>
            {report.total_penalty > 0 && (
              <span className="text-xs text-[#942e23] font-mono font-semibold">
                Penalty deduction: -{(report.total_penalty * 100).toFixed(1)}%
              </span>
            )}
          </div>
        </div>

        {/* 8-Category Progress Bars Grid */}
        <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          {dimensions.map((dim) => {
            const data = catScores[dim.key];
            const scoreVal = data ? data.raw_score * 100 : 0;
            const weightVal = data ? (data.weight * 100).toFixed(0) : "12";

            return (
              <div key={dim.key} className="rounded border border-[#edeae1] bg-[#fcfbf7] p-3.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-[#181816] truncate" title={dim.name}>
                    {dim.name}
                  </span>
                  <span className="font-mono text-[11px] font-bold text-[#181816]">
                    {scoreVal.toFixed(0)}%
                  </span>
                </div>

                {/* Progress bar */}
                <div className="mt-2 h-1.5 w-full rounded-full bg-[#ebe5d6] overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-300 ${
                      scoreVal >= 80 ? "bg-[#1f6339]" : scoreVal >= 60 ? "bg-[#8c6218]" : "bg-[#942e23]"
                    }`}
                    style={{ width: `${Math.min(100, Math.max(0, scoreVal))}%` }}
                  />
                </div>

                <div className="mt-2 flex items-center justify-between text-[10px] text-[#5c5953] font-mono">
                  <span>Weight: {weightVal}%</span>
                  <span>Target: {data ? (data.benchmark_target * 100).toFixed(0) : 80}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Strengths & Risks Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Strengths */}
        <div className="rounded border border-[#cde4d3] bg-[#ffffff] p-5 sm:p-6 shadow-editorial">
          <div className="flex items-center gap-2 border-b border-[#edeae1] pb-3 mb-4 text-[#1f6339]">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <h3 className="font-medium text-sm text-[#181816]">Identified Strengths</h3>
          </div>
          <ul className="space-y-2.5 text-xs text-[#5c5953]">
            {report.strengths.length > 0 ? (
              report.strengths.map((s, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-[#1f6339] font-bold shrink-0">•</span>
                  <span className="leading-relaxed">{s}</span>
                </li>
              ))
            ) : (
              <li className="text-[#5c5953]">Baseline review in progress.</li>
            )}
          </ul>
        </div>

        {/* ATS & Factual Risks */}
        <div className="rounded border border-[#f7d0ca] bg-[#ffffff] p-5 sm:p-6 shadow-editorial">
          <div className="flex items-center gap-2 border-b border-[#edeae1] pb-3 mb-4 text-[#942e23]">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <h3 className="font-medium text-sm text-[#181816]">Compatibility &amp; Factual Risks</h3>
          </div>
          <ul className="space-y-2.5 text-xs text-[#5c5953]">
            {report.ats_risks.length > 0 ? (
              report.ats_risks.map((risk, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-[#942e23] font-bold shrink-0">•</span>
                  <div className="leading-relaxed">
                    <span className="font-medium text-[#181816]">{risk.risk_type}: </span>
                    {risk.description}
                  </div>
                </li>
              ))
            ) : report.unsupported_claims.length > 0 ? (
              report.unsupported_claims.map((claim, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-[#942e23] font-bold shrink-0">•</span>
                  <span className="leading-relaxed">Unsupported claim detected: {claim}</span>
                </li>
              ))
            ) : (
              <li className="text-[#1f6339]">Zero structural or ungrounded claim risks detected.</li>
            )}
          </ul>
        </div>
      </div>

      {/* Priority Grounded Recommendations */}
      <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 shadow-editorial">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#edeae1] pb-3 mb-4">
          <div>
            <h3 className="font-serif text-lg font-normal text-[#181816]">
              Priority Optimization Recommendations
            </h3>
            <p className="text-xs text-[#5c5953]">
              Every suggestion is grounded in candidate proof and linked to specific job requirements.
            </p>
          </div>
          <button
            onClick={() => onNavigateTab("rewrite")}
            className="flex items-center gap-1 text-xs font-semibold text-[#181816] hover:underline min-h-[44px] py-1"
          >
            Review Proposed Changes <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="space-y-3">
          {report.recommendations && report.recommendations.length > 0 ? (
            report.recommendations.map((rec) => (
            <div
              key={rec.id}
              className="rounded border border-[#edeae1] bg-[#fcfbf7] p-4 text-xs transition-colors hover:border-[#ded9cc]"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-[#181816]">{rec.title}</span>
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase border ${
                      rec.priority === "high"
                        ? "bg-[#fdf2f0] text-[#942e23] border-[#f7d0ca]"
                        : "bg-[#fdf8ee] text-[#8c6218] border-[#fae8be]"
                    }`}
                  >
                    {rec.priority}
                  </span>
                </div>

                {rec.evidence_ids.length > 0 && (
                  <button
                    onClick={() => onNavigateTab("evidence")}
                    className="flex items-center gap-1 font-mono text-[11px] text-[#5c5953] hover:text-[#181816] hover:underline min-h-[36px] py-1"
                  >
                    <Layers className="h-3 w-3" />
                    {rec.evidence_ids.length} Evidence Links
                  </button>
                )}
              </div>

              <p className="mt-2 text-[#5c5953] leading-relaxed">{rec.description}</p>

              <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-[#edeae1] pt-2 text-[11px]">
                <span className="font-mono text-[#5c5953]">Action: {rec.suggested_action}</span>
                <button
                  onClick={() => onNavigateTab("rewrite")}
                  className="font-medium text-[#181816] hover:underline flex items-center gap-1 min-h-[36px] py-1"
                >
                  Inspect in Rewrite Workspace →
                </button>
              </div>
            </div>
          ))
          ) : (
            <div className="rounded border border-[#edeae1] bg-[#fcfbf7] p-6 text-center text-xs text-[#5c5953]">
              No priority recommendations flagged. Baseline ATS alignment satisfies target benchmarks.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
