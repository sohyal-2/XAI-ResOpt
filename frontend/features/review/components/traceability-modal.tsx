"use client";

import React, { useEffect } from "react";
import { ChangeReviewItem, TraceNode } from "../types";
import { X, Layers, ShieldCheck, ArrowDown } from "lucide-react";

interface TraceabilityModalProps {
  item?: ChangeReviewItem;
  trace?: TraceNode;
  isOpen?: boolean;
  onClose: () => void;
}

export const TraceabilityModal: React.FC<TraceabilityModalProps> = ({
  item,
  trace,
  isOpen = true,
  onClose,
}) => {
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = originalOverflow;
    };
  }, [isOpen, onClose]);

  if (isOpen === false) return null;

  const t: TraceNode = trace || item?.trace_chain || {
    recommendation_text: item?.why_changed || "Optimize bullet for ATS keyword density and requirements alignment.",
    change_before: item?.before_text || "",
    change_after: item?.after_text || "",
    claim_text: item?.evidence && item.evidence.length > 0 ? item.evidence[0].text : item?.before_text,
    claim_status: item?.supported_status || "SUPPORTED",
    evidence_text: item?.evidence && item.evidence.length > 0 ? item.evidence[0].text : "Extracted from candidate background.",
    original_source: item?.evidence && item.evidence.length > 0 ? item.evidence[0].source_uri || "Primary Resume" : "Resume.pdf",
    source_location: item?.evidence && item.evidence.length > 0 ? item.evidence[0].location || "Experience Section" : "Experience",
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#181816]/40 p-4 backdrop-blur-xs"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="traceability-modal-title"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-2xl rounded border border-[#ded9cc] bg-[#ffffff] p-5 sm:p-6 shadow-popup text-[#181816] max-h-[90vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#edeae1] pb-4">
          <div className="flex items-center gap-2.5">
            <span className="flex h-6 w-6 items-center justify-center rounded bg-[#181816] text-[10px] font-bold text-[#fcfbf7] shrink-0">
              5T
            </span>
            <div>
              <h3 id="traceability-modal-title" className="text-base font-serif font-normal text-[#181816]">
                5-Tier Provenance Trace
              </h3>
              <p className="text-[11px] text-[#5c5953]">
                Bidirectional audit trail linking recommendation to ground truth
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close provenance trace"
            className="flex h-10 w-10 sm:h-8 sm:w-8 items-center justify-center rounded text-[#5c5953] hover:bg-[#f7f5ef] hover:text-[#181816] transition-colors focus-visible:outline-2 focus-visible:outline-[#181816]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* 5 Steps Provenance Chain */}
        <div className="mt-6 space-y-4 text-xs">
          {/* Tier 1: Recommendation */}
          <div className="relative pl-6 border-l-2 border-[#181816]">
            <span className="absolute -left-2 top-0 flex h-4 w-4 items-center justify-center rounded-full bg-[#181816] text-[9px] font-bold text-[#fcfbf7]">
              1
            </span>
            <span className="text-[10px] uppercase tracking-wider text-[#5c5953] font-mono font-bold block">
              Tier 1 — Optimization Directive
            </span>
            <p className="mt-0.5 text-[#181816] font-medium leading-relaxed">
              {t.recommendation_text}
            </p>
          </div>

          {/* Tier 2: Change Proposed */}
          <div className="relative pl-6 border-l-2 border-[#181816]">
            <span className="absolute -left-2 top-0 flex h-4 w-4 items-center justify-center rounded-full bg-[#181816] text-[9px] font-bold text-[#fcfbf7]">
              2
            </span>
            <span className="text-[10px] uppercase tracking-wider text-[#5c5953] font-mono font-bold block">
              Tier 2 — Proposed Rewrite
            </span>
            <p className="mt-0.5 text-[#181816] font-medium leading-relaxed bg-[#fcfbf7] p-2 rounded border border-[#edeae1]">
              &quot;{t.change_after}&quot;
            </p>
          </div>

          {/* Tier 3: Verified Claim */}
          <div className="relative pl-6 border-l-2 border-[#181816]">
            <span className="absolute -left-2 top-0 flex h-4 w-4 items-center justify-center rounded-full bg-[#181816] text-[9px] font-bold text-[#fcfbf7]">
              3
            </span>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[10px] uppercase tracking-wider text-[#5c5953] font-mono font-bold">
                Tier 3 — Candidate Claim Assertion
              </span>
              <span className="rounded bg-[#f0f7f2] border border-[#cde4d3] px-1.5 py-0.5 text-[10px] text-[#1f6339] font-bold">
                {t.claim_status || "SUPPORTED"}
              </span>
            </div>
            <p className="mt-0.5 text-[#5c5953] leading-relaxed">
              {t.claim_text || t.change_before}
            </p>
          </div>

          {/* Tier 4: Grounded Evidence Store */}
          <div className="relative pl-6 border-l-2 border-[#181816]">
            <span className="absolute -left-2 top-0 flex h-4 w-4 items-center justify-center rounded-full bg-[#181816] text-[9px] font-bold text-[#fcfbf7]">
              4
            </span>
            <span className="text-[10px] uppercase tracking-wider text-[#5c5953] font-mono font-bold block">
              Tier 4 — Grounded Evidence Entity
            </span>
            <p className="mt-0.5 text-[#5c5953] leading-relaxed">
              {t.evidence_text}
            </p>
          </div>

          {/* Tier 5: Original Document Location */}
          <div className="relative pl-6 border-l-2 border-[#2e6b48]">
            <span className="absolute -left-2 top-0 flex h-4 w-4 items-center justify-center rounded-full bg-[#2e6b48] text-[9px] font-bold text-[#fcfbf7]">
              5
            </span>
            <span className="text-[10px] uppercase tracking-wider text-[#1f6339] font-mono font-bold block">
              Tier 5 — Primary Origin Document &amp; Location
            </span>
            <p className="mt-0.5 text-[#181816] font-mono text-[11px] break-words">
              {t.original_source} → {t.source_location}
            </p>
          </div>
        </div>

        <div className="mt-6 flex justify-end border-t border-[#edeae1] pt-4">
          <button
            type="button"
            onClick={onClose}
            className="w-full sm:w-auto rounded bg-[#181816] px-5 py-2.5 text-xs font-medium text-[#fcfbf7] hover:bg-[#2b2926] transition-colors min-h-[44px] flex items-center justify-center shadow-sm"
          >
            Close Provenance Trace
          </button>
        </div>
      </div>
    </div>
  );
};
