"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  FileText,
  Cpu,
  Search,
  Check,
  Layers,
  BarChart3,
  Lock,
  Menu,
  X,
  Sparkles,
} from "lucide-react";

export default function LandingPage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Close drawer on Escape key and lock body scroll when open
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

  return (
    <div className="min-h-screen bg-[#fcfbf7] text-[#181816] selection:bg-[#eae6dd]">
      {/* Top Editorial Navigation */}
      <header className="sticky top-0 z-50 border-b border-[#e6e2d8] bg-[#fcfbf7]/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 sm:py-4">
          <div className="flex items-center gap-8">
            <Link href="/" className="flex items-center gap-2.5 focus-visible:ring-2 focus-visible:ring-[#181816] rounded">
              <span className="flex h-7 w-7 items-center justify-center rounded border border-[#181816] bg-[#181816] text-xs font-bold text-[#fcfbf7]">
                X
              </span>
              <span className="font-mono text-sm font-semibold tracking-wider uppercase text-[#181816]">
                XAI-ResOpt
              </span>
            </Link>
            <nav
              aria-label="Desktop primary navigation"
              className="hidden items-center gap-6 text-xs font-medium uppercase tracking-wider text-[#5c5953] md:flex"
            >
              <Link
                href="/ats-checker"
                className="text-[#181816] font-semibold flex items-center gap-1.5 py-1 px-2.5 rounded bg-[#f7f5ef] border border-[#ded9cc]"
              >
                <Sparkles className="h-3 w-3 text-[#8c6218]" />
                ATS Checker
              </Link>
              <a href="#philosophy" className="hover:text-[#181816] transition-colors py-2">Philosophy</a>
              <a href="#pipeline" className="hover:text-[#181816] transition-colors py-2">Architecture</a>
              <a href="#evidence" className="hover:text-[#181816] transition-colors py-2">Evidence Graph</a>
            </nav>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <Link
              href="/ats-checker"
              className="inline-flex items-center justify-center gap-1.5 rounded border border-[#ded9cc] bg-[#f7f5ef] px-3.5 py-2 text-xs font-medium text-[#181816] hover:bg-[#eae6dd] transition-colors min-h-[40px]"
            >
              <Sparkles className="h-3.5 w-3.5 text-[#8c6218]" />
              <span className="hidden sm:inline">ATS Checker</span>
            </Link>
            <Link
              href="/login"
              className="hidden sm:inline-flex items-center justify-center rounded border border-[#ded9cc] bg-[#f7f5ef] px-4 py-2 text-xs font-medium text-[#181816] hover:bg-[#eae6dd] transition-colors min-h-[40px]"
            >
              Sign In
            </Link>
            <Link
              href="/analysis/new"
              className="inline-flex items-center justify-center gap-1.5 rounded bg-[#181816] px-3.5 py-2 sm:px-4 sm:py-2 text-xs font-medium text-[#fcfbf7] hover:bg-[#2b2926] transition-colors min-h-[40px] shadow-sm"
            >
              <span>Job Match</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>

            {/* Mobile Drawer Trigger Button */}
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="inline-flex items-center justify-center rounded border border-[#ded9cc] bg-[#f7f5ef] p-2 text-[#181816] hover:bg-[#eae6dd] md:hidden min-h-[44px] min-w-[44px]"
              aria-label="Open navigation menu"
              aria-expanded={mobileMenuOpen}
              aria-controls="mobile-landing-drawer"
            >
              <Menu className="h-5 w-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Slide-Over Navigation Drawer */}
      {mobileMenuOpen && (
        <div
          id="mobile-landing-drawer"
          role="dialog"
          aria-modal="true"
          aria-label="Mobile Navigation"
          className="fixed inset-0 z-50 flex justify-end md:hidden"
        >
          {/* Backdrop overlay */}
          <div
            onClick={() => setMobileMenuOpen(false)}
            className="fixed inset-0 bg-[#181816]/40 backdrop-blur-xs transition-opacity"
            aria-hidden="true"
          />

          {/* Drawer container */}
          <div className="relative z-10 flex h-full w-4/5 max-w-xs flex-col border-l border-[#ded9cc] bg-[#ffffff] p-6 shadow-popup">
            <div className="flex items-center justify-between border-b border-[#edeae1] pb-4">
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded bg-[#181816] text-[11px] font-bold text-[#fcfbf7]">
                  X
                </span>
                <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[#181816]">
                  Navigation
                </span>
              </div>
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="flex items-center justify-center rounded p-2 text-[#5c5953] hover:bg-[#f7f5ef] hover:text-[#181816] min-h-[44px] min-w-[44px]"
                aria-label="Close menu"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <nav className="mt-6 flex flex-col space-y-3" aria-label="Mobile primary navigation">
              <Link
                href="/ats-checker"
                onClick={() => setMobileMenuOpen(false)}
                className="rounded px-3 py-2.5 text-sm font-semibold text-[#181816] bg-[#f7f5ef] min-h-[44px] flex items-center gap-2"
              >
                <Sparkles className="h-4 w-4 text-[#8c6218]" />
                ATS Resume Checker
              </Link>
              <a
                href="#philosophy"
                onClick={() => setMobileMenuOpen(false)}
                className="rounded px-3 py-2.5 text-sm font-medium text-[#181816] hover:bg-[#f7f5ef] transition-colors min-h-[44px] flex items-center"
              >
                Philosophy
              </a>
              <a
                href="#pipeline"
                onClick={() => setMobileMenuOpen(false)}
                className="rounded px-3 py-2.5 text-sm font-medium text-[#181816] hover:bg-[#f7f5ef] transition-colors min-h-[44px] flex items-center"
              >
                Architecture
              </a>
              <a
                href="#evidence"
                onClick={() => setMobileMenuOpen(false)}
                className="rounded px-3 py-2.5 text-sm font-medium text-[#181816] hover:bg-[#f7f5ef] transition-colors min-h-[44px] flex items-center"
              >
                Evidence Graph
              </a>
            </nav>

            <div className="mt-auto border-t border-[#edeae1] pt-6 space-y-3">
              <Link
                href="/login"
                onClick={() => setMobileMenuOpen(false)}
                className="flex w-full items-center justify-center rounded border border-[#ded9cc] bg-[#f7f5ef] px-4 py-3 text-sm font-medium text-[#181816] hover:bg-[#eae6dd] min-h-[44px]"
              >
                Sign In
              </Link>
              <Link
                href="/ats-checker"
                onClick={() => setMobileMenuOpen(false)}
                className="flex w-full items-center justify-center gap-2 rounded bg-[#181816] px-4 py-3 text-sm font-medium text-[#fcfbf7] hover:bg-[#2b2926] min-h-[44px]"
              >
                <Sparkles className="h-4 w-4" />
                ATS Resume Checker
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Hero Section */}
      <section className="mx-auto max-w-5xl px-4 pt-14 pb-12 text-center sm:px-6 md:pt-28 md:pb-24">
        <div className="inline-flex items-center gap-2 rounded-full border border-[#ded9cc] bg-[#f7f5ef] px-3.5 py-1 text-xs font-medium text-[#5c5953] mb-6 sm:mb-8">
          <span className="h-1.5 w-1.5 rounded-full bg-[#2e6b48]" />
          Explainable Agentic RAG Framework v1.0
        </div>

        <h1 className="font-serif text-3xl font-normal tracking-tight text-[#181816] sm:text-5xl md:text-7xl leading-[1.12] break-words">
          Evaluate. Explain.<br />
          Optimize. Verify.
        </h1>

        <p className="mx-auto mt-5 max-w-2xl text-base text-[#5c5953] sm:text-lg leading-relaxed px-2">
          The rigorous resume optimization framework engineered to eliminate AI hallucinations.
          Every metric and keyword is grounded in candidate evidence, scored deterministically,
          and validated against ATS parsers.
        </p>

        <div className="mt-8 sm:mt-10 flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 px-4">
          <Link
            href="/ats-checker"
            className="flex w-full sm:w-auto items-center justify-center gap-2 rounded bg-[#181816] px-6 py-3.5 text-sm font-medium text-[#fcfbf7] hover:bg-[#2b2926] transition-all shadow-editorial min-h-[44px]"
          >
            <Sparkles className="h-4 w-4 text-[#e6e2d8]" />
            Instant ATS Resume Checker
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/analysis/new"
            className="flex w-full sm:w-auto items-center justify-center rounded border border-[#ded9cc] bg-[#f7f5ef] px-6 py-3.5 text-sm font-medium text-[#181816] hover:bg-[#eae6dd] transition-colors min-h-[44px]"
          >
            Job Match Analysis
          </Link>
          <Link
            href="/dashboard"
            className="flex w-full sm:w-auto items-center justify-center rounded border border-[#ded9cc] bg-[#f7f5ef] px-6 py-3.5 text-sm font-medium text-[#181816] hover:bg-[#eae6dd] transition-colors min-h-[44px]"
          >
            Open Dashboard
          </Link>
        </div>

        {/* Hero Proof Callout */}
        <div className="mt-12 sm:mt-16 rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 text-left shadow-editorial">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#edeae1] pb-4">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold uppercase tracking-wider text-[#5c5953]">
                Factual Integrity Invariant
              </span>
            </div>
            <span className="rounded bg-[#f0f7f2] px-2.5 py-0.5 text-[11px] font-semibold text-[#1f6339] border border-[#cde4d3]">
              Zero Hallucination Guaranteed
            </span>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-3 text-xs leading-relaxed text-[#5c5953]">
            <div>
              <p className="font-semibold text-[#181816] mb-1">Never Invented</p>
              <p>Companies, job titles, dates of employment, degrees, unearned certifications, and fictitious metrics are strictly barred.</p>
            </div>
            <div>
              <p className="font-semibold text-[#181816] mb-1">Deterministic Scoring</p>
              <p>8-dimension ATS score formula (0-100) calculated by transparent algorithms rather than black-box LLM estimations.</p>
            </div>
            <div>
              <p className="font-semibold text-[#181816] mb-1">Traceability Map</p>
              <p>Every single bullet rewrite links directly to verifiable resume sections, GitHub repos, or portfolio projects.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Philosophy Section */}
      <section id="philosophy" className="border-t border-[#e6e2d8] bg-[#f7f5ef] py-14 sm:py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="max-w-2xl">
            <p className="font-mono text-xs font-bold uppercase tracking-widest text-[#5c5953]">Core Thesis</p>
            <h2 className="mt-2 font-serif text-2xl font-normal text-[#181816] sm:text-4xl">
              Why Generative AI Fails at ATS Optimization
            </h2>
            <p className="mt-3 text-xs sm:text-sm text-[#5c5953] leading-relaxed">
              Standard AI tools inject fabricated achievements, inflate metrics, and use multi-column templates that crash enterprise ATS parsers like Workday and Taleo. XAI-ResOpt takes the opposite approach.
            </p>
          </div>

          <div className="mt-10 sm:mt-12 grid grid-cols-1 gap-6 sm:gap-8 md:grid-cols-2">
            <div className="rounded border border-[#f7d0ca] bg-[#ffffff] p-6 sm:p-8 shadow-editorial">
              <div className="flex items-center gap-2 text-[#942e23] font-semibold text-sm mb-4">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#fdf2f0] text-xs">✕</span>
                Generic AI Resume Tools
              </div>
              <ul className="space-y-3 text-xs text-[#5c5953] leading-relaxed">
                <li className="flex items-start gap-2.5">
                  <span className="text-[#942e23] mt-0.5">•</span>
                  <span>Fabricates quantitative metrics (e.g. &quot;increased revenue by 45%&quot;) without verifying background evidence.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-[#942e23] mt-0.5">•</span>
                  <span>Generates complex multi-column, table-heavy PDF templates that scramble text inside ATS parsers.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-[#942e23] mt-0.5">•</span>
                  <span>Outputs arbitrary &quot;ATS Scores&quot; (e.g. 92/100) generated by random prompt hallucination.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <span className="text-[#942e23] mt-0.5">•</span>
                  <span>Cannot explain why a change was recommended or what source justified the rephrasing.</span>
                </li>
              </ul>
            </div>

            <div className="rounded border border-[#cde4d3] bg-[#ffffff] p-6 sm:p-8 shadow-editorial">
              <div className="flex items-center gap-2 text-[#1f6339] font-semibold text-sm mb-4">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#f0f7f2] text-xs">✓</span>
                XAI-ResOpt Framework
              </div>
              <ul className="space-y-3 text-xs text-[#5c5953] leading-relaxed">
                <li className="flex items-start gap-2.5">
                  <Check className="h-4 w-4 text-[#1f6339] shrink-0 mt-0.5" />
                  <span>Strict Fact-Checking Agent rejects any bullet rephrasing that introduces unverified facts.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <Check className="h-4 w-4 text-[#1f6339] shrink-0 mt-0.5" />
                  <span>Deterministic ATS single-column formatting validated across 5 structural invariants.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <Check className="h-4 w-4 text-[#1f6339] shrink-0 mt-0.5" />
                  <span>Mathematical formula combining keyword coverage, semantic similarity, and penalty deductions.</span>
                </li>
                <li className="flex items-start gap-2.5">
                  <Check className="h-4 w-4 text-[#1f6339] shrink-0 mt-0.5" />
                  <span>Full traceability: click any recommendation to inspect the original claim and source location.</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Multi-Agent Architecture Pipeline */}
      <section id="pipeline" className="border-t border-[#e6e2d8] py-14 sm:py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="text-center max-w-3xl mx-auto">
            <p className="font-mono text-xs font-bold uppercase tracking-widest text-[#5c5953]">Agent Orchestration</p>
            <h2 className="mt-2 font-serif text-2xl font-normal text-[#181816] sm:text-4xl">
              11 Specialized Agents in a Closed Loop
            </h2>
            <p className="mt-3 text-xs sm:text-sm text-[#5c5953] leading-relaxed">
              Resumes are not evaluated by a single unstructured prompt. Eleven distinct agents collaborate with shared state, deterministic scoring, and validation checkpoints.
            </p>
          </div>

          <div className="mt-10 sm:mt-14 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { title: "Intake & Parser", desc: "Extracts sections, claims, dates, and contact blocks into structured entities.", icon: FileText },
              { title: "JD Analyzer", desc: "Extracts mandatory and preferred skills, seniority indicators, and required tools.", icon: Search },
              { title: "Evidence Agent", desc: "Builds internal graph linking every assertion to verified resume and external sources.", icon: Layers },
              { title: "ATS Agent", desc: "Performs exact lexical and synonym matching, keyword distribution, and layout check.", icon: Cpu },
              { title: "Skill Agent", desc: "Maps semantic skill coverage, identifying true gaps versus transferable knowledge.", icon: CheckCircle2 },
              { title: "Scoring Engine", desc: "Applies deterministic 8-category mathematical formulation with point penalties.", icon: BarChart3 },
              { title: "Critic & Fact-Check", desc: "Dual validation agents that strictly reject unsupported or exaggerated claims.", icon: ShieldCheck },
              { title: "Human Review", desc: "Full user oversight: Accept, Reject, Edit manually, or Re-run optimization loop.", icon: Lock },
            ].map((agent, idx) => {
              const Icon = agent.icon;
              return (
                <div key={idx} className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 shadow-editorial">
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-mono text-xs text-[#5c5953]">0{idx + 1}</span>
                    <Icon className="h-4 w-4 text-[#181816]" />
                  </div>
                  <h3 className="font-medium text-sm text-[#181816]">{agent.title}</h3>
                  <p className="mt-2 text-xs text-[#5c5953] leading-relaxed">{agent.desc}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Evidence Graph Spotlight */}
      <section id="evidence" className="border-t border-[#e6e2d8] bg-[#f7f5ef] py-14 sm:py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="grid grid-cols-1 gap-8 lg:grid-cols-12 items-center">
            <div className="lg:col-span-5">
              <p className="font-mono text-xs font-bold uppercase tracking-widest text-[#5c5953]">Traceability</p>
              <h2 className="mt-2 font-serif text-2xl font-normal text-[#181816] sm:text-4xl">
                Every Recommendation Has an Audit Trail
              </h2>
              <p className="mt-3 text-xs sm:text-sm text-[#5c5953] leading-relaxed">
                When XAI-ResOpt proposes rephrasing a bullet point to improve keyword alignment, it cites the exact claim in your original resume or GitHub repository that makes the statement truthful.
              </p>
              <div className="mt-6 space-y-3">
                <div className="flex items-center gap-2.5 text-xs text-[#181816]">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#1f6339]" />
                  <span className="font-medium">Recommendation → Claim → Evidence Item → Location</span>
                </div>
                <div className="flex items-center gap-2.5 text-xs text-[#181816]">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#8c6218]" />
                  <span className="font-medium">Confidence scores from 0.00 to 1.00</span>
                </div>
                <div className="flex items-center gap-2.5 text-xs text-[#181816]">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#942e23]" />
                  <span className="font-medium">Immediate rejection of unsupported claims</span>
                </div>
              </div>
            </div>

            <div className="lg:col-span-7">
              <div className="rounded border border-[#ded9cc] bg-[#ffffff] p-4 sm:p-6 shadow-editorial font-mono text-xs overflow-x-auto">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#edeae1] pb-3 text-[#5c5953]">
                  <span>TRACEABILITY NODE #TRC-084</span>
                  <span className="text-[#1f6339] font-bold">STATUS: SUPPORTED (0.97)</span>
                </div>

                <div className="mt-4 space-y-4">
                  <div className="rounded bg-[#fcfbf7] p-3.5 border border-[#edeae1]">
                    <span className="text-[#5c5953] block text-[10px] uppercase font-bold mb-1">Proposed Rewrite (After)</span>
                    <p className="text-[#181816] font-sans text-xs leading-relaxed">
                      &quot;Architected high-throughput REST APIs using Python and FastAPI, increasing transaction throughput by 40% with PostgreSQL connection pooling.&quot;
                    </p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[11px]">
                    <div className="p-3 border border-[#edeae1] rounded bg-[#ffffff]">
                      <span className="text-[#5c5953] block text-[10px] uppercase font-bold mb-1">Grounded Source</span>
                      <p className="text-[#181816]">Resume.pdf → Experience → TechCorp → Bullet 1</p>
                    </div>
                    <div className="p-3 border border-[#edeae1] rounded bg-[#ffffff]">
                      <span className="text-[#5c5953] block text-[10px] uppercase font-bold mb-1">Target Requirement</span>
                      <p className="text-[#181816]">Python / FastAPI Microservices (Mandatory)</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Call to Action */}
      <section className="border-t border-[#e6e2d8] py-14 sm:py-20 text-center">
        <div className="mx-auto max-w-4xl px-4 sm:px-6">
          <h2 className="font-serif text-2xl font-normal text-[#181816] sm:text-4xl">
            Experience Verifiable Resume Engineering
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-xs sm:text-sm text-[#5c5953] leading-relaxed">
            Begin with a single resume and job description. Inspect your explainable ATS score, review grounded bullet optimizations, and export certified single-column resumes.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 px-4">
            <Link
              href="/analysis/new"
              className="flex w-full sm:w-auto items-center justify-center gap-2 rounded bg-[#181816] px-6 py-3.5 text-sm font-medium text-[#fcfbf7] hover:bg-[#2b2926] transition-all min-h-[44px]"
            >
              Start New Analysis
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/login"
              className="flex w-full sm:w-auto items-center justify-center rounded border border-[#ded9cc] bg-[#f7f5ef] px-6 py-3.5 text-sm font-medium text-[#181816] hover:bg-[#eae6dd] transition-colors min-h-[44px]"
            >
              Sign In to Account
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#e6e2d8] bg-[#f7f5ef] py-10 text-xs text-[#5c5953]">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 sm:px-6 md:flex-row">
          <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3 text-center">
            <span className="font-semibold text-[#181816]">XAI-ResOpt</span>
            <span>—</span>
            <span>Explainable Agentic RAG Resume Optimization</span>
          </div>
          <nav aria-label="Footer navigation" className="flex flex-wrap items-center justify-center gap-4 sm:gap-6">
            <Link href="/dashboard" className="hover:text-[#181816] py-1 min-h-[44px] flex items-center">Dashboard</Link>
            <Link href="/analysis/new" className="hover:text-[#181816] py-1 min-h-[44px] flex items-center">New Analysis</Link>
            <Link href="/evidence" className="hover:text-[#181816] py-1 min-h-[44px] flex items-center">Evidence Explorer</Link>
            <Link href="/settings" className="hover:text-[#181816] py-1 min-h-[44px] flex items-center">Settings</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}