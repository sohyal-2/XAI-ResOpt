"use client";

import React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ProtectedRoute } from "@/features/auth/protected-route";
import { RewriteTab } from "@/features/analysis/rewrite-tab";
import { ArrowLeft } from "lucide-react";

function ReviewPageContent() {
  const params = useParams();
  const router = useRouter();
  const analysisId = params?.id as string;

  return (
    <main className="min-h-screen bg-[#fcfbf7] text-[#181816]">
      <header className="border-b border-[#e6e2d8] bg-[#fcfbf7]/95 sticky top-0 z-40 backdrop-blur-sm">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link
            href={`/analysis/${analysisId}?tab=rewrite`}
            className="flex items-center gap-1.5 text-xs font-medium text-[#5c5953] hover:text-[#181816] transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Analysis Workspace
          </Link>
          <span className="font-mono text-xs text-[#8a867c] uppercase">
            Human-in-the-Loop Review
          </span>
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-6 py-10">
        <RewriteTab
          analysisId={analysisId}
          onNavigateTab={(tab) => router.push(`/analysis/${analysisId}?tab=${tab}`)}
        />
      </div>
    </main>
  );
}

export default function ReviewPage() {
  return (
    <ProtectedRoute>
      <ReviewPageContent />
    </ProtectedRoute>
  );
}
