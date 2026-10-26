"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "@/features/auth/protected-route";
import { fetchGlobalEvidence } from "@/lib/api";
import {
  ArrowLeft,
  Search,
  Layers,
  ShieldCheck,
  FileText,
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
} from "lucide-react";

function EvidenceExplorerContent() {
  const [evidence, setEvidence] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<string>("all");

  const loadEvidence = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchGlobalEvidence(100);
      setEvidence(data);
    } catch (err: any) {
      setError(err.message || "Failed to load evidence records");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvidence();
  }, []);

  const filteredItems = evidence.filter((item) => {
    if (filterType !== "all" && item.evidence_type !== filterType) return false;
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (item.text && item.text.toLowerCase().includes(q)) ||
      (item.source_location && item.source_location.toLowerCase().includes(q)) ||
      (item.source_document && item.source_document.toLowerCase().includes(q))
    );
  });

  return (
    <main className="min-h-screen bg-[#fcfbf7] text-[#181816]">
      {/* Top Header */}
      <header className="border-b border-[#e6e2d8] bg-[#fcfbf7]/95 sticky top-0 z-40 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 sm:px-6 py-3.5 sm:py-4">
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="flex items-center gap-1.5 text-xs font-medium text-[#5c5953] hover:text-[#181816] transition-colors min-h-[44px] sm:min-h-0"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Dashboard
            </Link>
            <span className="text-[#ded9cc]">•</span>
            <Link
              href="/ats-checker"
              className="text-xs font-medium text-[#181816] hover:underline flex items-center gap-1"
            >
              <Sparkles className="h-3 w-3 text-[#8c6218]" />
              ATS Checker
            </Link>
            <span className="text-[#ded9cc]">/</span>
            <span className="font-serif text-sm font-normal text-[#181816]">
              Global Evidence Explorer
            </span>
          </div>
          <button
            type="button"
            onClick={loadEvidence}
            aria-label="Refresh evidence list"
            className="flex items-center gap-1.5 rounded border border-[#ded9cc] bg-[#f7f5ef] px-3.5 py-2 text-xs font-medium text-[#181816] hover:bg-[#eae6dd] min-h-[44px] sm:min-h-0"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-4 sm:px-6 py-6 sm:py-10 space-y-6 sm:space-y-8">
        {/* Banner */}
        <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 shadow-editorial">
          <div className="flex items-center gap-2 text-xs font-mono text-[#5c5953] uppercase tracking-wider mb-1">
            <Layers className="h-4 w-4 text-[#181816]" />
            Verifiable Knowledge Base
          </div>
          <h1 className="font-serif text-2xl sm:text-3xl font-normal text-[#181816]">
            Evidence &amp; Provenance Explorer
          </h1>
          <p className="mt-2 text-xs text-[#5c5953] max-w-2xl leading-relaxed">
            Every candidate skill, impact metric, and responsibility extracted from parsed documents is cataloged here with exact document coordinates and confidence ratings.
          </p>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="relative flex-1 max-w-md w-full">
            <label htmlFor="evidence-search-input" className="sr-only">
              Search evidence text, companies, or locations
            </label>
            <Search className="absolute left-3.5 top-3.5 h-3.5 w-3.5 text-[#5c5953]" />
            <input
              id="evidence-search-input"
              type="text"
              placeholder="Search evidence text, companies, or locations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded border border-[#ded9cc] bg-[#ffffff] pl-9 pr-3 py-2.5 text-xs text-[#181816] focus:border-[#181816] focus:outline-none shadow-sm min-h-[44px]"
            />
          </div>

          <span className="font-mono text-xs text-[#5c5953]">
            Cataloged: {filteredItems.length} entities
          </span>
        </div>

        {/* Evidence Feed */}
        {loading && evidence.length === 0 ? (
          <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-16 text-center text-xs text-[#5c5953]">
            <RefreshCw className="mx-auto h-5 w-5 animate-spin mb-3 text-[#181816]" />
            Loading grounded evidence graph...
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="rounded border border-[#ded9cc] bg-[#ffffff] p-12 text-center text-xs text-[#5c5953]">
            No evidence records found. Start an analysis to ingest candidate documents.
          </div>
        ) : (
          <div className="space-y-3" role="feed" aria-label="Evidence records">
            {filteredItems.map((item) => (
              <div
                key={item.id}
                className="rounded border border-[#e6e2d8] bg-[#ffffff] p-4 sm:p-5 shadow-editorial text-xs transition-colors hover:border-[#181816]"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#edeae1] pb-2.5 mb-2.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] font-bold text-[#181816] uppercase">
                      TYPE: {item.evidence_type}
                    </span>
                    <span className="rounded bg-[#f0f7f2] border border-[#cde4d3] px-1.5 py-0.5 text-[10px] font-semibold text-[#1f6339]">
                      ✓ GROUNDED
                    </span>
                  </div>
                  <span className="font-mono text-[11px] text-[#5c5953]">
                    Confidence: {(item.confidence * 100).toFixed(0)}%
                  </span>
                </div>

                <p className="text-[#181816] font-medium leading-relaxed mb-3">
                  &quot;{item.text}&quot;
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] font-mono text-[#5c5953] border-t border-[#edeae1] pt-2">
                  <div className="flex items-center gap-1.5">
                    <FileText className="h-3 w-3 text-[#5c5953]" />
                    <span>Source: </span>
                    <span className="text-[#181816]">{item.source_document || item.source_uri || "Resume"}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Layers className="h-3 w-3 text-[#5c5953]" />
                    <span>Location: </span>
                    <span className="text-[#181816]">{item.source_location || "Overview"}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

export default function EvidencePage() {
  return (
    <ProtectedRoute>
      <EvidenceExplorerContent />
    </ProtectedRoute>
  );
}
