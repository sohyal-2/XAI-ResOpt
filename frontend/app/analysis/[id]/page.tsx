"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { ProtectedRoute } from "@/features/auth/protected-route";
import { fetchBaselineReport, fetchAnalysisSummary } from "@/lib/api";
import type { BaselineReportResponse, AnalysisSummaryItem } from "@/types/api";

import { OverviewTab } from "@/features/analysis/overview-tab";
import { AtsTab } from "@/features/analysis/ats-tab";
import { SkillsTab } from "@/features/analysis/skills-tab";
import { EvidenceTab } from "@/features/analysis/evidence-tab";
import { ExplainTab } from "@/features/analysis/explain-tab";
import { RewriteTab } from "@/features/analysis/rewrite-tab";
import { ComparisonTab } from "@/features/analysis/comparison-tab";
import { AgentsTab } from "@/features/analysis/agents-tab";
import { HistoryTab } from "@/features/analysis/history-tab";
import { CopilotPanel } from "@/features/analysis/copilot-panel";

import {
  ArrowLeft,
  LayoutDashboard,
  Cpu,
  Layers,
  HelpCircle,
  Edit3,
  GitCompare,
  History,
  FileDown,
  ShieldCheck,
  RefreshCw,
  AlertTriangle,
  Menu,
  X,
  Sparkles,
} from "lucide-react";

