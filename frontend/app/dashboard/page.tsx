"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ProtectedRoute } from "@/features/auth/protected-route";
import { useAuth } from "@/features/auth/auth-provider";
import { fetchAnalyses, fetchResumes } from "@/lib/api";
import type { AnalysisSummaryItem, ResumeSummaryItem } from "@/types/api";
import {
  ArrowRight,
  Plus,
  FileText,
  Clock,
  Sparkles,
  Layers,
  ChevronRight,
  RefreshCw,
  LogOut,
  Settings,
  ShieldCheck,
  Menu,
  X,
} from "lucide-react";

function DashboardContent() {
  const router = useRouter();
  const { user, logout } = useAuth();

  const [analyses, setAnalyses] = useState<AnalysisSummaryItem[]>([]);
  const [resumes, setResumes] = useState<ResumeSummaryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Close drawer on Escape and lock scroll
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileMenuOpen(false);
    };
    if (mobileMenuOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [mobileMenuOpen]);

  const loadDashboardData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [analysesData, resumesData] = await Promise.all([
        fetchAnalyses().catch(() => []),
        fetchResumes().catch(() => []),
      ]);
      setAnalyses(analysesData);
      setResumes(resumesData);
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard data");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  // Calculate high-level summary metrics
  const totalAnalyses = analyses.length;
  const scoredAnalyses = analyses.filter((a) => a.overall_score !== null && a.overall_score !== undefined);
  const avgScore = scoredAnalyses.length > 0
    ? scoredAnalyses.reduce((acc, a) => acc + (a.overall_score || 0), 0) / scoredAnalyses.length
    : null;

  return (
    <main className="min-h-screen bg-[#fcfbf7] text-[#181816]">
      {/* Top Header */}
      <header className="sticky top-0 z-40 border-b border-[#e6e2d8] bg-[#fcfbf7]/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 sm:py-4">
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-2 rounded focus-visible:ring-2 focus-visible:ring-[#181816]">
              <span className="flex h-7 w-7 items-center justify-center rounded bg-[#181816] text-xs font-bold text-[#fcfbf7]">
                X
              </span>
              <span className="font-mono text-sm font-semibold tracking-wider uppercase text-[#181816]">
                XAI-ResOpt
              </span>
            </Link>
            <nav aria-label="Main navigation" className="hidden items-center gap-5 text-xs font-medium text-[#5c5953] md:flex">
              <Link href="/dashboard" className="text-[#181816] font-semibold py-2">Dashboard</Link>
              <Link href="/analysis/new" className="hover:text-[#181816] transition-colors py-2">New Analysis</Link>
              <Link href="/evidence" className="hover:text-[#181816] transition-colors py-2">Evidence</Link>
              <Link href="/settings" className="hover:text-[#181816] transition-colors py-2">Settings</Link>
            </nav>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <span className="hidden text-xs text-[#5c5953] lg:inline font-mono">
              {user?.full_name || user?.email}
            </span>
            <Link
              href="/analysis/new"
              className="flex items-center gap-1.5 rounded bg-[#181816] px-3.5 py-2 text-xs font-medium text-[#fcfbf7] hover:bg-[#2b2926] transition-colors shadow-sm min-h-[40px]"
            >
              <Plus className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">New Analysis</span>
            </Link>
            <button
              onClick={handleLogout}
              className="hidden sm:inline-flex items-center justify-center rounded border border-[#ded9cc] bg-[#f7f5ef] p-2 text-[#5c5953] hover:text-[#181816] hover:bg-[#eae6dd] transition-colors min-h-[40px] min-w-[40px]"
              aria-label="Sign out"
              title="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="inline-flex items-center justify-center rounded border border-[#ded9cc] bg-[#f7f5ef] p-2 text-[#181816] hover:bg-[#eae6dd] md:hidden min-h-[44px] min-w-[44px]"
              aria-label="Open mobile dashboard menu"
              aria-expanded={mobileMenuOpen}
              aria-controls="mobile-dashboard-drawer"
            >
              <Menu className="h-5 w-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div
          id="mobile-dashboard-drawer"
          role="dialog"
          aria-modal="true"
          aria-label="Dashboard Navigation Menu"
          className="fixed inset-0 z-50 flex justify-end md:hidden"
        >
          <div
            onClick={() => setMobileMenuOpen(false)}
            className="fixed inset-0 bg-[#181816]/40 backdrop-blur-xs transition-opacity"
            aria-hidden="true"
          />
          <div className="relative z-10 flex h-full w-4/5 max-w-xs flex-col border-l border-[#ded9cc] bg-[#ffffff] p-6 shadow-popup">
            <div className="flex items-center justify-between border-b border-[#edeae1] pb-4">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded bg-[#181816] text-[11px] font-bold text-[#fcfbf7]">
                  X
                </span>
                <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[#181816]">
                  Workspace
                </span>
              </div>
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center justify-center rounded p-2 text-[#5c5953] hover:bg-[#f7f5ef] hover:text-[#181816] min-h-[44px] min-w-[44px]"
                aria-label="Close dashboard menu"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="py-3 border-b border-[#edeae1]">
              <span className="block text-[11px] font-mono text-[#5c5953] truncate">
                {user?.full_name || user?.email}
              </span>
            </div>

            <nav className="mt-4 flex flex-col space-y-2" aria-label="Mobile workspace navigation">
              <Link
                href="/dashboard"
                onClick={() => setMobileMenuOpen(false)}
                className="rounded px-3 py-2.5 text-sm font-semibold text-[#181816] bg-[#f7f5ef] min-h-[44px] flex items-center"
              >
                Dashboard
              </Link>
              <Link
                href="/analysis/new"
                onClick={() => setMobileMenuOpen(false)}
                className="rounded px-3 py-2.5 text-sm font-medium text-[#181816] hover:bg-[#f7f5ef] min-h-[44px] flex items-center"
              >
                New Analysis
              </Link>
              <Link
                href="/evidence"
                onClick={() => setMobileMenuOpen(false)}
                className="rounded px-3 py-2.5 text-sm font-medium text-[#181816] hover:bg-[#f7f5ef] min-h-[44px] flex items-center"
              >
                Evidence Explorer
              </Link>
              <Link
                href="/settings"
                onClick={() => setMobileMenuOpen(false)}
                className="rounded px-3 py-2.5 text-sm font-medium text-[#181816] hover:bg-[#f7f5ef] min-h-[44px] flex items-center"
              >
                Settings
              </Link>
            </nav>

            <div className="mt-auto border-t border-[#edeae1] pt-6 space-y-3">
              <button
                onClick={handleLogout}
                className="flex w-full items-center justify-center gap-2 rounded border border-[#ded9cc] bg-[#f7f5ef] px-4 py-3 text-sm font-medium text-[#942e23] hover:bg-[#fdf2f0] min-h-[44px]"
              >
                <LogOut className="h-4 w-4" />
                Sign Out
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Workspace Body */}
      <div className="mx-auto max-w-7xl 2xl:max-w-[1700px] px-4 sm:px-6 py-8 sm:py-10 space-y-8 sm:space-y-10">
        <div>
          <h1 className="font-serif text-2xl sm:text-3xl font-normal text-[#181816]">
            Candidate Resume Workspace
          </h1>
          <p className="mt-1 text-xs sm:text-sm text-[#5c5953]">
            Track explainable analyses, deterministic ATS scores, and verified resume versions.
          </p>
        </div>

        {/* Executive Stats Cards */}
        <section aria-label="Executive Overview">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 shadow-editorial">
              <span className="text-[11px] font-mono uppercase tracking-wider text-[#5c5953]">Total Analyses</span>
              <p className="mt-2 text-2xl font-serif font-normal text-[#181816]">{totalAnalyses}</p>
              <span className="mt-1 block text-xs text-[#5c5953]">Multi-agent workflows</span>
            </div>

            <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 shadow-editorial">
              <span className="text-[11px] font-mono uppercase tracking-wider text-[#5c5953]">Average ATS Score</span>
              <p className="mt-2 text-2xl font-serif font-normal text-[#181816]">
                {avgScore !== null ? `${avgScore.toFixed(1)}%` : "—"}
              </p>
              <span className="mt-1 block text-xs text-[#5c5953]">Deterministic compatibility</span>
            </div>

            <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 shadow-editorial">
              <span className="text-[11px] font-mono uppercase tracking-wider text-[#5c5953]">Resumes Tracked</span>
              <p className="mt-2 text-2xl font-serif font-normal text-[#181816]">{resumes.length}</p>
              <span className="mt-1 block text-xs text-[#5c5953]">With version history</span>
            </div>

            <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 shadow-editorial">
              <span className="text-[11px] font-mono uppercase tracking-wider text-[#5c5953]">Factual Guarantee</span>
              <p className="mt-2 text-2xl font-serif font-normal text-[#1f6339] flex items-center gap-1.5">
                <ShieldCheck className="h-5 w-5" />
                100% Verified
              </p>
              <span className="mt-1 block text-xs text-[#5c5953]">Zero hallucination invariant</span>
            </div>
          </div>
        </section>

        {/* Error Notification Banner */}
        {error && (
          <div className="flex items-center justify-between rounded border border-[#f7d0ca] bg-[#fdf2f0] p-4 text-xs text-[#942e23]" role="alert">
            <span>{error}</span>
            <button onClick={loadDashboardData} className="underline font-semibold min-h-[44px] px-2 flex items-center">Retry</button>
          </div>
        )}

        {/* Main 2-Column Split: Analyses vs Resumes & Evidence */}
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 items-start">
          {/* Left Column: Recent Analyses (8 Cols) */}
          <section className="lg:col-span-8 space-y-4" aria-labelledby="analyses-heading">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e6e2d8] pb-3">
              <div>
                <h2 id="analyses-heading" className="font-serif text-xl font-normal text-[#181816]">
                  Recent Analyses
                </h2>
                <p className="text-xs text-[#5c5953]">All evaluation and optimization sessions</p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={loadDashboardData}
                  className="rounded border border-[#ded9cc] bg-[#f7f5ef] p-2 text-[#5c5953] hover:text-[#181816] min-h-[44px] min-w-[44px] flex items-center justify-center"
                  aria-label="Refresh analyses"
                  title="Refresh analyses"
                >
                  <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
                </button>
                <Link
                  href="/analysis/new"
                  className="rounded bg-[#181816] px-3.5 py-2 text-xs font-medium text-[#fcfbf7] hover:bg-[#2b2926] min-h-[44px] flex items-center"
                >
                  New Analysis
                </Link>
              </div>
            </div>

            {isLoading && analyses.length === 0 ? (
              <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-12 text-center text-xs text-[#5c5953]">
                <RefreshCw className="mx-auto h-5 w-5 animate-spin mb-2" />
                Loading analyses...
              </div>
            ) : analyses.length === 0 ? (
              <div className="rounded border border-[#ded9cc] border-dashed bg-[#f7f5ef] p-8 sm:p-12 text-center">
                <FileText className="mx-auto h-8 w-8 text-[#5c5953] mb-3" />
                <h3 className="font-medium text-sm text-[#181816]">No analyses conducted yet</h3>
                <p className="mt-1 text-xs text-[#5c5953] max-w-sm mx-auto">
                  Upload your resume and a job description to initiate the 11-agent explainable evaluation pipeline.
                </p>
                <Link
                  href="/analysis/new"
                  className="mt-5 inline-flex items-center gap-1.5 rounded bg-[#181816] px-4 py-2.5 text-xs font-medium text-[#fcfbf7] hover:bg-[#2b2926] min-h-[44px]"
                >
                  Start First Analysis
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {analyses.map((item) => (
                  <Link
                    key={item.id}
                    href={`/analysis/${item.id}`}
                    className="group block rounded border border-[#e6e2d8] bg-[#ffffff] p-4 sm:p-5 shadow-editorial hover:border-[#181816] transition-all"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="text-sm font-semibold text-[#181816] group-hover:underline">
                            {item.job_title || "Target Job Position"}
                          </h3>
                          <span
                            className={`rounded px-2 py-0.5 text-[10px] font-semibold border ${
                              item.status === "completed"
                                ? "bg-[#f0f7f2] text-[#1f6339] border-[#cde4d3]"
                                : item.status === "running"
                                ? "bg-[#fdf8ee] text-[#8c6218] border-[#fae8be]"
                                : "bg-[#f7f5ef] text-[#5c5953] border-[#ded9cc]"
                            }`}
                          >
                            {item.status.toUpperCase()}
                          </span>
                        </div>
                        <p className="mt-1 text-xs text-[#5c5953]">
                          Resume: <span className="font-medium text-[#181816]">{item.resume_title || "Candidate Profile"}</span>
                        </p>
                      </div>

                      <div className="flex items-center gap-4">
                        {item.overall_score !== null && (
                          <div className="text-right">
                            <span className="text-[10px] font-mono text-[#5c5953] uppercase">ATS Score</span>
                            <p className="text-lg font-serif font-normal text-[#181816]">
                              {item.overall_score.toFixed(1)}%
                            </p>
                          </div>
                        )}
                        <ChevronRight className="h-4 w-4 text-[#5c5953] group-hover:text-[#181816] transition-colors" />
                      </div>
                    </div>

                    <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-[#edeae1] pt-3 text-[11px] text-[#5c5953]">
                      <div className="flex flex-wrap items-center gap-3">
                        <span className="flex items-center gap-1 font-mono">
                          <Clock className="h-3 w-3" />
                          {new Date(item.created_at).toLocaleDateString(undefined, {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                          })}
                        </span>
                        <span className="font-mono">ID: {item.id.slice(0, 8)}...</span>
                      </div>
                      <span className="text-xs font-medium text-[#181816] group-hover:underline flex items-center gap-1 min-h-[32px]">
                        Open Workspace <ArrowRight className="h-3 w-3" />
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </section>

          {/* Right Column: Resumes & Version History (4 Cols) */}
          <section className="lg:col-span-4 space-y-6" aria-labelledby="resumes-heading">
            <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 shadow-editorial">
              <div className="flex items-center justify-between border-b border-[#edeae1] pb-3">
                <h2 id="resumes-heading" className="font-serif text-lg font-normal text-[#181816]">
                  Active Resumes
                </h2>
                <Link
                  href="/analysis/new"
                  className="font-mono text-[11px] text-[#5c5953] hover:text-[#181816] underline py-1 min-h-[36px] flex items-center"
                >
                  Upload New
                </Link>
              </div>

              {resumes.length === 0 ? (
                <div className="py-6 text-center text-xs text-[#5c5953]">
                  No resumes ingested yet.
                </div>
              ) : (
                <div className="mt-4 space-y-3">
                  {resumes.map((r) => (
                    <div key={r.id} className="rounded border border-[#edeae1] bg-[#fcfbf7] p-3 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-[#181816]">{r.title}</span>
                        {r.is_final && (
                          <span className="rounded bg-[#f0f7f2] px-1.5 py-0.5 text-[10px] text-[#1f6339] border border-[#cde4d3]">
                            Finalized
                          </span>
                        )}
                      </div>
                      <div className="mt-2 flex items-center justify-between text-[11px] text-[#5c5953]">
                        <span>{r.versions_count} version{r.versions_count !== 1 ? "s" : ""}</span>
                        {r.latest_version_id && (
                          <Link
                            href={`/resumes/export?versionId=${r.latest_version_id}`}
                            className="text-[#181816] hover:underline flex items-center gap-1 font-medium py-1"
                          >
                            Export PDF <ArrowRight className="h-2.5 w-2.5" />
                          </Link>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Evidence Quick Jump Card */}
            <div className="rounded border border-[#ded9cc] bg-[#f7f5ef] p-5 sm:p-6">
              <div className="flex items-center gap-2 mb-2">
                <Layers className="h-4 w-4 text-[#181816]" />
                <h3 className="font-medium text-sm text-[#181816]">Evidence Explorer</h3>
              </div>
              <p className="text-xs text-[#5c5953] leading-relaxed">
                Inspect candidate assertions, confidence ratings, and provenance linkages across all past documents.
              </p>
              <Link
                href="/evidence"
                className="mt-4 inline-flex items-center gap-1.5 rounded border border-[#ded9cc] bg-[#ffffff] px-4 py-2.5 text-xs font-medium text-[#181816] hover:bg-[#eae6dd] transition-colors min-h-[44px]"
              >
                Browse Global Evidence Graph
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}