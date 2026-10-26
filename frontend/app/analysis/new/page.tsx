"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ProtectedRoute } from "@/features/auth/protected-route";
import {
  ingestResume,
  ingestJobDescription,
  ingestExternalSource,
  triggerBaselineAnalysis,
} from "@/lib/api";
import {
  ArrowLeft,
  ArrowRight,
  Upload,
  FileText,
  Briefcase,
  GitBranch,
  Globe,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Cpu,
  Layers,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function NewAnalysisContent() {
  const router = useRouter();
  const fileInputRef = React.useRef<HTMLInputElement | null>(null);
  const jdFileInputRef = React.useRef<HTMLInputElement | null>(null);

  // Step tracking: 1: Resume, 2: Job Description, 3: External Sources (Optional), 4: Launching / Processing
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [isDragging, setIsDragging] = useState(false);

  // Resume state
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [resumePastedText, setResumePastedText] = useState("");
  const [resumeIngestedId, setResumeIngestedId] = useState<string | null>(null);

  // Job Description state
  const [jobTitle, setJobTitle] = useState("");
  const [jdMode, setJdMode] = useState<"text" | "url" | "file">("text");
  const [jdText, setJdText] = useState("");
  const [jdUrl, setJdUrl] = useState("");
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [jdIngestedId, setJdIngestedId] = useState<string | null>(null);

  // Optional external sources
  const [githubUrl, setGithubUrl] = useState("");
  const [portfolioUrl, setPortfolioUrl] = useState("");

  // Pipeline Execution state
  const [isProcessing, setIsProcessing] = useState(false);
  const [pipelineStep, setPipelineStep] = useState("");
  const [pipelineProgress, setPipelineProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Standalone Instant ATS Resume Check (Enhancv-style without requiring JD)
  const handleRunInstantAtsCheck = async () => {
    setError(null);
    if (!resumeFile && !resumePastedText.trim()) {
      setError("Please upload a resume file (PDF or DOCX) or paste resume text.");
      return;
    }

    try {
      setIsProcessing(true);
      setCurrentStep(4);
      setPipelineStep("Validating document format and extracting digital text layer...");
      setPipelineProgress(20);

      let fileToUpload = resumeFile;
      if (!fileToUpload && resumePastedText.trim()) {
        const blob = new Blob([resumePastedText], { type: "text/plain" });
        fileToUpload = new File([blob], "resume.txt", { type: "text/plain" });
      }

      let resId = resumeIngestedId;
      if (!resId && fileToUpload) {
        const res = await ingestResume(fileToUpload);
        resId = res.id;
        setResumeIngestedId(res.id);
      }

      setPipelineStep("Auditing ATS readability, section structure, action verbs, and metrics...");
      setPipelineProgress(55);

      const baselineReport = await triggerBaselineAnalysis({
        resume_id: resId!,
      });

      setPipelineStep("Deterministic ATS score synthesized. Opening Analysis Dashboard...");
      setPipelineProgress(100);

      setTimeout(() => {
        router.push(`/analysis/${baselineReport.analysis_id}`);
      }, 600);
    } catch (err: any) {
      setError(err.message || "Failed to execute ATS Resume Check.");
      setIsProcessing(false);
      setCurrentStep(1);
    }
  };

  // Handle Resume Submission to proceed to optional JD step
  const handleResumeNext = async () => {
    setError(null);
    if (!resumeFile && !resumePastedText.trim()) {
      setError("Please upload a resume file (PDF, DOCX, TXT) or paste plain text.");
      return;
    }

    try {
      setIsProcessing(true);
      let fileToUpload = resumeFile;
      if (!fileToUpload && resumePastedText.trim()) {
        const blob = new Blob([resumePastedText], { type: "text/plain" });
        fileToUpload = new File([blob], "resume.txt", { type: "text/plain" });
      }

      if (fileToUpload && !resumeIngestedId) {
        const res = await ingestResume(fileToUpload);
        setResumeIngestedId(res.id);
      }
      setCurrentStep(2);
    } catch (err: any) {
      setError(err.message || "Failed to parse resume document.");
    } finally {
      setIsProcessing(false);
    }
  };

  // Handle Job Description Submission
  const handleJdNext = async () => {
    setError(null);
    if (jdMode === "text" && !jdText.trim()) {
      setError("Please paste the job description text.");
      return;
    }
    if (jdMode === "url" && !jdUrl.trim()) {
      setError("Please provide a valid job posting URL.");
      return;
    }
    if (jdMode === "file" && !jdFile) {
      setError("Please select a job description file.");
      return;
    }

    try {
      setIsProcessing(true);
      const res = await ingestJobDescription({
        title: jobTitle || undefined,
        text: jdMode === "text" ? jdText : undefined,
        url: jdMode === "url" ? jdUrl : undefined,
        file: jdMode === "file" ? jdFile || undefined : undefined,
      });
      setJdIngestedId(res.id);
      setCurrentStep(3);
    } catch (err: any) {
      setError(err.message || "Failed to analyze job description.");
    } finally {
      setIsProcessing(false);
    }
  };

  // Launch Full Multi-Agent Pipeline with Job Description
  const handleLaunchPipeline = async () => {
    setError(null);
    if (!resumeIngestedId) {
      setError("Resume identifier missing. Please re-verify previous steps.");
      return;
    }

    try {
      setIsProcessing(true);
      setCurrentStep(4);

      if (githubUrl.trim()) {
        setPipelineStep("Ingesting external GitHub evidence...");
        setPipelineProgress(15);
        await ingestExternalSource(githubUrl.trim(), "github").catch(() => null);
      }
      if (portfolioUrl.trim()) {
        setPipelineStep("Ingesting portfolio evidence...");
        setPipelineProgress(30);
        await ingestExternalSource(portfolioUrl.trim(), "portfolio").catch(() => null);
      }

      setPipelineStep("Orchestrating multi-agent RAG workflow (Parser, ATS, Skill, Evidence, Scoring)...");
      setPipelineProgress(55);

      const baselineReport = await triggerBaselineAnalysis({
        resume_id: resumeIngestedId,
        job_description_id: jdIngestedId || undefined,
      });

      setPipelineStep("Deterministic scoring complete. Opening Analysis Workspace...");
      setPipelineProgress(100);

      setTimeout(() => {
        router.push(`/analysis/${baselineReport.analysis_id}`);
      }, 700);
    } catch (err: any) {
      setError(err.message || "Analysis pipeline execution encountered an issue.");
      setIsProcessing(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#fcfbf7] text-[#181816]">
      {/* Top Header */}
      <header className="border-b border-[#e6e2d8] bg-[#fcfbf7]">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 sm:px-6 py-4">
          <div className="flex items-center gap-4">
            <Link href="/dashboard" className="flex items-center gap-2 text-xs font-medium text-[#5c5953] hover:text-[#181816] transition-colors min-h-[44px] sm:min-h-0">
              <ArrowLeft className="h-3.5 w-3.5" />
              Dashboard
            </Link>
            <span className="text-[#ded9cc]">•</span>
            <Link href="/ats-checker" className="text-xs font-medium text-[#181816] hover:underline flex items-center gap-1">
              <Sparkles className="h-3 w-3 text-[#8c6218]" />
              ATS Checker
            </Link>
          </div>
          <span className="font-mono text-xs text-[#5c5953] uppercase tracking-wider">
            Job Match Workflow (Step {currentStep} of 4)
          </span>
        </div>
      </header>

      <div className="mx-auto max-w-3xl px-4 sm:px-6 py-8 sm:py-12">
        {/* Notice banner pointing to dedicated ATS Checker */}
        <div className="mb-6 rounded border border-[#ded9cc] bg-[#f7f5ef] p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-[#181816]">
            <Sparkles className="h-4 w-4 text-[#8c6218] shrink-0" />
            <span>Only looking to audit your resume for ATS mistakes without a job description?</span>
          </div>
          <Link
            href="/ats-checker"
            className="font-medium text-[#181816] hover:underline shrink-0 flex items-center gap-1 font-mono text-[11px]"
          >
            Open Standalone ATS Checker <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
        {/* Step Indicator */}
        <div className="mb-8 sm:mb-10 grid grid-cols-4 gap-1.5 sm:gap-2 text-center text-xs font-medium">
          {[
            { num: 1, label: "Resume" },
            { num: 2, label: "Job Desc" },
            { num: 3, label: "External" },
            { num: 4, label: "Execution" },
          ].map((s) => (
            <div
              key={s.num}
              className={`border-b-2 pb-2 transition-colors ${
                currentStep === s.num
                  ? "border-[#181816] text-[#181816] font-semibold"
                  : currentStep > s.num
                  ? "border-[#2e6b48] text-[#2e6b48]"
                  : "border-[#ded9cc] text-[#5c5953]"
              }`}
            >
              <span className="block font-mono text-[10px] sm:text-[11px] mb-0.5">0{s.num}</span>
              <span className="text-[10px] sm:text-xs leading-tight block truncate sm:overflow-visible">{s.label}</span>
            </div>
          ))}
        </div>

        {error && (
          <div className="mb-6 flex items-start gap-2 rounded border border-[#f7d0ca] bg-[#fdf2f0] p-4 text-xs text-[#942e23]" role="alert">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* STEP 1: Upload Resume */}
        {currentStep === 1 && (
          <section className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-8 shadow-editorial">
            <div className="flex items-center gap-2 text-xs font-mono text-[#5c5953] uppercase tracking-wider mb-2">
              <FileText className="h-4 w-4 text-[#181816]" />
              Step 01 — ATS Resume Checker
            </div>
            <h1 className="font-serif text-xl sm:text-2xl font-normal text-[#181816]">Upload Candidate Resume</h1>
            <p className="mt-1 text-xs text-[#5c5953]">
              Upload your resume in PDF or DOCX format. We will audit ATS readability, layout traps, section structure, action verbs, and quantifiable metrics.
            </p>

            <div className="mt-6 space-y-6">
              {/* File Dropzone */}
              <div
                tabIndex={0}
                role="button"
                aria-label="Upload resume file dropzone. Press Enter or Space to choose a file."
                onClick={() => fileInputRef.current?.click()}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    fileInputRef.current?.click();
                  }
                }}
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragging(true);
                }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragging(false);
                  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    setResumeFile(e.dataTransfer.files[0]);
                  }
                }}
                className={`flex flex-col items-center justify-center rounded border-2 border-dashed p-6 sm:p-8 text-center cursor-pointer transition-colors focus-visible:outline-2 focus-visible:outline-[#181816] ${
                  isDragging
                    ? "border-[#181816] bg-[#f2efe6]"
                    : "border-[#ded9cc] bg-[#fcfbf7] hover:border-[#181816]"
                }`}
              >
                <Upload className="h-8 w-8 text-[#5c5953] mb-2" />
                <span className="text-xs font-medium text-[#181816] break-all">
                  {resumeFile ? resumeFile.name : "Click or drag & drop your resume file here"}
                </span>
                <span className="mt-1 text-[11px] text-[#5c5953]">Supports PDF, DOCX, TXT (up to 10MB)</span>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.txt"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setResumeFile(e.target.files[0]);
                    }
                  }}
                />
              </div>

              {/* Selected File Preview Card */}
              {resumeFile && (
                <div className="flex items-center justify-between rounded border border-[#cde4d3] bg-[#f0f7f2] p-4 text-xs">
                  <div className="flex items-center gap-3">
                    <FileText className="h-5 w-5 text-[#1f6339] shrink-0" />
                    <div>
                      <p className="font-medium text-[#181816] break-all">{resumeFile.name}</p>
                      <div className="mt-0.5 flex items-center gap-2 text-[11px] text-[#5c5953]">
                        <span>{formatFileSize(resumeFile.size)}</span>
                        <span>•</span>
                        <span className="text-[#1f6339] font-medium flex items-center gap-1">
                          <CheckCircle2 className="h-3 w-3" /> Ready for ATS Analysis
                        </span>
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setResumeFile(null)}
                    className="text-xs text-[#5c5953] hover:text-[#942e23] transition-colors ml-2"
                  >
                    Change
                  </button>
                </div>
              )}

              <div className="relative flex items-center justify-center">
                <span className="bg-[#ffffff] px-3 font-mono text-[11px] text-[#5c5953] uppercase font-bold">Or Paste Plain Text</span>
              </div>

              <div>
                <label htmlFor="resume-plain-text" className="sr-only">Paste plain resume text</label>
                <textarea
                  id="resume-plain-text"
                  value={resumePastedText}
                  onChange={(e) => setResumePastedText(e.target.value)}
                  rows={5}
                  placeholder="Paste raw resume text here if preferred..."
                  className="w-full rounded border border-[#ded9cc] bg-[#fcfbf7] p-3 text-xs text-[#181816] focus:border-[#181816] focus:outline-none transition-colors font-mono leading-relaxed"
                />
              </div>

              {/* Dual Action Buttons (Instant ATS Check vs Target Job Matching) */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-4 border-t border-[#edeae1]">
                <button
                  type="button"
                  onClick={handleResumeNext}
                  disabled={isProcessing || (!resumeFile && !resumePastedText.trim())}
                  className="flex items-center justify-center gap-1.5 rounded border border-[#ded9cc] bg-[#f7f5ef] px-4 py-2.5 text-xs font-medium text-[#181816] hover:bg-[#eae6dd] disabled:opacity-50 transition-colors min-h-[44px]"
                >
                  <span>Match with Target Job (Optional)</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>

                <button
                  type="button"
                  onClick={handleRunInstantAtsCheck}
                  disabled={isProcessing || (!resumeFile && !resumePastedText.trim())}
                  className="flex items-center justify-center gap-2 rounded bg-[#181816] px-5 py-2.5 text-xs font-bold text-[#fcfbf7] hover:bg-[#2b2926] disabled:opacity-50 transition-colors shadow-sm min-h-[44px]"
                >
                  <ShieldCheck className="h-4 w-4 text-[#8cd69e]" />
                  <span>{isProcessing ? "Analyzing Resume..." : "Run Instant ATS Check"}</span>
                </button>
              </div>
            </div>
          </section>
        )}


        {/* STEP 2: Job Description */}
        {currentStep === 2 && (
          <section className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-8 shadow-editorial">
            <div className="flex items-center gap-2 text-xs font-mono text-[#5c5953] uppercase tracking-wider mb-2">
              <Briefcase className="h-4 w-4 text-[#181816]" />
              Step 02 — Target Requirement
            </div>
            <h1 className="font-serif text-xl sm:text-2xl font-normal text-[#181816]">Target Job Description</h1>
            <p className="mt-1 text-xs text-[#5c5953]">
              Provide the job posting. The JD Analyzer will categorize mandatory vs preferred skills, seniority expectations, and required tooling.
            </p>

            <div className="mt-6 space-y-5">
              <div>
                <label className="block text-xs font-medium text-[#181816]">
                  Job Title / Target Role (Optional)
                  <input
                    type="text"
                    value={jobTitle}
                    onChange={(e) => setJobTitle(e.target.value)}
                    placeholder="e.g. Senior Backend Engineer"
                    className="mt-1.5 w-full rounded border border-[#ded9cc] bg-[#fcfbf7] px-3 py-2.5 text-xs text-[#181816] focus:border-[#181816] focus:outline-none"
                  />
                </label>
              </div>

              {/* Mode Toggle */}
              <div className="flex items-center gap-2 border-b border-[#edeae1] pb-2 text-xs flex-wrap">
                {(["text", "url", "file"] as const).map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setJdMode(m)}
                    className={`rounded px-3.5 py-2 font-medium capitalize transition-colors min-h-[44px] sm:min-h-0 flex items-center justify-center ${
                      jdMode === m
                        ? "bg-[#181816] text-[#fcfbf7]"
                        : "bg-[#f7f5ef] text-[#5c5953] hover:bg-[#eae6dd]"
                    }`}
                  >
                    {m === "text" ? "Paste Text" : m === "url" ? "Public URL" : "Upload File"}
                  </button>
                ))}
              </div>

              {jdMode === "text" && (
                <div>
                  <label htmlFor="jd-text-area" className="sr-only">Paste full job description text</label>
                  <textarea
                    id="jd-text-area"
                    value={jdText}
                    onChange={(e) => setJdText(e.target.value)}
                    rows={8}
                    placeholder="Paste the full job posting, responsibilities, and qualifications..."
                    className="w-full rounded border border-[#ded9cc] bg-[#fcfbf7] p-3 text-xs text-[#181816] focus:border-[#181816] focus:outline-none font-mono leading-relaxed"
                  />
                </div>
              )}

              {jdMode === "url" && (
                <div>
                  <label className="block text-xs font-medium text-[#181816]">
                    Job Posting URL
                    <input
                      type="url"
                      value={jdUrl}
                      onChange={(e) => setJdUrl(e.target.value)}
                      placeholder="https://company.com/careers/role-123"
                      className="mt-1.5 w-full rounded border border-[#ded9cc] bg-[#fcfbf7] px-3 py-2.5 text-xs text-[#181816] focus:border-[#181816] focus:outline-none"
                    />
                  </label>
                  <span className="mt-1 block text-[11px] text-[#5c5953]">
                    System validates URL safety, timeouts, and respects SSRF security policies.
                  </span>
                </div>
              )}

              {jdMode === "file" && (
                <div
                  tabIndex={0}
                  role="button"
                  aria-label="Upload job description file dropzone. Press Enter or Space to choose a file."
                  onClick={() => jdFileInputRef.current?.click()}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      jdFileInputRef.current?.click();
                    }
                  }}
                  className="flex flex-col items-center justify-center rounded border-2 border-dashed border-[#ded9cc] bg-[#fcfbf7] p-6 text-center cursor-pointer hover:border-[#181816] focus-visible:outline-2 focus-visible:outline-[#181816] transition-colors"
                >
                  <Upload className="h-6 w-6 text-[#5c5953] mb-1" />
                  <span className="text-xs font-medium text-[#181816] break-all">
                    {jdFile ? jdFile.name : "Select Job Description file (PDF, DOCX, TXT)"}
                  </span>
                  <input
                    ref={jdFileInputRef}
                    type="file"
                    accept=".pdf,.docx,.txt"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setJdFile(e.target.files[0]);
                      }
                    }}
                  />
                </div>
              )}

              <div className="flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-4 border-t border-[#edeae1]">
                <button
                  type="button"
                  onClick={() => setCurrentStep(1)}
                  className="rounded border border-[#ded9cc] bg-[#f7f5ef] px-4 py-2.5 text-xs font-medium text-[#5c5953] hover:text-[#181816] min-h-[44px] flex items-center justify-center"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={handleJdNext}
                  disabled={isProcessing}
                  className="flex items-center justify-center gap-1.5 rounded bg-[#181816] px-5 py-2.5 text-xs font-medium text-[#fcfbf7] hover:bg-[#2b2926] disabled:opacity-50 shadow-sm min-h-[44px]"
                >
                  {isProcessing ? "Analyzing Job..." : "Continue to External Evidence"}
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </section>
        )}

        {/* STEP 3: Optional External Proof */}
        {currentStep === 3 && (
          <section className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-8 shadow-editorial">
            <div className="flex items-center gap-2 text-xs font-mono text-[#5c5953] uppercase tracking-wider mb-2">
              <ShieldCheck className="h-4 w-4 text-[#181816]" />
              Step 03 — External Evidence (Optional)
            </div>
            <h1 className="font-serif text-xl sm:text-2xl font-normal text-[#181816]">External Supporting Profiles</h1>
            <p className="mt-1 text-xs text-[#5c5953]">
              Link your public GitHub profile or portfolio. External projects and READMEs serve as supporting evidence for technical claims without inflating unverified skills.
            </p>

            <div className="mt-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#181816]">
                  <span className="flex items-center gap-1.5 mb-1">
                    <GitBranch className="h-3.5 w-3.5" />
                    GitHub Profile / Repository URL
                  </span>
                  <input
                    type="url"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                    placeholder="https://github.com/username"
                    className="w-full rounded border border-[#ded9cc] bg-[#fcfbf7] px-3 py-2.5 text-xs text-[#181816] focus:border-[#181816] focus:outline-none"
                  />
                </label>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#181816]">
                  <span className="flex items-center gap-1.5 mb-1">
                    <Globe className="h-3.5 w-3.5" />
                    Portfolio / Technical Blog URL
                  </span>
                  <input
                    type="url"
                    value={portfolioUrl}
                    onChange={(e) => setPortfolioUrl(e.target.value)}
                    placeholder="https://janedoe.dev"
                    className="w-full rounded border border-[#ded9cc] bg-[#fcfbf7] px-3 py-2.5 text-xs text-[#181816] focus:border-[#181816] focus:outline-none"
                  />
                </label>
              </div>

              <div className="rounded border border-[#edeae1] bg-[#fcfbf7] p-4 text-[11px] text-[#5c5953] leading-relaxed">
                <span className="font-semibold text-[#181816] block mb-1">Factual Grounding Rule</span>
                External profiles are used to substantiate claims in your resume. If a skill cannot be corroborated by evidence in either your resume or external profiles, the system flags it as an unsupported gap rather than inventing it.
              </div>

              <div className="flex flex-col-reverse sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-4 border-t border-[#edeae1]">
                <button
                  type="button"
                  onClick={() => setCurrentStep(2)}
                  className="rounded border border-[#ded9cc] bg-[#f7f5ef] px-4 py-2.5 text-xs font-medium text-[#5c5953] hover:text-[#181816] min-h-[44px] flex items-center justify-center"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={handleLaunchPipeline}
                  disabled={isProcessing}
                  className="flex items-center justify-center gap-2 rounded bg-[#181816] px-6 py-3 text-xs font-bold text-[#fcfbf7] hover:bg-[#2b2926] disabled:opacity-50 shadow-sm min-h-[44px]"
                >
                  Run 11-Agent Analysis Pipeline
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </section>
        )}

        {/* STEP 4: Live Processing Pipeline Visualizer */}
        {currentStep === 4 && (
          <section className="rounded border border-[#e6e2d8] bg-[#ffffff] p-6 sm:p-10 shadow-editorial text-center">
            <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-[#f7f5ef] border border-[#ded9cc] mb-4">
              <RefreshCw className="h-6 w-6 text-[#181816] animate-spin" />
            </div>

            <h2 className="font-serif text-xl sm:text-2xl font-normal text-[#181816]">
              Executing Multi-Agent Evaluation
            </h2>
            <p className="mt-2 text-xs text-[#5c5953] max-w-md mx-auto">
              {pipelineStep || "Initializing RAG retrieval and deterministic scoring engine..."}
            </p>

            {/* Progress Bar */}
            <div className="mt-6 mx-auto max-w-md bg-[#f7f5ef] rounded-full h-2 overflow-hidden border border-[#ded9cc]">
              <div
                className="bg-[#181816] h-full transition-all duration-500 rounded-full"
                style={{ width: `${pipelineProgress}%` }}
              />
            </div>

            {/* Active Agent Nodes */}
            <div className="mt-8 grid grid-cols-2 sm:grid-cols-3 gap-3 text-left max-w-lg mx-auto text-xs">
              {[
                { name: "Intake Agent", done: pipelineProgress >= 20 },
                { name: "JD Analyzer", done: pipelineProgress >= 35 },
                { name: "Evidence Store", done: pipelineProgress >= 50 },
                { name: "ATS Agent", done: pipelineProgress >= 70 },
                { name: "Skill Agent", done: pipelineProgress >= 85 },
                { name: "Scoring Engine", done: pipelineProgress >= 95 },
              ].map((agent, i) => (
                <div
                  key={i}
                  className={`flex items-center gap-2 rounded border p-2.5 ${
                    agent.done
                      ? "border-[#cde4d3] bg-[#f0f7f2] text-[#1f6339]"
                      : "border-[#ded9cc] bg-[#fcfbf7] text-[#5c5953]"
                  }`}
                >
                  <CheckCircle2 className={`h-3.5 w-3.5 ${agent.done ? "text-[#1f6339]" : "text-[#ded9cc]"}`} />
                  <span className="font-mono text-[11px]">{agent.name}</span>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}

export default function NewAnalysisPage() {
  return (
    <ProtectedRoute>
      <NewAnalysisContent />
    </ProtectedRoute>
  );
}