export default function AnalysisWorkspacePage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();

  const analysisId = params?.id as string;
  const initialTab = searchParams?.get("tab") || "overview";

  const [activeTab, setActiveTab] = useState<string>(initialTab);
  const [report, setReport] = useState<BaselineReportResponse | null>(null);
  const [summary, setSummary] = useState<AnalysisSummaryItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [copilotOpen, setCopilotOpen] = useState(false);

  const loadAnalysisData = async () => {
    if (!analysisId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [reportData, summaryData] = await Promise.all([
        fetchBaselineReport(analysisId),
        fetchAnalysisSummary(analysisId).catch(() => null),
      ]);
      setReport(reportData);
      setSummary(summaryData);
    } catch (err: any) {
      setError(err.message || "Failed to load analysis workspace");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAnalysisData();
  }, [analysisId]);

  // Close modals on Escape key and lock body scroll when drawers are open
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setMobileMenuOpen(false);
        setCopilotOpen(false);
      }
    };
    if (mobileMenuOpen || copilotOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [mobileMenuOpen, copilotOpen]);

  const handleTabChange = (tabKey: string) => {
    setActiveTab(tabKey);
    setMobileMenuOpen(false);
  };

  const navTabs = [
    { key: "overview", label: "Overview", icon: LayoutDashboard },
    { key: "explain", label: "Explain & Gaps", icon: HelpCircle },
    { key: "rewrite", label: "Optimizer & Review", icon: Edit3 },
    { key: "comparison", label: "Before vs After", icon: GitCompare },
    { key: "ats", label: "ATS Invariants", icon: ShieldCheck },
    { key: "skills", label: "Skills Coverage", icon: Layers },
    { key: "history", label: "Version History", icon: History },
  ];

  if (isLoading && !report) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#fcfbf7] text-xs text-[#5c5953]">
        <div className="flex items-center gap-3">
          <RefreshCw className="h-5 w-5 animate-spin text-[#181816]" />
          <span>Loading Analysis Workspace...</span>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#fcfbf7] p-6 text-xs">
        <div className="w-full max-w-md rounded border border-[#f7d0ca] bg-[#ffffff] p-8 text-center shadow-editorial">
          <AlertTriangle className="mx-auto h-8 w-8 text-[#942e23] mb-2" />
          <h2 className="font-serif text-lg font-normal text-[#181816]">Workspace Error</h2>
          <p className="mt-1 text-[#5c5953] mb-4">{error}</p>
          <div className="flex justify-center gap-3">
            <button
              onClick={loadAnalysisData}
              className="rounded bg-[#181816] px-4 py-2 text-xs font-medium text-[#fcfbf7] hover:bg-[#2b2926] min-h-[44px]"
            >
              Retry
            </button>
            <Link
              href="/dashboard"
              className="rounded border border-[#ded9cc] bg-[#f7f5ef] px-4 py-2 text-xs font-medium text-[#181816] min-h-[44px] flex items-center"
            >
              Back to Dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-[#fcfbf7] text-[#181816]">
        {/* Workspace Top Bar */}
        <header className="sticky top-0 z-40 border-b border-[#e6e2d8] bg-[#fcfbf7]/95 backdrop-blur-sm">
          <div className="mx-auto flex max-w-7xl 2xl:max-w-[1700px] items-center justify-between px-4 py-3 sm:px-6">
            <div className="flex items-center gap-3 sm:gap-4 overflow-hidden">
              <Link
                href="/dashboard"
                className="flex items-center gap-1.5 text-xs font-medium text-[#5c5953] hover:text-[#181816] transition-colors shrink-0 py-1 min-h-[40px]"
                aria-label="Back to dashboard"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Dashboard</span>
              </Link>
              <span className="text-[#ded9cc]">/</span>
              <div className="min-w-0">
                <h1 className="text-xs font-semibold text-[#181816] truncate max-w-[160px] sm:max-w-xs md:max-w-md">
                  {summary?.job_title || "Target Role Analysis"}
                </h1>
                <span className="font-mono text-[10px] text-[#5c5953] block truncate">
                  Resume: {summary?.resume_title || "Candidate Profile"}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2 sm:gap-3 shrink-0">
              {/* Overall Score Pill */}
              <div className="flex items-center gap-1.5 sm:gap-2 rounded border border-[#e6e2d8] bg-[#ffffff] px-2.5 py-1 text-xs shadow-editorial">
                <span className="hidden sm:inline font-mono text-[10px] uppercase text-[#5c5953]">ATS</span>
                <span className="font-mono font-bold text-[#181816]">
                  {report.overall_score.toFixed(1)}%
                </span>
              </div>

              {/* Export Button */}
              <Link
                href={`/resumes/export?versionId=${summary?.resume_version_id || report.resume_version_id}`}
                className="flex items-center justify-center gap-1.5 rounded bg-[#181816] px-3 py-1.5 text-xs font-medium text-[#fcfbf7] hover:bg-[#2b2926] transition-colors shadow-sm min-h-[38px]"
                title="Export Resume"
              >
                <FileDown className="h-3.5 w-3.5" />
                <span className="hidden md:inline">Export Resume</span>
              </Link>

              {/* Mobile Copilot Trigger Button */}
              <button
                onClick={() => setCopilotOpen(true)}
                className="flex items-center gap-1 rounded border border-[#181816] bg-[#181816] px-2.5 py-1.5 text-xs font-medium text-[#fcfbf7] lg:hidden min-h-[38px] shadow-sm"
                aria-label="Open AI Copilot"
              >
                <Sparkles className="h-3.5 w-3.5" />
                <span className="hidden xs:inline">Copilot</span>
              </button>

              {/* Mobile Menu Drawer Trigger Button */}
              <button
                onClick={() => setMobileMenuOpen(true)}
                className="flex items-center justify-center rounded border border-[#ded9cc] bg-[#f7f5ef] p-2 text-[#181816] lg:hidden min-h-[44px] min-w-[44px]"
                aria-label="Open workspace navigation"
                aria-expanded={mobileMenuOpen}
              >
                <Menu className="h-4 w-4" />
              </button>
            </div>
          </div>
        </header>

        {/* Mobile Navigation Drawer */}
        {mobileMenuOpen && (
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Workspace Navigation"
            className="fixed inset-0 z-50 flex lg:hidden"
          >
            <div
              onClick={() => setMobileMenuOpen(false)}
              className="fixed inset-0 bg-[#181816]/40 backdrop-blur-xs transition-opacity"
              aria-hidden="true"
            />
            <div className="relative z-10 flex h-full w-4/5 max-w-xs flex-col border-r border-[#ded9cc] bg-[#ffffff] p-5 shadow-popup overflow-y-auto">
              <div className="flex items-center justify-between border-b border-[#edeae1] pb-3 mb-4">
                <div className="flex items-center gap-2">
                  <span className="flex h-6 w-6 items-center justify-center rounded bg-[#181816] text-[10px] font-bold text-[#fcfbf7]">
                    X
                  </span>
                  <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[#181816]">
                    Analysis Navigation
                  </span>
                </div>
                <button
                  onClick={() => setMobileMenuOpen(false)}
                  className="flex items-center justify-center rounded p-1.5 text-[#5c5953] hover:bg-[#f7f5ef] hover:text-[#181816] min-h-[44px] min-w-[44px]"
                  aria-label="Close navigation drawer"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Context Summary Card */}
              <div className="rounded border border-[#e6e2d8] bg-[#fcfbf7] p-4 text-xs mb-4">
                <span className="font-mono text-[10px] uppercase text-[#5c5953] tracking-wider block mb-1">
                  Analysis Context
                </span>
                <h2 className="font-semibold text-xs text-[#181816] leading-snug">
                  {summary?.job_title || "Target Role"}
                </h2>
                <div className="mt-2 space-y-1 text-[11px] font-mono text-[#5c5953] border-t border-[#edeae1] pt-2">
                  <div>
                    <span className="text-[#5c5953]">Score: </span>
                    <span className="text-[#181816] font-bold">{report.overall_score.toFixed(1)}%</span>
                  </div>
                  <div>
                    <span className="text-[#5c5953]">Confidence: </span>
                    <span className="text-[#181816]">{(report.evidence_confidence * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </div>

              {/* 9 Tab Links */}
              <nav className="space-y-1" aria-label="Workspace tabs navigation">
                {navTabs.map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.key;
                  return (
                    <button
                      key={tab.key}
                      onClick={() => handleTabChange(tab.key)}
                      className={`flex w-full items-center justify-between rounded px-3 py-2.5 text-xs font-medium transition-colors min-h-[44px] ${
                        isActive
                          ? "bg-[#181816] text-[#fcfbf7]"
                          : "text-[#5c5953] hover:bg-[#f7f5ef] hover:text-[#181816]"
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <Icon className="h-4 w-4" />
                        <span>{tab.label}</span>
                      </div>
                      {tab.key === "rewrite" && (
                        <span
                          className={`rounded px-1.5 py-0.2 font-mono text-[10px] ${
                            isActive ? "bg-[#2b2926] text-[#fcfbf7]" : "bg-[#f7f5ef] text-[#5c5953]"
                          }`}
                        >
                          Review
                        </span>
                      )}
                    </button>
                  );
                })}
              </nav>

              {/* Quick Actions */}
              <div className="mt-auto border-t border-[#edeae1] pt-4 space-y-2 text-xs">
                <Link
                  href={`/resumes/export?versionId=${summary?.resume_version_id || report.resume_version_id}`}
                  className="flex items-center justify-between text-[#181816] hover:underline font-medium min-h-[40px] px-2"
                >
                  <span>Export Resume</span>
                  <FileDown className="h-4 w-4" />
                </Link>
                <Link
                  href="/evidence"
                  className="flex items-center justify-between text-[#181816] hover:underline font-medium min-h-[40px] px-2"
                >
                  <span>Global Evidence</span>
                  <Layers className="h-4 w-4" />
                </Link>
              </div>
            </div>
          </div>
        )}

        {/* Mobile Copilot Slide-Over Drawer */}
        {copilotOpen && (
          <div
            role="dialog"
            aria-modal="true"
            aria-label="AI Copilot"
            className="fixed inset-0 z-50 flex justify-end lg:hidden"
          >
            <div
              onClick={() => setCopilotOpen(false)}
              className="fixed inset-0 bg-[#181816]/40 backdrop-blur-xs transition-opacity"
              aria-hidden="true"
            />
            <div className="relative z-10 flex h-full w-full max-w-md flex-col bg-[#ffffff] shadow-popup">
              <CopilotPanel
                analysisId={analysisId}
                onNavigateTab={handleTabChange}
                onClose={() => setCopilotOpen(false)}
              />
            </div>
          </div>
        )}

        {/* Floating Copilot Trigger Button on Mobile */}
        <button
          onClick={() => setCopilotOpen(true)}
          className="fixed bottom-5 right-5 z-30 flex items-center gap-2 rounded-full bg-[#181816] text-[#fcfbf7] px-4 py-3 shadow-lg hover:bg-[#2b2926] transition-transform active:scale-95 lg:hidden min-h-[48px]"
          aria-label="Open AI Copilot"
        >
          <Sparkles className="h-4 w-4" />
          <span className="text-xs font-medium">Copilot</span>
        </button>

        {/* 3-Column Main Workspace Container */}
        <div className="mx-auto max-w-7xl 2xl:max-w-[1700px] px-4 py-6 sm:px-6">
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 items-start">
            {/* LEFT COLUMN: Navigation & Context (3 Cols on >= lg) */}
            <aside className="hidden lg:block lg:col-span-3 space-y-4 sticky top-20">
              {/* Context Summary Card */}
              <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 shadow-editorial text-xs">
                <span className="font-mono text-[10px] uppercase text-[#5c5953] tracking-wider block mb-1">
                  Analysis Context
                </span>
                <h2 className="font-medium text-sm text-[#181816] leading-snug">
                  {summary?.job_title || "Target Role"}
                </h2>
                <div className="mt-3 space-y-1.5 text-[11px] font-mono text-[#5c5953] border-t border-[#edeae1] pt-3">
                  <div>
                    <span className="text-[#5c5953]">Status: </span>
                    <span className="text-[#1f6339] font-semibold">{report.status.toUpperCase()}</span>
                  </div>
                  <div>
                    <span className="text-[#5c5953]">Evidence backing: </span>
                    <span className="text-[#181816]">{(report.evidence_confidence * 100).toFixed(0)}%</span>
                  </div>
                  <div>
                    <span className="text-[#5c5953]">Analysis ID: </span>
                    <span className="text-[#181816]">{analysisId.slice(0, 8)}...</span>
                  </div>
                </div>
              </div>

              {/* 9-Tab Navigation Menu */}
              <nav aria-label="Analysis tab navigation" className="rounded border border-[#e6e2d8] bg-[#ffffff] p-2 shadow-editorial space-y-1">
                {navTabs.map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.key;
                  return (
                    <button
                      key={tab.key}
                      onClick={() => handleTabChange(tab.key)}
                      className={`flex w-full items-center justify-between rounded px-3 py-2 text-xs font-medium transition-colors min-h-[40px] ${
                        isActive
                          ? "bg-[#181816] text-[#fcfbf7]"
                          : "text-[#5c5953] hover:bg-[#f7f5ef] hover:text-[#181816]"
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <Icon className="h-3.5 w-3.5" />
                        <span>{tab.label}</span>
                      </div>
                      {tab.key === "rewrite" && (
                        <span
                          className={`rounded px-1.5 py-0.2 font-mono text-[10px] ${
                            isActive ? "bg-[#2b2926] text-[#fcfbf7]" : "bg-[#f7f5ef] text-[#5c5953]"
                          }`}
                        >
                          Review
                        </span>
                      )}
                    </button>
                  );
                })}
              </nav>

              {/* Quick Links */}
              <div className="rounded border border-[#ded9cc] bg-[#f7f5ef] p-4 text-xs">
                <span className="font-mono text-[10px] uppercase text-[#5c5953] block mb-2 font-bold">
                  Quick Actions
                </span>
                <div className="space-y-2">
                  <Link
                    href={`/resumes/export?versionId=${summary?.resume_version_id || report.resume_version_id}`}
                    className="flex items-center justify-between text-[#181816] hover:underline font-medium py-1"
                  >
                    <span>Deterministic Resume Export</span>
                    <FileDown className="h-3.5 w-3.5" />
                  </Link>
                  <Link
                    href="/evidence"
                    className="flex items-center justify-between text-[#181816] hover:underline font-medium py-1"
                  >
                    <span>Global Evidence Graph</span>
                    <Layers className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </div>
            </aside>

            {/* CENTER COLUMN: Tabbed Analysis / Results (6 Cols on >= lg, full width on < lg) */}
            <main className="w-full lg:col-span-6 space-y-6">
              {activeTab === "overview" && (
                <OverviewTab report={report} onNavigateTab={handleTabChange} />
              )}
              {activeTab === "ats" && <AtsTab report={report} />}
              {activeTab === "skills" && (
                <SkillsTab report={report} onNavigateTab={handleTabChange} />
              )}
              {activeTab === "evidence" && <EvidenceTab report={report} />}
              {activeTab === "explain" && (
                <ExplainTab report={report} onNavigateTab={handleTabChange} />
              )}
              {activeTab === "rewrite" && (
                <RewriteTab analysisId={analysisId} onNavigateTab={handleTabChange} />
              )}
              {activeTab === "comparison" && (
                <ComparisonTab
                  analysisId={analysisId}
                  baselineReport={report}
                  onNavigateTab={handleTabChange}
                />
              )}
              {activeTab === "agents" && <AgentsTab analysisId={analysisId} />}
              {activeTab === "history" && <HistoryTab analysisId={analysisId} />}
            </main>

            {/* RIGHT COLUMN: AI Copilot (3 Cols on >= lg, hidden on < lg because accessible via drawer) */}
            <div className="hidden lg:block lg:col-span-3 h-[calc(100vh-6rem)] sticky top-20">
              <CopilotPanel analysisId={analysisId} onNavigateTab={handleTabChange} />
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}
