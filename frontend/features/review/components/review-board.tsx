"use client";

import React, { useState, useEffect } from "react";
import { ReviewSessionResponse } from "../types";
import { ChangeCard } from "./change-card";
import { CheckCheck, RefreshCw, ArrowRight, ShieldCheck, AlertCircle } from "lucide-react";

interface ReviewBoardProps {
  session: ReviewSessionResponse;
  onAcceptChange: (changeId: string) => void;
  onRejectChange: (changeId: string) => void;
  onManualEditChange: (changeId: string, manualText: string) => void;
  onAcceptAllSafe: () => void;
  onReOptimize: () => void;
  onFinalize: (force: boolean, notes?: string) => void;
  isLoading?: boolean;
}

export const ReviewBoard: React.FC<ReviewBoardProps> = ({
  session,
  onAcceptChange,
  onRejectChange,
  onManualEditChange,
  onAcceptAllSafe,
  onReOptimize,
  onFinalize,
  isLoading = false,
}) => {
  const [showFinalizeModal, setShowFinalizeModal] = useState(false);
  const [notes, setNotes] = useState("");
  const [forceClaims, setForceClaims] = useState(false);

  useEffect(() => {
    if (!showFinalizeModal) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setShowFinalizeModal(false);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = originalOverflow;
    };
  }, [showFinalizeModal]);

  const hasUnsupported = session.unsupported_claims_count > 0;

  const handleFinalizeConfirm = () => {
    onFinalize(forceClaims, notes);
    setShowFinalizeModal(false);
  };

  return (
    <div className="space-y-6">
      {/* Top Header & Metrics Banner */}
      <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 shadow-editorial text-[#181816]">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-[#edeae1] pb-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-[#5c5953] uppercase tracking-wider mb-1">
              <ShieldCheck className="h-4 w-4 text-[#181816]" />
              Human-in-the-Loop Change Review
            </div>
            <h2 className="font-serif text-xl sm:text-2xl font-normal text-[#181816]">
              Review Proposed Modifications
            </h2>
            <p className="mt-1 text-xs text-[#5c5953]">
              Inspect AI-suggested keyword enhancements, edit wording manually, verify provenance, and finalize resume versions.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 w-full lg:w-auto">
            <button
              type="button"
              onClick={onAcceptAllSafe}
              disabled={isLoading}
              className="flex-1 sm:flex-initial flex items-center justify-center gap-1.5 rounded border border-[#cde4d3] bg-[#f0f7f2] px-3.5 py-2 text-xs font-semibold text-[#1f6339] hover:bg-[#e4f2e8] transition-colors disabled:opacity-50 min-h-[44px]"
            >
              <CheckCheck className="h-3.5 w-3.5" />
              Accept All Safe
            </button>
            <button
              type="button"
              onClick={onReOptimize}
              disabled={isLoading}
              className="flex-1 sm:flex-initial flex items-center justify-center gap-1.5 rounded border border-[#ded9cc] bg-[#f7f5ef] px-3.5 py-2 text-xs font-medium text-[#181816] hover:bg-[#eae6dd] transition-colors disabled:opacity-50 min-h-[44px]"
            >
              <RefreshCw className={`h-3 w-3 ${isLoading ? "animate-spin" : ""}`} />
              Re-run Optimizer
            </button>
            <button
              type="button"
              onClick={() => setShowFinalizeModal(true)}
              disabled={isLoading}
              className="w-full sm:w-auto flex items-center justify-center gap-1.5 rounded bg-[#181816] px-4 py-2 text-xs font-medium text-[#fcfbf7] hover:bg-[#2b2926] transition-colors disabled:opacity-50 shadow-sm min-h-[44px]"
            >
              Finalize &amp; Publish Version
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Status Counts */}
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5 sm:gap-3">
          <div className="rounded border border-[#edeae1] bg-[#fcfbf7] p-3 text-xs">
            <span className="text-[10px] font-mono text-[#5c5953] uppercase font-bold">Total Changes</span>
            <p className="text-lg font-serif font-normal text-[#181816] mt-0.5">{session.total_changes}</p>
          </div>
          <div className="rounded border border-[#cde4d3] bg-[#f0f7f2] p-3 text-xs">
            <span className="text-[10px] font-mono text-[#1f6339] uppercase font-bold">Accepted</span>
            <p className="text-lg font-serif font-normal text-[#1f6339] mt-0.5">{session.accepted_count}</p>
          </div>
          <div className="rounded border border-[#ded9cc] bg-[#fcfbf7] p-3 text-xs">
            <span className="text-[10px] font-mono text-[#181816] uppercase font-bold">Manual Edits</span>
            <p className="text-lg font-serif font-normal text-[#181816] mt-0.5">{session.edited_count}</p>
          </div>
          <div className="rounded border border-[#f7d0ca] bg-[#fdf2f0] p-3 text-xs">
            <span className="text-[10px] font-mono text-[#942e23] uppercase font-bold">Rejected</span>
            <p className="text-lg font-serif font-normal text-[#942e23] mt-0.5">{session.rejected_count}</p>
          </div>
          <div className="col-span-2 sm:col-span-1 rounded border border-[#edeae1] bg-[#fcfbf7] p-3 text-xs">
            <span className="text-[10px] font-mono text-[#5c5953] uppercase font-bold">Pending</span>
            <p className="text-lg font-serif font-normal text-[#5c5953] mt-0.5">{session.pending_count}</p>
          </div>
        </div>

        {/* Warning if unsupported claims exist */}
        {hasUnsupported && (
          <div className="mt-4 flex items-start gap-2.5 rounded border border-[#f7d0ca] bg-[#fdf2f0] p-3.5 text-xs text-[#942e23]" role="alert">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Factual Guardrail Alert: </span>
              {session.unsupported_claims_count} unverified claim{session.unsupported_claims_count > 1 ? "s" : ""} detected.
              Finalizing requires explicit acknowledgement or manual revision.
            </div>
          </div>
        )}
      </div>

      {/* Change Cards Feed */}
      <div className="space-y-4" role="feed" aria-label="Proposed changes list">
        {session.changes.length === 0 ? (
          <div className="rounded border border-[#ded9cc] bg-[#ffffff] p-12 text-center text-xs text-[#5c5953]">
            No proposed changes available for this session.
          </div>
        ) : (
          session.changes.map((change) => (
            <ChangeCard
              key={change.change_id}
              item={change}
              onAccept={onAcceptChange}
              onReject={onRejectChange}
              onManualEdit={onManualEditChange}
            />
          ))
        )}
      </div>

      {/* Finalize Modal */}
      {showFinalizeModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-[#181816]/40 p-4 backdrop-blur-xs"
          onClick={() => setShowFinalizeModal(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="finalize-modal-title"
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-lg rounded border border-[#ded9cc] bg-[#ffffff] p-5 sm:p-6 shadow-popup text-[#181816] max-h-[90vh] overflow-y-auto"
          >
            <div className="flex items-center gap-2 border-b border-[#edeae1] pb-3 mb-4">
              <ShieldCheck className="h-5 w-5 text-[#181816]" />
              <h3 id="finalize-modal-title" className="font-serif text-lg font-normal text-[#181816]">
                Finalize &amp; Publish Resume Version
              </h3>
            </div>

            <p className="text-xs text-[#5c5953] leading-relaxed mb-4">
              Publishing applies all accepted changes and manual edits to create a new deterministic resume version.
              Pre-rendering invariants will run to verify single-column ATS parsability.
            </p>

            <div className="space-y-4 text-xs">
              <div>
                <label htmlFor="version-notes" className="block font-medium text-[#181816] mb-1">
                  Version Release Notes (Optional)
                </label>
                <textarea
                  id="version-notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g. Optimized for Senior Backend role with enhanced FastAPI &amp; PostgreSQL keywords..."
                  rows={3}
                  className="w-full rounded border border-[#ded9cc] bg-[#fcfbf7] p-2.5 text-xs text-[#181816] focus:border-[#181816] focus:outline-none"
                />
              </div>

              {hasUnsupported && (
                <label className="flex items-start gap-2 rounded border border-[#f7d0ca] bg-[#fdf2f0] p-3 text-xs text-[#942e23] cursor-pointer">
                  <input
                    type="checkbox"
                    checked={forceClaims}
                    onChange={(e) => setForceClaims(e.target.checked)}
                    className="mt-0.5 h-4 w-4"
                  />
                  <span>
                    Acknowledge and override unresolved unverified claims for this release.
                  </span>
                </label>
              )}
            </div>

            <div className="mt-6 flex flex-col sm:flex-row items-center justify-end gap-3 border-t border-[#edeae1] pt-4">
              <button
                type="button"
                onClick={() => setShowFinalizeModal(false)}
                className="w-full sm:w-auto rounded border border-[#ded9cc] bg-[#f7f5ef] px-4 py-2.5 text-xs font-medium text-[#5c5953] hover:text-[#181816] min-h-[44px] flex items-center justify-center"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleFinalizeConfirm}
                disabled={hasUnsupported && !forceClaims}
                className="w-full sm:w-auto rounded bg-[#181816] px-5 py-2.5 text-xs font-medium text-[#fcfbf7] hover:bg-[#2b2926] disabled:opacity-40 transition-colors shadow-sm min-h-[44px] flex items-center justify-center"
              >
                Confirm &amp; Publish
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
