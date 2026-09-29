"use client";

import React, { useState } from "react";
import type { BaselineReportResponse, RequirementTraceItem } from "@/types/api";
import { CheckCircle2, AlertCircle, XCircle, Search, Layers } from "lucide-react";

interface SkillsTabProps {
  report: BaselineReportResponse;
  onNavigateTab: (tab: string) => void;
}

export const SkillsTab: React.FC<SkillsTabProps> = ({ report, onNavigateTab }) => {
  const [filter, setFilter] = useState<"all" | "matched" | "missing">("all");
  const [searchQuery, setSearchQuery] = useState("");

  const reqs = report.requirement_coverage || [];
  const matchedReqs = reqs.filter((r) => r.status === "matched");
  const missingReqs = reqs.filter((r) => r.status === "missing");

  const filteredReqs = reqs.filter((r) => {
    if (filter === "matched" && r.status !== "matched") return false;
    if (filter === "missing" && r.status !== "missing") return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        r.requirement_text.toLowerCase().includes(q) ||
        r.matched_terms.some((t) => t.toLowerCase().includes(q)) ||
        r.missing_terms.some((t) => t.toLowerCase().includes(q))
      );
    }
    return true;
  });

  return (
    <div className="space-y-8">
      {/* Top Skill Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="rounded border border-[#cde4d3] bg-[#ffffff] p-5 shadow-editorial">
          <span className="text-[11px] font-mono uppercase tracking-wider text-[#1f6339]">Verified Skills</span>
          <p className="mt-1 text-3xl font-serif font-normal text-[#1f6339]">{matchedReqs.length}</p>
          <span className="text-xs text-[#5c5953]">Grounded in candidate evidence</span>
        </div>

        <div className="rounded border border-[#f7d0ca] bg-[#ffffff] p-5 shadow-editorial">
          <span className="text-[11px] font-mono uppercase tracking-wider text-[#942e23]">Mandatory Gaps</span>
          <p className="mt-1 text-3xl font-serif font-normal text-[#942e23]">{report.mandatory_skill_gaps.length}</p>
          <span className="text-xs text-[#5c5953]">Critical missing requirements</span>
        </div>

        <div className="rounded border border-[#fae8be] bg-[#ffffff] p-5 shadow-editorial">
          <span className="text-[11px] font-mono uppercase tracking-wider text-[#8c6218]">Preferred Gaps</span>
          <p className="mt-1 text-3xl font-serif font-normal text-[#8c6218]">{report.preferred_skill_gaps.length}</p>
          <span className="text-xs text-[#5c5953]">Secondary recommendations</span>
        </div>
      </div>

      {/* Critical Skill Gaps Notice */}
      {report.mandatory_skill_gaps.length > 0 && (
        <div className="rounded border border-[#f7d0ca] bg-[#fdf2f0] p-5 text-xs text-[#942e23]">
          <div className="flex items-center gap-2 font-bold mb-1">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>Unsatisfied Mandatory Job Requirements</span>
          </div>
          <p className="text-[#5c5953] leading-relaxed mb-3">
            The target role specifies mandatory requirements that cannot be verified from your uploaded background.
            Rather than fabricating these skills, XAI-ResOpt preserves factual honesty.
          </p>
          <div className="flex flex-wrap gap-1.5">
            {report.mandatory_skill_gaps.map((skill, idx) => (
              <span
                key={idx}
                className="rounded bg-[#ffffff] border border-[#f7d0ca] px-2.5 py-1 font-mono text-[11px] font-medium text-[#942e23]"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Interactive Requirement & Skill Matrix */}
      <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 shadow-editorial">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#edeae1] pb-4 mb-4">
          <div>
            <h3 className="font-serif text-lg font-normal text-[#181816]">
              Requirements &amp; Evidence Matrix
            </h3>
            <p className="text-xs text-[#5c5953]">
              Full breakdown of extracted JD requirements and candidate evidence matches.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full lg:w-auto">
            {/* Filter Toggle */}
            <div className="flex items-center rounded border border-[#ded9cc] bg-[#fcfbf7] p-1 text-xs font-medium">
              <button
                onClick={() => setFilter("all")}
                className={`flex-1 sm:flex-none rounded px-3 py-1.5 transition-colors min-h-[38px] flex items-center justify-center ${
                  filter === "all" ? "bg-[#181816] text-[#fcfbf7]" : "text-[#5c5953] hover:text-[#181816]"
                }`}
              >
                All ({reqs.length})
              </button>
              <button
                onClick={() => setFilter("matched")}
                className={`flex-1 sm:flex-none rounded px-3 py-1.5 transition-colors min-h-[38px] flex items-center justify-center ${
                  filter === "matched" ? "bg-[#181816] text-[#fcfbf7]" : "text-[#5c5953] hover:text-[#181816]"
                }`}
              >
                Matched ({matchedReqs.length})
              </button>
              <button
                onClick={() => setFilter("missing")}
                className={`flex-1 sm:flex-none rounded px-3 py-1.5 transition-colors min-h-[38px] flex items-center justify-center ${
                  filter === "missing" ? "bg-[#181816] text-[#fcfbf7]" : "text-[#5c5953] hover:text-[#181816]"
                }`}
              >
                Missing ({missingReqs.length})
              </button>
            </div>

            {/* Search Input */}
            <div className="relative flex-1 sm:w-60">
              <label htmlFor="skills-search-input" className="sr-only">Search skills</label>
              <Search className="absolute left-3 top-3 h-3.5 w-3.5 text-[#5c5953]" />
              <input
                id="skills-search-input"
                type="text"
                placeholder="Search skills..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded border border-[#ded9cc] bg-[#fcfbf7] pl-8 pr-3 py-2 text-xs text-[#181816] focus:border-[#181816] focus:outline-none min-h-[40px]"
              />
            </div>
          </div>
        </div>

        {/* Requirements Table / Card List */}
        <div className="space-y-3">
          {filteredReqs.length === 0 ? (
            <div className="py-8 text-center text-xs text-[#5c5953]">
              No requirements match your current filter.
            </div>
          ) : (
            filteredReqs.map((req, idx) => {
              const isMatched = req.status === "matched";
              return (
                <div
                  key={idx}
                  className={`rounded border p-4 text-xs transition-colors ${
                    isMatched
                      ? "border-[#cde4d3] bg-[#ffffff]"
                      : "border-[#edeae1] bg-[#fcfbf7]"
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="flex items-start gap-2 max-w-full sm:max-w-xl">
                      {isMatched ? (
                        <CheckCircle2 className="h-4 w-4 text-[#1f6339] shrink-0 mt-0.5" />
                      ) : (
                        <XCircle className="h-4 w-4 text-[#942e23] shrink-0 mt-0.5" />
                      )}
                      <div>
                        <span className="font-medium text-[#181816] text-xs leading-snug">
                          {req.requirement_text}
                        </span>
                        <div className="mt-1.5 flex flex-wrap items-center gap-2">
                          <span className="rounded bg-[#f7f5ef] px-1.5 py-0.5 font-mono text-[10px] text-[#5c5953] border border-[#ded9cc]">
                            {req.kind.toUpperCase()}
                          </span>
                          <span className="text-[11px] text-[#5c5953] font-mono">
                            Confidence: {(req.match_confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </div>
                    </div>

                    {isMatched && req.source_evidence_ids.length > 0 && (
                      <button
                        onClick={() => onNavigateTab("evidence")}
                        className="flex items-center gap-1 font-mono text-[11px] text-[#5c5953] hover:text-[#181816] hover:underline py-1 min-h-[36px]"
                      >
                        <Layers className="h-3 w-3" />
                        View Evidence Links
                      </button>
                    )}
                  </div>

                  {/* Matched vs Missing Terms Chips */}
                  <div className="mt-3 flex flex-wrap gap-2 border-t border-[#edeae1] pt-2 text-[11px]">
                    {req.matched_terms.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1">
                        <span className="text-[#5c5953]">Matched:</span>
                        {req.matched_terms.map((term, i) => (
                          <span
                            key={i}
                            className="rounded bg-[#f0f7f2] border border-[#cde4d3] px-1.5 py-0.2 text-[#1f6339] font-mono"
                          >
                            {term}
                          </span>
                        ))}
                      </div>
                    )}
                    {req.missing_terms.length > 0 && (
                      <div className="flex flex-wrap items-center gap-1">
                        <span className="text-[#5c5953]">Missing:</span>
                        {req.missing_terms.map((term, i) => (
                          <span
                            key={i}
                            className="rounded bg-[#fdf2f0] border border-[#f7d0ca] px-1.5 py-0.2 text-[#942e23] font-mono"
                          >
                            {term}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
