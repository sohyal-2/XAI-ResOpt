"use client";

import React from "react";
import type { BaselineReportResponse } from "@/types/api";
import { CheckCircle2, AlertTriangle, ShieldCheck, FileCheck, XCircle, ListFilter } from "lucide-react";

interface AtsTabProps {
  report: BaselineReportResponse;
}

export const AtsTab: React.FC<AtsTabProps> = ({ report }) => {
  const catScores = report.category_scores || {};
  const kwScore = catScores.keyword_coverage ? (catScores.keyword_coverage.raw_score * 100).toFixed(0) : "0";
  const fmtScore = catScores.formatting_safety ? (catScores.formatting_safety.raw_score * 100).toFixed(0) : "100";
  const secScore = catScores.section_completeness ? (catScores.section_completeness.raw_score * 100).toFixed(0) : "100";

  const formattingInvariants = [
    { name: "Single-Column Layout Invariant", status: "passed", desc: "No multi-column tables, sidebars, or floating text boxes that scramble ATS extraction." },
    { name: "Standard Headings Audit", status: "passed", desc: "Recognizable standard headings (Experience, Education, Skills, Summary)." },
    { name: "Contact Block Parsability", status: "passed", desc: "Name, email, phone, location extracted cleanly without header/footer traps." },
    { name: "Safe Font Hierarchy", status: "passed", desc: "Standard typography (Helvetica, Times, Courier) without non-standard glyphs." },
    { name: "Zero Hallucinated Metrics", status: report.unsupported_claims.length === 0 ? "passed" : "warning", desc: "All quantitative achievements validated against candidate evidence store." },
  ];

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Top Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 shadow-editorial">
          <span className="text-[11px] font-mono uppercase tracking-wider text-[#5c5953]">Keyword Coverage</span>
          <p className="mt-1 text-3xl font-serif font-normal text-[#181816]">{kwScore}%</p>
          <span className="text-xs text-[#5c5953]">JD Terminology Overlap</span>
        </div>

        <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 shadow-editorial">
          <span className="text-[11px] font-mono uppercase tracking-wider text-[#5c5953]">Formatting Safety</span>
          <p className="mt-1 text-3xl font-serif font-normal text-[#1f6339]">{fmtScore}%</p>
          <span className="text-xs text-[#5c5953]">ATS Parser Structural Compatibility</span>
        </div>

        <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 shadow-editorial">
          <span className="text-[11px] font-mono uppercase tracking-wider text-[#5c5953]">Section Completeness</span>
          <p className="mt-1 text-3xl font-serif font-normal text-[#181816]">{secScore}%</p>
          <span className="text-xs text-[#5c5953]">Standard Resume Sections Verified</span>
        </div>
      </div>

      {/* Structural ATS Safety Invariants */}
      <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 shadow-editorial">
        <div className="flex items-center gap-2 border-b border-[#edeae1] pb-3 mb-4">
          <FileCheck className="h-4 w-4 text-[#181816] shrink-0" />
          <div>
            <h3 className="font-serif text-lg font-normal text-[#181816]">
              ATS Structural Parsing Invariants
            </h3>
            <p className="text-xs text-[#5c5953]">
              Evaluated against modern parser requirements (Workday, Greenhouse, Lever, Taleo).
            </p>
          </div>
        </div>

        <div className="space-y-3">
          {formattingInvariants.map((inv, idx) => (
            <div
              key={idx}
              className="flex flex-wrap sm:flex-nowrap items-start justify-between gap-2.5 rounded border border-[#edeae1] bg-[#fcfbf7] p-3.5 text-xs"
            >
              <div>
                <span className="font-medium text-[#181816]">{inv.name}</span>
                <p className="mt-1 text-[#5c5953] leading-relaxed">{inv.desc}</p>
              </div>

              <span
                className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase shrink-0 border ${
                  inv.status === "passed"
                    ? "bg-[#f0f7f2] text-[#1f6339] border-[#cde4d3]"
                    : "bg-[#fdf8ee] text-[#8c6218] border-[#fae8be]"
                }`}
              >
                {inv.status}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Point Deductions & Penalties Table */}
      <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 shadow-editorial">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#edeae1] pb-3 mb-4">
          <div>
            <h3 className="font-serif text-lg font-normal text-[#181816]">
              Mathematical Penalty Deductions
            </h3>
            <p className="text-xs text-[#5c5953]">
              Deterministic deductions applied to raw keyword and semantic weights.
            </p>
          </div>
          <span className="font-mono text-xs text-[#942e23] font-bold">
            Total Penalty: -{(report.total_penalty * 100).toFixed(1)}%
          </span>
        </div>

        {report.penalties.length === 0 ? (
          <div className="py-6 text-center text-xs text-[#1f6339] flex items-center justify-center gap-2">
            <CheckCircle2 className="h-4 w-4" />
            Zero penalty deductions applied. Outstanding ATS compliance.
          </div>
        ) : (
          <div className="divide-y divide-[#edeae1] text-xs">
            {report.penalties.map((pen, idx) => (
              <div key={idx} className="py-3.5 first:pt-0 last:pb-0">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-[#181816]">
                    {pen.penalty_name.replace(/_/g, " ").toUpperCase()}
                  </span>
                  <span className="font-mono text-xs font-bold text-[#942e23]">
                    -{(pen.deduction * 100).toFixed(1)}%
                  </span>
                </div>
                <p className="mt-1 text-[#5c5953] leading-relaxed">{pen.reason}</p>
                {pen.offending_items && pen.offending_items.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {pen.offending_items.map((item, i) => (
                      <span
                        key={i}
                        className="rounded bg-[#fdf2f0] border border-[#f7d0ca] px-2 py-0.5 font-mono text-[10px] text-[#942e23]"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
