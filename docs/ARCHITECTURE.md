# XAI-ResOpt Architecture

## Product Boundary

XAI-ResOpt accepts a PDF/DOCX resume, pasted/uploaded/URL job description, and optional GitHub, portfolio, certification, or public-profile evidence. It produces ATS analysis, skill and evidence analysis, a deterministic explainable baseline score, grounded rewrites, validation results, a bounded re-evaluation loop, human approval, a final ATS-safe resume, and an explainable before/after report with history.

## Logical Pipeline

```text
Resume/JD/GitHub/Portfolio
  -> Intake Agent
  -> Deterministic + structured AI Parsing
  -> Resume Knowledge / Evidence Store
  -> Requirement-aware Agentic RAG
  -> Hybrid lexical + semantic retrieval and reranking
  -> ATS Agent + Skill Agent + Evidence Agent
  -> Explainability Layer
  -> Deterministic Baseline Score
  -> Optimizer Agent
  -> Critic Agent
  -> Fact-Check Agent
  -> PASS/FAIL
  -> ATS Re-Evaluator
  -> bounded controlled optimization loop
  -> Human Approval
  -> Final Resume + Explainable Report
```

## Runtime Components

- **Frontend:** Next.js, React, TypeScript, Tailwind CSS, accessible component system, typed API client, React Query or equivalent server-state layer.
- **Backend:** Python/FastAPI/Pydantic with modules for API, agents, RAG, parsing, scoring, evaluation, evidence, rewriting, integrations, models, services, and core concerns.
- **Workflow:** an explicit LangGraph-like state machine with shared structured state, deterministic transitions, bounded retries, resumable background jobs, and agent-level events.
- **Persistence:** PostgreSQL with pgvector. Redis handles cache, job status, rate limiting, and appropriate transient state. File storage is behind a local/object-storage abstraction.
- **Provider boundary:** an LLM provider interface supporting OpenAI, Anthropic, Gemini, and local/Ollama implementations through environment configuration.

## State and Ownership

The analysis state should carry input identifiers, normalized resume/JD structures, requirement records, retrieved evidence IDs and scores, agent outputs, deterministic score components, proposed changes, validation results, iteration number, and approval state. Persist durable facts and events; do not use client state as the source of truth for analysis results.

## Required Boundaries

Parsing first uses deterministic extraction where practical and structured AI only for ambiguity. Retrieval is requirement-aware. Agents consume and produce validated structured state. The scoring engine owns numeric calculations. The fact checker owns support validation. The re-evaluator compares persisted before/after values. The UI renders backend events and cannot invent agent activity.

## Operational Flow

Long-running parsing, embedding, retrieval, multi-agent analysis, optimization, and rendering run as background work. APIs expose queued/running/completed/failed/cancelled status. Every request and analysis carries correlation identifiers, and agent runs record duration, retries, retrieval counts, model calls, token usage when available, errors, and summaries.