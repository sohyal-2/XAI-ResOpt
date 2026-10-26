"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ProtectedRoute } from "@/features/auth/protected-route";
import { useAuth } from "@/features/auth/auth-provider";
import { ingestResume, triggerBaselineAnalysis, fetchBaselineReport } from "@/lib/api";
import type { BaselineReportResponse } from "@/types/api";
import { AtsTab } from "@/features/analysis/ats-tab";
import {
  Sparkles,
  Upload,
  FileText,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  ArrowRight,
  RefreshCw,
  ShieldCheck,
  Layers,
  RotateCcw,
  FileCheck,
  Check,
  ChevronRight,
  LogOut,
  Menu,
  X,
  FileCode,
  Sliders,
  ExternalLink,
} from "lucide-react";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function AtsCheckerContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, logout } = useAuth();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  // Upload input states
  const [uploadMode, setUploadMode] = useState<"file" | "text">("file");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [pastedText, setPastedText] = useState("");

  // Audit Execution state
  const [isScanning, setIsScanning] = useState(false);
  const [scanStepIndex, setScanStepIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Result state
  const [report, setReport] = useState<BaselineReportResponse | null>(null);
  const [currentAnalysisId, setCurrentAnalysisId] = useState<string | null>(null);

  const scanSteps = [
    "Extracting digital text layer & parsing section hierarchy...",
    "Scanning layout for multi-columns, nested tables, & text box traps...",
    "Auditing action verbs, quantifiable metrics (Google X-Y-Z formula), & repetition...",
    "Verifying contact coordinates & professional profile links...",
    "Synthesizing 5-pillar ATS scores & generating prioritized fix plan...",
  ];

  // If analysisId is provided in URL, load it directly
  useEffect(() => {
    const analysisId = searchParams.get("analysisId");
    if (analysisId) {
      setCurrentAnalysisId(analysisId);
      setIsScanning(true);
      fetchBaselineReport(analysisId)
        .then((data: BaselineReportResponse) => {
          setReport(data);
        })
        .catch((err: any) => {
          setError(err.message || "Failed to load resume analysis report.");
        })
        .finally(() => {
          setIsScanning(false);
        });
    }
  }, [searchParams]);

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    setError(null);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (!["pdf", "docx", "txt"].includes(ext || "")) {
        setError("Unsupported file format. Please upload a PDF, DOCX, or TXT file.");
        return;
      }
      setResumeFile(file);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    if (e.target.files && e.target.files.length > 0) {
      setResumeFile(e.target.files[0]);
    }
  };

  const handleRunAudit = async () => {
    setError(null);
    if (uploadMode === "file" && !resumeFile) {
      setError("Please select or drop a PDF or DOCX resume to check.");
      return;
    }
    if (uploadMode === "text" && !pastedText.trim()) {
      setError("Please paste your resume plain text.");
      return;
    }

    try {
      setIsScanning(true);
      setScanStepIndex(0);

      // Step interval animation
      const interval = setInterval(() => {
        setScanStepIndex((prev) => (prev < scanSteps.length - 1 ? prev + 1 : prev));
      }, 700);

      let fileToUpload = resumeFile;
      if (uploadMode === "text" || !fileToUpload) {
        const blob = new Blob([pastedText], { type: "text/plain" });
        fileToUpload = new File([blob], "resume.txt", { type: "text/plain" });
      }

      // 1. Ingest Resume
      const res = await ingestResume(fileToUpload);

      // 2. Trigger Standalone Baseline ATS Analysis (No Job Description)
      const baselineReport = await triggerBaselineAnalysis({
        resume_id: res.id,
      });

      clearInterval(interval);
      setReport(baselineReport);
      setCurrentAnalysisId(baselineReport.analysis_id);
    } catch (err: any) {
      setError(err.message || "Failed to run ATS resume check.");
    } finally {
      setIsScanning(false);
    }
  };

  const handleReset = () => {
    setReport(null);
    setCurrentAnalysisId(null);
    setResumeFile(null);
    setPastedText("");
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    router.replace("/ats-checker");
  };

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };

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
              <Link href="/dashboard" className="hover:text-[#181816] transition-colors py-2">
                Dashboard
              </Link>
              <Link
                href="/ats-checker"
                className="text-[#181816] font-semibold flex items-center gap-1.5 py-2 border-b-2 border-[#181816]"
              >
                <Sparkles className="h-3 w-3 text-[#181816]" />
                ATS Checker
              </Link>
              <Link href="/analysis/new" className="hover:text-[#181816] transition-colors py-2">
                Job Match Analysis
              </Link>
              <Link href="/evidence" className="hover:text-[#181816] transition-colors py-2">
                Evidence
              </Link>
              <Link href="/settings" className="hover:text-[#181816] transition-colors py-2">
                Settings
              </Link>
            </nav>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <span className="hidden text-xs text-[#5c5953] lg:inline font-mono">
              {user?.full_name || user?.email}
            </span>
            <Link
              href="/analysis/new"
              className="hidden sm:flex items-center gap-1.5 rounded border border-[#ded9cc] bg-[#f7f5ef] px-3.5 py-2 text-xs font-medium text-[#181816] hover:bg-[#eae6dd] transition-colors min-h-[40px]"
            >
              Job Match
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
              aria-label="Open navigation menu"
            >
              <Menu className="h-5 w-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 flex justify-end md:hidden" role="dialog" aria-modal="true">
          <div
            onClick={() => setMobileMenuOpen(false)}
            className="fixed inset-0 bg-[#181816]/40 backdrop-blur-xs"
            aria-hidden="true"
          />
          <div className="relative z-10 flex h-full w-4/5 max-w-xs flex-col border-l border-[#ded9cc] bg-[#ffffff] p-6 shadow-popup">
            <div className="flex items-center justify-between border-b border-[#edeae1] pb-4">
              <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[#181816]">
                Workspace Menu
              </span>
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center justify-center rounded p-2 text-[#5c5953] hover:bg-[#f7f5ef] min-h-[44px] min-w-[44px]"
                aria-label="Close menu"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <nav className="mt-4 flex flex-col space-y-2">
              <Link
                href="/dashboard"
                onClick={() => setMobileMenuOpen(false)}
                className="rounded px-3 py-2.5 text-sm font-medium text-[#181816] hover:bg-[#f7f5ef] min-h-[44px] flex items-center"
              >
                Dashboard
              </Link>
              <Link
                href="/ats-checker"
                onClick={() => setMobileMenuOpen(false)}
                className="rounded px-3 py-2.5 text-sm font-semibold text-[#181816] bg-[#f7f5ef] min-h-[44px] flex items-center gap-2"
              >
                <Sparkles className="h-4 w-4" />
                ATS Checker
              </Link>
              <Link
                href="/analysis/new"
                onClick={() => setMobileMenuOpen(false)}
                className="rounded px-3 py-2.5 text-sm font-medium text-[#181816] hover:bg-[#f7f5ef] min-h-[44px] flex items-center"
              >
                Job Match Analysis
              </Link>
              <Link
                href="/evidence"
                onClick={() => setMobileMenuOpen(false)}
                className="rounded px-3 py-2.5 text-sm font-medium text-[#181816] hover:bg-[#f7f5ef] min-h-[44px] flex items-center"
              >
                Evidence Explorer
              </Link>
            </nav>
            <div className="mt-auto border-t border-[#edeae1] pt-6">
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

      {/* Main Container */}
      <div className="mx-auto max-w-7xl px-4 sm:px-6 py-8 sm:py-12 space-y-8">
        {/* Error Alert */}
        {error && (
          <div
            className="flex items-center justify-between rounded border border-[#f7d0ca] bg-[#fdf2f0] p-4 text-xs text-[#942e23]"
            role="alert"
          >
            <div className="flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-xs font-semibold underline px-2 py-1 min-h-[32px]"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* View 1: Upload & Scan Form (when no report loaded) */}
        {!report && (
          <div className="space-y-8 max-w-4xl mx-auto">
            {/* Hero Header */}
            <div className="text-center space-y-3">
              <div className="inline-flex items-center gap-1.5 rounded-full border border-[#ded9cc] bg-[#f7f5ef] px-3.5 py-1 text-xs font-mono uppercase tracking-wider text-[#181816]">
                <Sparkles className="h-3.5 w-3.5 text-[#8c6218]" />
                Enhancv-Inspired ATS Resume Checker
              </div>
              <h1 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-normal text-[#181816] tracking-tight">
                Check Your Resume for ATS Mistakes
              </h1>
              <p className="text-sm sm:text-base text-[#5c5953] max-w-2xl mx-auto leading-relaxed">
                Upload your resume in PDF or DOCX format. Get an instant, 5-pillar compatibility audit that checks
                multi-column layout traps, weak passive verbs, missing metrics, and section structure — completely
                free, no job description required.
              </p>
            </div>

            {/* Upload Mode Selector */}
            <div className="flex justify-center">
              <div className="inline-flex rounded border border-[#ded9cc] bg-[#f7f5ef] p-1 text-xs">
                <button
                  type="button"
                  onClick={() => setUploadMode("file")}
                  className={`rounded px-4 py-1.5 font-medium transition-colors min-h-[36px] flex items-center gap-1.5 ${
                    uploadMode === "file"
                      ? "bg-[#181816] text-[#fcfbf7] shadow-xs"
                      : "text-[#5c5953] hover:text-[#181816]"
                  }`}
                >
                  <Upload className="h-3.5 w-3.5" />
                  Upload PDF / DOCX
                </button>
                <button
                  type="button"
                  onClick={() => setUploadMode("text")}
                  className={`rounded px-4 py-1.5 font-medium transition-colors min-h-[36px] flex items-center gap-1.5 ${
                    uploadMode === "text"
                      ? "bg-[#181816] text-[#fcfbf7] shadow-xs"
                      : "text-[#5c5953] hover:text-[#181816]"
                  }`}
                >
                  <FileText className="h-3.5 w-3.5" />
                  Paste Plain Text
                </button>
              </div>
            </div>

            {/* Upload Area */}
            <div className="rounded-xl border border-[#ded9cc] bg-[#ffffff] p-6 sm:p-10 shadow-editorial space-y-6">
              {uploadMode === "file" ? (
                <div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx,.txt"
                    onChange={handleFileSelect}
                    className="hidden"
                    id="ats-resume-upload-input"
                  />

                  {!resumeFile ? (
                    <div
                      onDragOver={(e) => {
                        e.preventDefault();
                        setIsDragging(true);
                      }}
                      onDragLeave={() => setIsDragging(false)}
                      onDrop={handleFileDrop}
                      onClick={() => fileInputRef.current?.click()}
                      className={`cursor-pointer rounded-lg border-2 border-dashed p-8 sm:p-14 text-center transition-all ${
                        isDragging
                          ? "border-[#181816] bg-[#f7f5ef] scale-[0.99]"
                          : "border-[#ded9cc] bg-[#fcfbf7] hover:border-[#181816] hover:bg-[#f7f5ef]/50"
                      }`}
                    >
                      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#f7f5ef] border border-[#ded9cc] mb-4 text-[#181816]">
                        <Upload className="h-6 w-6" />
                      </div>
                      <h3 className="font-serif text-lg font-normal text-[#181816]">
                        Drag and drop your resume here
                      </h3>
                      <p className="mt-1.5 text-xs text-[#5c5953]">
                        Supports PDF, DOCX, or plain TXT up to 10MB
                      </p>
                      <div className="mt-5">
                        <span className="inline-flex items-center gap-1.5 rounded bg-[#181816] px-4 py-2 text-xs font-medium text-[#fcfbf7] hover:bg-[#2b2926] shadow-xs">
                          Browse Files
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-lg border border-[#cde4d3] bg-[#f0f7f2] p-5">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 items-center justify-center rounded bg-[#ffffff] border border-[#cde4d3] text-[#1f6339]">
                            <FileCheck className="h-5 w-5" />
                          </div>
                          <div>
                            <h4 className="text-sm font-semibold text-[#181816] truncate max-w-sm">
                              {resumeFile.name}
                            </h4>
                            <div className="flex items-center gap-2 mt-0.5 text-[11px] text-[#5c5953] font-mono">
                              <span>{formatFileSize(resumeFile.size)}</span>
                              <span>•</span>
                              <span className="uppercase">{resumeFile.name.split(".").pop()}</span>
                              <span>•</span>
                              <span className="text-[#1f6339] font-medium flex items-center gap-1">
                                <CheckCircle2 className="h-3 w-3" /> Ready for ATS Audit
                              </span>
                            </div>
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={() => {
                            setResumeFile(null);
                            if (fileInputRef.current) fileInputRef.current.value = "";
                          }}
                          className="rounded border border-[#ded9cc] bg-[#ffffff] px-3 py-1.5 text-xs font-medium text-[#5c5953] hover:text-[#942e23] hover:border-[#f7d0ca] transition-colors min-h-[36px]"
                        >
                          Change File
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  <label htmlFor="pasted-resume-text" className="block text-xs font-medium text-[#181816]">
                    Paste Resume Content
                  </label>
                  <textarea
                    id="pasted-resume-text"
                    rows={12}
                    value={pastedText}
                    onChange={(e) => setPastedText(e.target.value)}
                    placeholder="Paste the full text of your resume here, including Contact Info, Summary, Experience, Skills, and Education..."
                    className="w-full rounded border border-[#ded9cc] bg-[#fcfbf7] p-4 text-xs font-mono leading-relaxed text-[#181816] focus:border-[#181816] focus:outline-hidden focus:ring-1 focus:ring-[#181816]"
                  />
                </div>
              )}

              {/* Progress Indicator when scanning */}
              {isScanning && (
                <div className="rounded-lg border border-[#e6e2d8] bg-[#f7f5ef] p-6 space-y-4 animate-in fade-in">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs uppercase tracking-wider text-[#5c5953] flex items-center gap-2">
                      <RefreshCw className="h-3.5 w-3.5 animate-spin text-[#181816]" />
                      Auditing Resume Compatibility
                    </span>
                    <span className="font-mono text-xs font-semibold text-[#181816]">
                      Step {scanStepIndex + 1} of {scanSteps.length}
                    </span>
                  </div>

                  <div className="h-1.5 w-full bg-[#ded9cc] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#181816] transition-all duration-500 rounded-full"
                      style={{ width: `${((scanStepIndex + 1) / scanSteps.length) * 100}%` }}
                    />
                  </div>

                  <p className="text-xs text-[#181816] font-medium">
                    {scanSteps[scanStepIndex]}
                  </p>
                </div>
              )}

              {/* Action Button */}
              <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-[#edeae1]">
                <div className="flex items-center gap-2 text-xs text-[#5c5953]">
                  <ShieldCheck className="h-4 w-4 text-[#1f6339]" />
                  <span>100% deterministic evaluation • Zero fabricated claims</span>
                </div>

                <button
                  type="button"
                  onClick={handleRunAudit}
                  disabled={isScanning || (uploadMode === "file" && !resumeFile) || (uploadMode === "text" && !pastedText.trim())}
                  className={`w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded bg-[#181816] px-6 py-3 text-sm font-medium text-[#fcfbf7] hover:bg-[#2b2926] transition-all shadow-editorial min-h-[44px] ${
                    isScanning || (uploadMode === "file" && !resumeFile) || (uploadMode === "text" && !pastedText.trim())
                      ? "opacity-50 cursor-not-allowed"
                      : ""
                  }`}
                >
                  <Sparkles className="h-4 w-4" />
                  <span>{isScanning ? "Analyzing Resume..." : "Check My Resume Mistakes"}</span>
                  <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Feature Highlights Grid */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3 pt-4">
              <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 shadow-editorial space-y-2">
                <span className="text-[11px] font-mono uppercase tracking-wider text-[#5c5953]">Pillar 1 & 2</span>
                <h4 className="font-serif text-base font-normal text-[#181816]">Layout & Structure</h4>
                <p className="text-xs text-[#5c5953] leading-relaxed">
                  Detects multi-column traps, floating text boxes, and table layouts that cause ATS engines to parse text out of order.
                </p>
              </div>

              <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 shadow-editorial space-y-2">
                <span className="text-[11px] font-mono uppercase tracking-wider text-[#5c5953]">Pillar 3</span>
                <h4 className="font-serif text-base font-normal text-[#181816]">Active Verbs & Metrics</h4>
                <p className="text-xs text-[#5c5953] leading-relaxed">
                  Identifies passive phrasing (*"responsible for"*) and calculates your Google X-Y-Z formula measurable outcomes ratio.
                </p>
              </div>

              <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 shadow-editorial space-y-2">
                <span className="text-[11px] font-mono uppercase tracking-wider text-[#5c5953]">Pillar 4 & 5</span>
                <h4 className="font-serif text-base font-normal text-[#181816]">Contact & Evidence</h4>
                <p className="text-xs text-[#5c5953] leading-relaxed">
                  Validates email formatting, LinkedIn profiles, and verifies that skills are backed by genuine work history evidence.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* View 2: Complete ATS Compatibility & Mistakes Dashboard (when report loaded) */}
        {report && (
          <div className="space-y-6">
            {/* Top Results Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#e6e2d8] pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="rounded bg-[#f0f7f2] px-2 py-0.5 text-[10px] font-mono font-semibold text-[#1f6339] border border-[#cde4d3]">
                    AUDIT COMPLETED
                  </span>
                  <h1 className="font-serif text-2xl font-normal text-[#181816]">
                    ATS Resume Compatibility Report
                  </h1>
                </div>
                <p className="text-xs text-[#5c5953] mt-1">
                  General ATS Quality Audit • Analyzed on {new Date(report.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2 sm:gap-3">
                <button
                  type="button"
                  onClick={handleReset}
                  className="inline-flex items-center gap-1.5 rounded border border-[#ded9cc] bg-[#f7f5ef] px-3.5 py-2 text-xs font-medium text-[#181816] hover:bg-[#eae6dd] transition-colors min-h-[40px]"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  Check Another Resume
                </button>

                {currentAnalysisId && (
                  <Link
                    href={`/analysis/${currentAnalysisId}?tab=rewrite`}
                    className="inline-flex items-center gap-1.5 rounded bg-[#181816] px-4 py-2 text-xs font-medium text-[#fcfbf7] hover:bg-[#2b2926] transition-colors shadow-sm min-h-[40px]"
                  >
                    <Sparkles className="h-3.5 w-3.5 text-[#e6e2d8]" />
                    Fix in AI Optimizer
                    <ArrowRight className="h-3 w-3" />
                  </Link>
                )}
              </div>
            </div>

            {/* Embed the Enhancv-Style ATS Compatibility Dashboard */}
            <AtsTab
              report={report}
              onNavigateTab={(tab) => {
                if (currentAnalysisId) {
                  router.push(`/analysis/${currentAnalysisId}?tab=${tab}`);
                }
              }}
            />
          </div>
        )}
      </div>
    </main>
  );
}

export default function AtsCheckerPage() {
  return (
    <ProtectedRoute>
      <AtsCheckerContent />
    </ProtectedRoute>
  );
}
