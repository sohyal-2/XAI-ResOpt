# XAI-ResOpt Development Instructions

## Source of Truth

The authoritative product requirements are in [docs/XAI-RESOPT-MASTER-SPEC.md](../docs/XAI-RESOPT-MASTER-SPEC.md). Preserve its evidence-first, explainable, fact-grounded behavior. Do not invent requirements, fabricate evidence, hard-code scores, or silently modify user facts.

## Architecture Invariants

Preserve this logical flow:

`Resume/JD/GitHub/Portfolio -> Intake -> Parsing -> Evidence Knowledge Model -> Agentic RAG -> Hybrid Retrieval -> ATS Agent -> Skill Agent -> Evidence Agent -> Explainability -> Baseline Score -> Optimizer -> Critic -> Fact Checker -> ATS Re-Evaluator -> Controlled Optimization Loop -> Human Approval -> Final Resume + Explainable Report`

Use Next.js, React, TypeScript, Tailwind CSS, accessible components, typed API contracts, Python, FastAPI, Pydantic, PostgreSQL, pgvector, Redis, and a modular file-storage abstraction. Use explicit state-machine orchestration such as LangGraph or an equivalent, with structured shared state, bounded retries, and observability.

## Evidence and AI Rules

- Every meaningful claim must have provenance, confidence, and support status.
- Unsupported claims must be marked unsupported and rejected; never fabricate facts, metrics, employers, titles, skills, technologies, education, certifications, projects, or responsibilities.
- Retrieval must combine TF-IDF/BM25-style lexical signals with pgvector semantic similarity and evidence strength; weights must be configurable.
- Scoring must be deterministic and explainable. Call it the XAI-ResOpt ATS Compatibility Score, not an industry-standard formula.
- Agent outputs must be structured and validated. Agents share state and are not disconnected prompts.
- Optimization is bounded to 2–3 cycles or another explicit maximum; record scores, changes, rejected changes, validation issues, and evidence used.
- The user must inspect and accept, reject, or edit changes before finalization.

## Engineering Standards

Keep domain logic separate from presentation, use typed request/response schemas, relational foreign keys and indexes, background processing for long operations, loading/empty/success/failure/retry states, request and analysis IDs, structured logs, and tenant/user isolation. Never expose provider keys to the browser. Add unit, integration, end-to-end, and responsive-flow tests before declaring a phase complete.

Implement according to [docs/IMPLEMENTATION-PLAN.md](../docs/IMPLEMENTATION-PLAN.md), verifying tests and blocking errors after every phase. Do not start application implementation until the documentation and architecture decisions are reviewed.