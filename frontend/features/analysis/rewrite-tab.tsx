"use client";

import React, { useEffect, useState } from "react";
import { ReviewBoard } from "@/features/review/components/review-board";
import { ReviewSessionResponse } from "@/features/review/types";
import {
  fetchReviewSession,
  submitReviewDecisions,
  acceptAllSafeChanges,
  reRunReviewOptimization,
  finalizeHumanReview,
} from "@/lib/api";
import { RefreshCw, AlertTriangle } from "lucide-react";

interface RewriteTabProps {
  analysisId: string;
  onNavigateTab: (tab: string) => void;
}

export const RewriteTab: React.FC<RewriteTabProps> = ({ analysisId, onNavigateTab }) => {
  const [session, setSession] = useState<ReviewSessionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadSession = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchReviewSession(analysisId);
      setSession(data);
    } catch (err: any) {
      setError(err.message || "Failed to load review session");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (analysisId) {
      loadSession();
    }
  }, [analysisId]);

  const handleDecision = async (changeId: string, action: string, manualText?: string) => {
    try {
      const data = await submitReviewDecisions(analysisId, [
        { change_id: changeId, action, manual_text: manualText },
      ]);
      setSession(data);
    } catch (err: any) {
      alert(err.message || "Failed to save decision");
    }
  };

  const handleAcceptAllSafe = async () => {
    try {
      const data = await acceptAllSafeChanges(analysisId);
      setSession(data);
      setSuccessMessage("All low-risk, factually grounded changes accepted.");
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      alert(err.message || "Failed to accept safe changes");
    }
  };

  const handleReOptimize = async () => {
    try {
      setLoading(true);
      await reRunReviewOptimization(analysisId);
      await loadSession();
      setSuccessMessage("Re-ran optimization taking your review decisions into account.");
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      alert(err.message || "Failed to re-run optimization");
      setLoading(false);
    }
  };

  const handleFinalize = async (force: boolean, notes?: string) => {
    try {
      setLoading(true);
      const res = await finalizeHumanReview(analysisId, force, notes);
      setSuccessMessage(`Resume Version ${res.version_number} successfully published!`);
      setTimeout(() => {
        onNavigateTab("history");
      }, 1200);
    } catch (err: any) {
      alert(err.message || "Finalization failed");
      setLoading(false);
    }
  };

  if (loading && !session) {
    return (
      <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-16 text-center text-xs text-[#8a867c] shadow-editorial">
        <RefreshCw className="mx-auto h-5 w-5 animate-spin mb-3 text-[#181816]" />
        Loading grounded review session...
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="rounded border border-[#f7d0ca] bg-[#ffffff] p-8 text-center text-xs shadow-editorial">
        <AlertTriangle className="mx-auto h-6 w-6 text-[#942e23] mb-2" />
        <p className="font-semibold text-sm text-[#181816] mb-1">Error Loading Review Workspace</p>
        <p className="text-[#5c5953] mb-4">{error}</p>
        <button
          onClick={loadSession}
          className="rounded bg-[#181816] px-4 py-2 text-xs font-medium text-[#fcfbf7] hover:bg-[#2b2926]"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {successMessage && (
        <div className="rounded border border-[#cde4d3] bg-[#f0f7f2] p-3.5 text-xs text-[#1f6339] font-medium">
          ✓ {successMessage}
        </div>
      )}

      <ReviewBoard
        session={session}
        onAcceptChange={(id) => handleDecision(id, "accept")}
        onRejectChange={(id) => handleDecision(id, "reject")}
        onManualEditChange={(id, text) => handleDecision(id, "edit", text)}
        onAcceptAllSafe={handleAcceptAllSafe}
        onReOptimize={handleReOptimize}
        onFinalize={handleFinalize}
        isLoading={loading}
      />
    </div>
  );
};
