"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchOptimizationHistory } from "@/lib/api";
import { History, FileText, ArrowRight, RefreshCw, Layers } from "lucide-react";

interface HistoryTabProps {
  analysisId: string;
}

export const HistoryTab: React.FC<HistoryTabProps> = ({ analysisId }) => {
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadHistory() {
      try {
        setLoading(true);
        const data = await fetchOptimizationHistory(analysisId);
        setHistory(data);
      } catch {
        setHistory([]);
      } finally {
        setLoading(false);
      }
    }
    if (analysisId) loadHistory();
  }, [analysisId]);

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Banner */}
      <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 shadow-editorial">
        <div className="flex items-center gap-2 text-xs font-mono text-[#5c5953] uppercase tracking-wider mb-1">
          <History className="h-4 w-4 text-[#181816]" />
          Audit Trail &amp; Versioning
        </div>
        <h2 className="font-serif text-xl sm:text-2xl font-normal text-[#181816]">
          Optimization Iteration History
        </h2>
        <p className="mt-2 text-xs text-[#5c5953] leading-relaxed">
          Records every pass of the closed-loop optimization engine (Optimizer → Critic → Fact-Check → ATS Re-Evaluator).
        </p>
      </div>

      {loading ? (
        <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-12 text-center text-xs text-[#5c5953]">
          <RefreshCw className="mx-auto h-5 w-5 animate-spin mb-2 text-[#181816]" />
          Loading iteration history...
        </div>
      ) : history.length === 0 ? (
        <div className="rounded border border-[#ded9cc] bg-[#ffffff] p-10 text-center text-xs text-[#5c5953]">
          <FileText className="mx-auto h-8 w-8 text-[#5c5953] mb-2" />
          <p className="font-medium text-sm text-[#181816]">Baseline Analysis Run Recorded</p>
          <p className="mt-1 max-w-sm mx-auto">
            You are currently viewing Iteration 0 (Initial Baseline). Trigger a closed-loop optimization run to generate candidate iterations.
          </p>
        </div>
      ) : (
        <div className="space-y-4 text-xs">
          {history.map((iter, idx) => (
            <div key={idx} className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 shadow-editorial">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#edeae1] pb-3 mb-3">
                <span className="font-mono font-bold text-[#181816]">
                  ITERATION {iter.iteration || idx + 1}
                </span>
                <span className="font-mono text-xs font-bold text-[#1f6339]">
                  Score: {iter.score ? `${iter.score.toFixed(1)}%` : "—"}
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-[11px] font-mono text-[#5c5953]">
                <div>
                  <span className="text-[#5c5953] block text-[10px] uppercase">Proposed:</span>
                  <span className="text-[#181816] font-bold">{iter.changes?.length || 0} changes</span>
                </div>
                <div>
                  <span className="text-[#5c5953] block text-[10px] uppercase">Rejected:</span>
                  <span className="text-[#942e23] font-bold">{iter.rejected_changes?.length || 0} unverified</span>
                </div>
                <div>
                  <span className="text-[#5c5953] block text-[10px] uppercase">Validation Issues:</span>
                  <span className="text-[#181816] font-bold">{iter.validation_issues?.length || 0}</span>
                </div>
                <div>
                  <span className="text-[#5c5953] block text-[10px] uppercase">Evidence Linked:</span>
                  <span className="text-[#1f6339] font-bold">{iter.evidence_used?.length || 0} citations</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
