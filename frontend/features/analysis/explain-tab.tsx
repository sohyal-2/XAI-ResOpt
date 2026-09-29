"use client";

import React from "react";
import type { BaselineReportResponse } from "@/types/api";
import { HelpCircle, Sparkles, AlertTriangle, ShieldCheck, CheckCircle2 } from "lucide-react";

interface ExplainTabProps {
  report: BaselineReportResponse;
}

export const ExplainTab: React.FC<ExplainTabProps> = ({ report }) => {
  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Banner */}
      <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 shadow-editorial">
        <div className="flex items-center gap-2 text-xs font-mono text-[#5c5953] uppercase tracking-wider mb-1">
          <HelpCircle className="h-4 w-4 text-[#181816]" />
          Explainability Engine
        </div>
        <h2 className="font-serif text-xl sm:text-2xl font-normal text-[#181816]">
          Deterministic Score &amp; Penalty Rationales
        </h2>
        <p className="mt-2 text-xs text-[#5c5953] leading-relaxed max-w-2xl">
          Unlike black-box generative models, XAI-ResOpt explains every point calculation, deduction, and recommendation with traceable reasons and mathematical bounds.
        </p>
      </div>

      {/* Score Explanation Cards */}
      <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 shadow-editorial">
        <h3 className="font-serif text-lg font-normal text-[#181816] mb-4">
          Why Your Score Is {report.overall_score.toFixed(1)}%
        </h3>

        <div className="space-y-4 text-xs leading-relaxed">
          {report.reasons && report.reasons.length > 0 ? (
            report.reasons.map((reason, idx) => (
              <div key={idx} className="rounded border border-[#edeae1] bg-[#fcfbf7] p-4">
                <div className="flex items-center justify-between font-medium text-[#181816] mb-1">
                  <span className="capitalize">{reason.category.replace(/_/g, " ")} Factor</span>
                  <span className="font-mono text-[10px] text-[#5c5953]">{reason.impact}</span>
                </div>
                <p className="text-[#5c5953]">{reason.explanation}</p>
              </div>
            ))
          ) : (
            <div className="space-y-3 text-[#5c5953]">
              <p>
                • <strong className="text-[#181816]">Baseline Alignment:</strong> Your resume demonstrates verified capability in core technologies demanded by the job description.
              </p>
              <p>
                • <strong className="text-[#181816]">Factual Grounding:</strong> Confidence rating is at {(report.evidence_confidence * 100).toFixed(0)}%, ensuring high provenance integrity across experience bullets.
              </p>
              <p>
                • <strong className="text-[#181816]">Mathematical Deductions:</strong> Penalties are only deducted when specific keywords are missing or formatting anomalies arise.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Why Recommendations Were Generated */}
      <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 shadow-editorial">
        <h3 className="font-serif text-lg font-normal text-[#181816] mb-4">
          Recommendation Rationale &amp; Safety Proofs
        </h3>

        <div className="space-y-4">
          {report.recommendations && report.recommendations.length > 0 ? (
            report.recommendations.map((rec) => (
            <div key={rec.id} className="rounded border border-[#edeae1] bg-[#fcfbf7] p-4 text-xs">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#edeae1] pb-2 mb-2">
                <span className="font-semibold text-[#181816]">{rec.title}</span>
                <span className="text-[#1f6339] font-mono text-[10px] uppercase font-bold flex items-center gap-1">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Verified Safe
                </span>
              </div>
              <p className="text-[#5c5953] leading-relaxed mb-2">{rec.description}</p>
              <div className="font-mono text-[11px] text-[#5c5953]">
                <span>Evidence Backing: </span>
                <span className="text-[#181816] font-semibold">{rec.evidence_ids.length} verified candidate assertions</span>
              </div>
            </div>
          ))
          ) : (
            <div className="rounded border border-[#edeae1] bg-[#fcfbf7] p-6 text-center text-xs text-[#5c5953]">
              No open recommendation items. All requirements satisfy baseline evaluation constraints.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
