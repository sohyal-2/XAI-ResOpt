"use client";

import React, { useState } from "react";
import type { BaselineReportResponse, EvidenceTraceItem } from "@/types/api";
import { ShieldCheck, Layers, FileText, Search, ExternalLink, AlertTriangle } from "lucide-react";

interface EvidenceTabProps {
  report: BaselineReportResponse;
}

export const EvidenceTab: React.FC<EvidenceTabProps> = ({ report }) => {
  const [searchQuery, setSearchQuery] = useState("");
  const evidenceItems = report.evidence_references || [];

  const filteredEvidence = evidenceItems.filter((item) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      item.matched_claim.toLowerCase().includes(q) ||
      (item.source_document && item.source_document.toLowerCase().includes(q)) ||
      (item.source_location && item.source_location.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Evidence Banner */}
      <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 shadow-editorial">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#edeae1] pb-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-[#5c5953] uppercase tracking-wider mb-1">
              <ShieldCheck className="h-4 w-4 text-[#1f6339]" />
              Grounded Evidence Graph
            </div>
            <h3 className="font-serif text-2xl font-normal text-[#181816]">
              Evidence Explorer &amp; Provenance
            </h3>
          </div>
          <div className="text-right">
            <span className="text-[10px] font-mono text-[#5c5953] uppercase font-bold">Evidence Confidence</span>
            <p className="text-xl font-serif font-normal text-[#1f6339]">
              {(report.evidence_confidence * 100).toFixed(1)}%
            </p>
          </div>
        </div>

        <p className="mt-3 text-xs text-[#5c5953] leading-relaxed">
          Every assertion is indexed with exact provenance. The system establishes bidirectional links from
          <span className="font-semibold text-[#181816]"> Recommendation → Claim → Evidence Item → Original Document Location</span>.
        </p>
      </div>

      {/* Unsupported Claims Alert Banner */}
      {report.unsupported_claims.length > 0 && (
        <div className="rounded border border-[#f7d0ca] bg-[#fdf2f0] p-4 sm:p-5 text-xs text-[#942e23]">
          <div className="flex items-center gap-2 font-bold mb-2">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>Unsupported Claims Barred from Output</span>
          </div>
          <p className="text-[#5c5953] leading-relaxed mb-3">
            The following claims lacked verifiable evidence in the candidate repository and were rejected by the Fact-Check Agent:
          </p>
          <div className="space-y-1.5">
            {report.unsupported_claims.map((claim, idx) => (
              <div key={idx} className="flex items-start gap-2 text-xs">
                <span className="text-[#942e23] font-bold shrink-0">✕</span>
                <span className="font-mono text-[#942e23] bg-[#ffffff] px-2 py-0.5 rounded border border-[#f7d0ca] break-all">
                  {claim}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Search & Filter Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-md">
          <label htmlFor="evidence-tab-search" className="sr-only">Search claims or documents</label>
          <Search className="absolute left-3 top-3 h-3.5 w-3.5 text-[#5c5953]" />
          <input
            id="evidence-tab-search"
            type="text"
            placeholder="Search claims, documents, or locations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded border border-[#ded9cc] bg-[#ffffff] pl-9 pr-3 py-2 text-xs text-[#181816] focus:border-[#181816] focus:outline-none shadow-sm min-h-[40px]"
          />
        </div>
        <span className="font-mono text-xs text-[#5c5953]">
          Showing {filteredEvidence.length} of {evidenceItems.length} verified items
        </span>
      </div>

      {/* Evidence Items Trace List */}
      <div className="space-y-3">
        {filteredEvidence.length === 0 ? (
          <div className="rounded border border-[#ded9cc] bg-[#ffffff] p-12 text-center text-xs text-[#5c5953]">
            No evidence items match your query.
          </div>
        ) : (
          filteredEvidence.map((item, idx) => (
            <div
              key={idx}
              className="rounded border border-[#e6e2d8] bg-[#ffffff] p-4 sm:p-5 shadow-editorial transition-colors hover:border-[#181816]"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#edeae1] pb-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[11px] font-bold text-[#181816]">
                    CLAIM #{idx + 1}
                  </span>
                  <span className="rounded bg-[#f0f7f2] border border-[#cde4d3] px-2 py-0.5 text-[10px] font-semibold text-[#1f6339]">
                    SUPPORTED
                  </span>
                </div>
                <span className="font-mono text-[11px] text-[#5c5953]">
                  Confidence: {(item.confidence * 100).toFixed(0)}%
                </span>
              </div>

              {/* Claim Body */}
              <div className="mt-3">
                <p className="text-xs text-[#181816] font-medium leading-relaxed">
                  &quot;{item.matched_claim}&quot;
                </p>
              </div>

              {/* Provenance Location Details */}
              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-2.5 text-[11px] font-mono border-t border-[#edeae1] pt-3">
                <div className="flex items-center gap-1.5 text-[#5c5953]">
                  <FileText className="h-3.5 w-3.5 text-[#5c5953] shrink-0" />
                  <span>Document: </span>
                  <span className="text-[#181816] font-semibold truncate">{item.source_document || "Primary Resume"}</span>
                </div>
                <div className="flex items-center gap-1.5 text-[#5c5953]">
                  <Layers className="h-3.5 w-3.5 text-[#5c5953] shrink-0" />
                  <span>Location: </span>
                  <span className="text-[#181816] font-semibold truncate">{item.source_location || "Overview / Skills"}</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
