"use client";

import { useQuery } from "@tanstack/react-query";

import { StatusIndicator } from "@/components/status-indicator";
import { fetchHealth } from "@/lib/api";

export function HealthStatus() {
  const health = useQuery({
    queryKey: ["foundation-health"],
    queryFn: fetchHealth,
    refetchInterval: 10_000,
  });

  if (health.isPending) {
    return <p role="status">Checking backend dependencies...</p>;
  }

  if (health.isError) {
    return (
      <p className="border border-red-300 bg-red-50 p-4 text-red-800" role="alert">
        Backend is unreachable. Start the backend service and retry.
      </p>
    );
  }

  const result = health.data;
  return (
    <section aria-labelledby="connectivity-heading" className="space-y-4">
      <div>
        <p className="text-sm uppercase tracking-[0.18em] text-neutral-500">Foundation status</p>
        <h2 className="text-2xl font-semibold" id="connectivity-heading">
          Frontend <span aria-hidden="true">-&gt;</span> Backend <span aria-hidden="true">-&gt;</span> Services
        </h2>
      </div>
      <p className={result.status === "ok" ? "text-emerald-700" : "text-red-700"} role="status">
        {result.status === "ok" ? "All foundation services are connected." : "One or more services are unavailable."}
      </p>
      <ul className="border-y border-neutral-200">
        <StatusIndicator label="FastAPI backend" status={result.status === "ok" ? "ok" : "error"} />
        <StatusIndicator label="PostgreSQL + pgvector" status={result.database} />
        <StatusIndicator label="Redis" status={result.redis} />
      </ul>
      {result.details && (
        <details className="text-sm text-red-800">
          <summary>Connection details</summary>
          <pre className="mt-2 overflow-auto whitespace-pre-wrap">{JSON.stringify(result.details, null, 2)}</pre>
        </details>
      )}
    </section>
  );
}