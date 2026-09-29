"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ProtectedRoute } from "@/features/auth/protected-route";
import {
  fetchResumeVersions,
  getResumePdfExportUrl,
  getResumeDocxExportUrl,
  downloadResumePdf,
  downloadResumeDocx,
} from "@/lib/api";
import { useAuth } from "@/features/auth/auth-provider";
import type { ResumeVersionSummaryItem } from "@/types/api";
import { ArrowLeft, History, FileDown, FileText, CheckCircle2, Clock, RefreshCw } from "lucide-react";

function VersionHistoryContent() {
  const params = useParams();
  const resumeId = params?.id as string;
  const { token } = useAuth();

  const [versions, setVersions] = useState<ResumeVersionSummaryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadVersions = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchResumeVersions(resumeId);
      setVersions(data);
    } catch (err: any) {
      setError(err.message || "Failed to load version history");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (resumeId) loadVersions();
  }, [resumeId]);

  return (
    <main className="min-h-screen bg-[#fcfbf7] text-[#181816]">
      <header className="border-b border-[#e6e2d8] bg-[#fcfbf7]/95 sticky top-0 z-40 backdrop-blur-sm">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 sm:px-6 py-3.5 sm:py-4">
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="flex items-center gap-1.5 text-xs font-medium text-[#5c5953] hover:text-[#181816] transition-colors min-h-[44px] sm:min-h-0"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Dashboard
            </Link>
            <span className="text-[#ded9cc]">/</span>
            <span className="font-serif text-sm font-normal text-[#181816]">
              Resume Version History
            </span>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-4 sm:px-6 py-6 sm:py-10 space-y-6 sm:space-y-8">
        <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 shadow-editorial">
          <div className="flex items-center gap-2 text-xs font-mono text-[#5c5953] uppercase tracking-wider mb-1">
            <History className="h-4 w-4 text-[#181816]" />
            Immutable Version Archive
          </div>
          <h1 className="font-serif text-xl sm:text-2xl font-normal text-[#181816]">
            Document Versions &amp; Audit Trail
          </h1>
          <p className="mt-2 text-xs text-[#5c5953] leading-relaxed">
            Every finalized iteration creates a permanent resume version. You can inspect content diffs, review decisions, and download historical binary documents.
          </p>
        </div>

        {loading ? (
          <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-12 text-center text-xs text-[#5c5953]">
            <RefreshCw className="mx-auto h-5 w-5 animate-spin mb-2 text-[#181816]" />
            Loading version records...
          </div>
        ) : versions.length === 0 ? (
          <div className="rounded border border-[#ded9cc] bg-[#ffffff] p-10 text-center text-xs text-[#5c5953]">
            No versions recorded yet for this resume.
          </div>
        ) : (
          <div className="space-y-4" role="feed" aria-label="Resume version history">
            {versions.map((v) => (
              <div
                key={v.id}
                className="rounded border border-[#e6e2d8] bg-[#ffffff] p-4 sm:p-5 shadow-editorial text-xs"
              >
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#edeae1] pb-3 mb-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono font-bold text-sm text-[#181816]">
                      VERSION {v.version_number}
                    </span>
                    {v.is_final ? (
                      <span className="rounded bg-[#f0f7f2] border border-[#cde4d3] px-2 py-0.5 text-[10px] font-semibold text-[#1f6339] flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3" /> FINALIZED RELEASE
                      </span>
                    ) : (
                      <span className="rounded bg-[#f7f5ef] border border-[#ded9cc] px-2 py-0.5 text-[10px] text-[#5c5953]">
                        BASELINE DRAFT
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <a
                      href={getResumePdfExportUrl(v.id)}
                      download
                      className="flex items-center justify-center gap-1 rounded border border-[#ded9cc] bg-[#f7f5ef] px-3 py-1.5 text-xs font-medium text-[#181816] hover:bg-[#eae6dd] transition-colors min-h-[44px] sm:min-h-0"
                    >
                      <FileDown className="h-3.5 w-3.5" /> PDF
                    </a>
                    <a
                      href={getResumeDocxExportUrl(v.id)}
                      download
                      className="flex items-center justify-center gap-1 rounded border border-[#ded9cc] bg-[#f7f5ef] px-3 py-1.5 text-xs font-medium text-[#181816] hover:bg-[#eae6dd] transition-colors min-h-[44px] sm:min-h-0"
                    >
                      <FileText className="h-3.5 w-3.5" /> DOCX
                    </a>
                  </div>
                </div>

                <div className="flex items-center gap-4 text-[11px] font-mono text-[#5c5953] flex-wrap">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {new Date(v.created_at).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                  <span>ID: {v.id.slice(0, 8)}...</span>
                </div>

                {v.content_preview && (
                  <div className="mt-3 rounded bg-[#fcfbf7] p-3 text-[#5c5953] border border-[#edeae1] font-mono text-[11px] leading-relaxed break-words">
                    {v.content_preview}...
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

export default function VersionHistoryPage() {
  return (
    <ProtectedRoute>
      <VersionHistoryContent />
    </ProtectedRoute>
  );
}
