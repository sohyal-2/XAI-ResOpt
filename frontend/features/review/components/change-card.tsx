"use client";

import React, { useState } from "react";
import { ChangeReviewItem } from "../types";
import { TraceabilityModal } from "./traceability-modal";
import { Check, X, Edit3, ArrowRight, ShieldCheck, AlertCircle, Layers } from "lucide-react";

interface ChangeCardProps {
  item: ChangeReviewItem;
  onAccept: (changeId: string) => void;
  onReject: (changeId: string) => void;
  onManualEdit: (changeId: string, manualText: string) => void;
}

export const ChangeCard: React.FC<ChangeCardProps> = ({
  item,
  onAccept,
  onReject,
  onManualEdit,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(item.manual_text || item.after_text);
  const [showTrace, setShowTrace] = useState(false);

  const handleSaveEdit = () => {
    onManualEdit(item.change_id, editText);
    setIsEditing(false);
  };

  const getRiskBadge = (risk: string) => {
    switch (risk.toLowerCase()) {
      case "low":
        return (
          <span className="rounded bg-[#f0f7f2] border border-[#cde4d3] px-2 py-0.5 text-[11px] font-semibold text-[#1f6339]">
            Risk: Low
          </span>
        );
      case "medium":
        return (
          <span className="rounded bg-[#fdf8ee] border border-[#fae8be] px-2 py-0.5 text-[11px] font-semibold text-[#8c6218]">
            Risk: Medium
          </span>
        );
      default:
        return (
          <span className="rounded bg-[#fdf2f0] border border-[#f7d0ca] px-2 py-0.5 text-[11px] font-semibold text-[#942e23]">
            Risk: High
          </span>
        );
    }
  };

  const getSupportBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case "SUPPORTED":
        return (
          <span className="rounded bg-[#f0f7f2] border border-[#cde4d3] px-2 py-0.5 text-[11px] font-semibold text-[#1f6339] flex items-center gap-1">
            <Check className="h-3 w-3" /> SUPPORTED
          </span>
        );
      case "PARTIALLY_SUPPORTED":
        return (
          <span className="rounded bg-[#fdf8ee] border border-[#fae8be] px-2 py-0.5 text-[11px] font-semibold text-[#8c6218]">
            ~ PARTIALLY SUPPORTED
          </span>
        );
      case "UNSUPPORTED":
        return (
          <span className="rounded bg-[#fdf2f0] border border-[#f7d0ca] px-2 py-0.5 text-[11px] font-semibold text-[#942e23] flex items-center gap-1">
            <X className="h-3 w-3" /> UNSUPPORTED
          </span>
        );
      default:
        return (
          <span className="rounded bg-[#fdf2f0] border border-[#f7d0ca] px-2 py-0.5 text-[11px] font-semibold text-[#942e23]">
            CONTRADICTED
          </span>
        );
    }
  };

  const getDecisionBadge = (decision: string) => {
    switch (decision.toLowerCase()) {
      case "accepted":
        return (
          <span className="rounded bg-[#f0f7f2] border border-[#cde4d3] px-2.5 py-0.5 text-xs font-semibold text-[#1f6339]">
            Accepted
          </span>
        );
      case "rejected":
        return (
          <span className="rounded bg-[#fdf2f0] border border-[#f7d0ca] px-2.5 py-0.5 text-xs font-semibold text-[#942e23]">
            Rejected
          </span>
        );
      case "edited":
        return (
          <span className="rounded bg-[#f7f5ef] border border-[#ded9cc] px-2.5 py-0.5 text-xs font-semibold text-[#181816]">
            Manual Edit
          </span>
        );
      default:
        return (
          <span className="rounded bg-[#f7f5ef] border border-[#ded9cc] px-2.5 py-0.5 text-xs font-medium text-[#8a867c]">
            Pending Review
          </span>
        );
    }
  };

  return (
    <>
      <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 shadow-editorial transition-all">
        {/* Top Metadata Header */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#edeae1] pb-3 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] font-bold uppercase text-[#181816]">
              {item.section} • {item.change_type}
            </span>
            {getSupportBadge(item.supported_status)}
            {getRiskBadge(item.risk)}
          </div>
          <div>{getDecisionBadge(item.decision)}</div>
        </div>

        {/* 7-Dimension Inspection Grid */}
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          {/* BEFORE */}
          <div className="rounded border border-[#edeae1] bg-[#fcfbf7] p-3.5">
            <span className="font-mono text-[10px] uppercase font-bold text-[#5c5953] block mb-1">
              Original (Before)
            </span>
            <p className="text-[#5c5953] leading-relaxed line-through decoration-[#ded9cc]">
              {item.before_text}
            </p>
          </div>

          {/* AFTER */}
          <div className="rounded border border-[#cde4d3] bg-[#ffffff] p-3.5">
            <span className="font-mono text-[10px] uppercase font-bold text-[#1f6339] block mb-1">
              Proposed Rewrite (After)
            </span>
            {isEditing ? (
              <div className="space-y-2">
                <textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  rows={3}
                  className="w-full rounded border border-[#ded9cc] bg-[#fcfbf7] p-2 text-xs text-[#181816] focus:border-[#181816] focus:outline-none"
                />
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={handleSaveEdit}
                    className="rounded bg-[#181816] px-3.5 py-2 text-[11px] font-medium text-[#fcfbf7] hover:bg-[#2b2926] min-h-[40px] flex items-center"
                  >
                    Save Custom Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsEditing(false)}
                    className="rounded border border-[#ded9cc] bg-[#f7f5ef] px-3.5 py-2 text-[11px] text-[#5c5953] hover:text-[#181816] min-h-[40px] flex items-center"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-[#181816] leading-relaxed font-medium">
                {item.manual_text || item.after_text}
              </p>
            )}
          </div>
        </div>

        {/* Rationale & Evidence Details */}
        <div className="mt-3 rounded border border-[#edeae1] bg-[#fcfbf7] p-3 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-[#5c5953]">
              <span className="font-semibold text-[#181816]">Why changed: </span>
              {item.why_changed}
            </p>
            <button
              type="button"
              onClick={() => setShowTrace(true)}
              className="flex items-center gap-1.5 font-mono text-[11px] text-[#181816] hover:underline font-semibold shrink-0 min-h-[44px] sm:min-h-0"
            >
              <Layers className="h-3.5 w-3.5" />
              Trace 5-Tier Provenance
            </button>
          </div>
        </div>

        {/* Action Controls */}
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-[#edeae1] pt-3">
          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
            <button
              type="button"
              onClick={() => onAccept(item.change_id)}
              className="flex-1 sm:flex-initial flex items-center justify-center gap-1 rounded bg-[#181816] px-4 py-2 text-xs font-medium text-[#fcfbf7] hover:bg-[#2b2926] transition-colors shadow-sm min-h-[44px] sm:min-h-0"
            >
              <Check className="h-3.5 w-3.5" />
              Accept
            </button>
            <button
              type="button"
              onClick={() => onReject(item.change_id)}
              className="flex-1 sm:flex-initial flex items-center justify-center gap-1 rounded border border-[#f7d0ca] bg-[#fdf2f0] px-4 py-2 text-xs font-medium text-[#942e23] hover:bg-[#f7d0ca] transition-colors min-h-[44px] sm:min-h-0"
            >
              <X className="h-3.5 w-3.5" />
              Reject
            </button>
            {!isEditing && (
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="w-full sm:w-auto flex items-center justify-center gap-1 rounded border border-[#ded9cc] bg-[#f7f5ef] px-4 py-2 text-xs font-medium text-[#181816] hover:bg-[#eae6dd] transition-colors min-h-[44px] sm:min-h-0"
              >
                <Edit3 className="h-3.5 w-3.5" />
                Edit Manually
              </button>
            )}
          </div>

          <span className="font-mono text-[11px] text-[#5c5953]">
            ID: {item.change_id.slice(0, 8)}...
          </span>
        </div>
      </div>

      {showTrace && (
        <TraceabilityModal
          item={item}
          onClose={() => setShowTrace(false)}
        />
      )}
    </>
  );
};
