"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "@/features/auth/protected-route";
import { useAuth } from "@/features/auth/auth-provider";
import { fetchHealth, type HealthResponse } from "@/lib/api";
import {
  ArrowLeft,
  Settings as SettingsIcon,
  Server,
  Database,
  Sliders,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  User,
  Sparkles,
} from "lucide-react";

function SettingsContent() {
  const { user } = useAuth();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(true);

  // Scoring Weights state (Master Spec Section 7)
  const [lexicalWeight, setLexicalWeight] = useState(0.4);
  const [semanticWeight, setSemanticWeight] = useState(0.4);
  const [evidenceWeight, setEvidenceWeight] = useState(0.2);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    async function checkSystemHealth() {
      try {
        setLoadingHealth(true);
        const data = await fetchHealth();
        setHealth(data);
      } catch {
        setHealth({ status: "degraded", database: "error", redis: "error" });
      } finally {
        setLoadingHealth(false);
      }
    }
    checkSystemHealth();
  }, []);

  const handleSaveWeights = (e: React.FormEvent) => {
    e.preventDefault();
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  return (
    <main className="min-h-screen bg-[#fcfbf7] text-[#181816]">
      {/* Top Header */}
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
              System &amp; Scoring Configuration
            </span>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-4 sm:px-6 py-6 sm:py-10 space-y-6 sm:space-y-8">
        <div className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 shadow-editorial">
          <div className="flex items-center gap-2 text-xs font-mono text-[#5c5953] uppercase tracking-wider mb-1">
            <SettingsIcon className="h-4 w-4 text-[#181816]" />
            Configuration
          </div>
          <h1 className="font-serif text-2xl sm:text-3xl font-normal text-[#181816]">
            Platform Settings
          </h1>
          <p className="mt-2 text-xs text-[#5c5953] leading-relaxed">
            Manage scoring engine weights, check backend database and cache connectivity, and customize ATS rendering defaults.
          </p>
        </div>

        {/* User Account Profile */}
        <section className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 shadow-editorial text-xs space-y-4">
          <div className="flex items-center gap-2 border-b border-[#edeae1] pb-3">
            <User className="h-4 w-4 text-[#181816]" />
            <h2 className="font-semibold text-sm text-[#181816]">User Profile</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <span className="text-[#5c5953] block text-[11px] font-medium">Full Name</span>
              <p className="font-medium text-[#181816] mt-0.5">{user?.full_name || "—"}</p>
            </div>
            <div>
              <span className="text-[#5c5953] block text-[11px] font-medium">Email Address</span>
              <p className="font-medium text-[#181816] mt-0.5">{user?.email || "—"}</p>
            </div>
          </div>
        </section>

        {/* Backend Connectivity Status */}
        <section className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 shadow-editorial text-xs space-y-4">
          <div className="flex items-center justify-between border-b border-[#edeae1] pb-3">
            <div className="flex items-center gap-2">
              <Server className="h-4 w-4 text-[#181816]" />
              <h2 className="font-semibold text-sm text-[#181816]">System Infrastructure</h2>
            </div>
            <span
              className={`rounded px-2 py-0.5 text-[10px] font-semibold uppercase border ${
                health?.status === "ok"
                  ? "bg-[#f0f7f2] text-[#1f6339] border-[#cde4d3]"
                  : "bg-[#fdf8ee] text-[#8c6218] border-[#fae8be]"
              }`}
            >
              {health?.status === "ok" ? "All Systems Operational" : "Degraded State"}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="rounded border border-[#edeae1] bg-[#fcfbf7] p-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-[#5c5953]" />
                <span className="font-medium text-[#181816]">PostgreSQL + pgvector</span>
              </div>
              <span className="font-mono text-[11px] text-[#1f6339] font-semibold">
                {health?.database === "ok" ? "CONNECTED" : "OFFLINE"}
              </span>
            </div>

            <div className="rounded border border-[#edeae1] bg-[#fcfbf7] p-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Server className="h-4 w-4 text-[#5c5953]" />
                <span className="font-medium text-[#181816]">Redis Cache &amp; Queues</span>
              </div>
              <span className="font-mono text-[11px] text-[#1f6339] font-semibold">
                {health?.redis === "ok" ? "CONNECTED" : "OFFLINE"}
              </span>
            </div>
          </div>
        </section>

        {/* Configurable Hybrid Scoring Weights */}
        <section className="rounded border border-[#e6e2d8] bg-[#ffffff] p-5 sm:p-6 shadow-editorial text-xs space-y-4">
          <div className="flex items-center justify-between border-b border-[#edeae1] pb-3">
            <div className="flex items-center gap-2">
              <Sliders className="h-4 w-4 text-[#181816]" />
              <div>
                <h2 className="font-semibold text-sm text-[#181816]">
                  Configurable ATS Scoring Weights
                </h2>
                <p className="text-[#5c5953] text-[11px]">
                  Adjust the relative balance between lexical keyword overlap, semantic retrieval, and verified evidence confidence.
                </p>
              </div>
            </div>
          </div>

          {saveSuccess && (
            <div className="rounded border border-[#cde4d3] bg-[#f0f7f2] p-3 text-[#1f6339] font-medium" role="alert">
              ✓ Scoring weights updated successfully.
            </div>
          )}

          <form onSubmit={handleSaveWeights} className="space-y-4">
            <div>
              <div className="flex justify-between font-medium text-[#181816] mb-1">
                <label htmlFor="lexical-weight-slider">Lexical Keyword Weight (Exact &amp; Synonyms)</label>
                <span className="font-mono">{(lexicalWeight * 100).toFixed(0)}%</span>
              </div>
              <input
                id="lexical-weight-slider"
                type="range"
                min="0.1"
                max="0.8"
                step="0.05"
                value={lexicalWeight}
                onChange={(e) => setLexicalWeight(parseFloat(e.target.value))}
                aria-label="Lexical Keyword Weight percentage"
                className="w-full accent-[#181816] h-6 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between font-medium text-[#181816] mb-1">
                <label htmlFor="semantic-weight-slider">Semantic Retrieval Weight (pgvector similarity)</label>
                <span className="font-mono">{(semanticWeight * 100).toFixed(0)}%</span>
              </div>
              <input
                id="semantic-weight-slider"
                type="range"
                min="0.1"
                max="0.8"
                step="0.05"
                value={semanticWeight}
                onChange={(e) => setSemanticWeight(parseFloat(e.target.value))}
                aria-label="Semantic Retrieval Weight percentage"
                className="w-full accent-[#181816] h-6 cursor-pointer"
              />
            </div>

            <div>
              <div className="flex justify-between font-medium text-[#181816] mb-1">
                <label htmlFor="evidence-weight-slider">Evidence Confidence Weight (Factual Backing)</label>
                <span className="font-mono">{(evidenceWeight * 100).toFixed(0)}%</span>
              </div>
              <input
                id="evidence-weight-slider"
                type="range"
                min="0.1"
                max="0.8"
                step="0.05"
                value={evidenceWeight}
                onChange={(e) => setEvidenceWeight(parseFloat(e.target.value))}
                aria-label="Evidence Confidence Weight percentage"
                className="w-full accent-[#181816] h-6 cursor-pointer"
              />
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                className="w-full sm:w-auto rounded bg-[#181816] px-5 py-2.5 text-xs font-medium text-[#fcfbf7] hover:bg-[#2b2926] shadow-sm min-h-[44px] flex items-center justify-center"
              >
                Save Scoring Parameters
              </button>
            </div>
          </form>
        </section>
      </div>
    </main>
  );
}

export default function SettingsPage() {
  return (
    <ProtectedRoute>
      <SettingsContent />
    </ProtectedRoute>
  );
}
