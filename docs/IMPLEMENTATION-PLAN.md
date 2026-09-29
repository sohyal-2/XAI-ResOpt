# XAI-ResOpt Implementation Plan

Build incrementally. After every phase, run tests, verify the application, fix errors, and do not continue while major blocking errors remain.

## Dependency Order

1. **Project foundation:** repository layout, frontend/backend shells, Docker development environment, environment example, baseline tooling.
2. **Database and authentication:** PostgreSQL/pgvector, Redis, migrations, seed plumbing, user/session/auth and authorization boundaries.
3. **Resume/JD ingestion:** upload and URL intake, validation, storage abstraction, deterministic PDF/DOCX/text parsing, JD parsing.
4. **Knowledge/evidence model:** normalized resume sections, requirements, claims, evidence, confidence, provenance, and external sources.
5. **Hybrid retrieval:** lexical TF-IDF/BM25 channel, embeddings/pgvector channel, configurable combination, reranking and persistence.
6. **Agentic RAG:** explicit state machine, requirement decomposition, retrieval cycles, grounded context, retries, status events.
7. **ATS/Skill/Evidence agents:** structured outputs and validation for coverage, skills, gaps, factual support, contradictions, and confidence.
8. **Explainable scoring:** deterministic dimensions, weights, penalties, reasons, supporting evidence, and versioned score output.
9. **Optimizer/Critic/Fact Checker:** evidence-grounded changes, quality/factual review, rejection behavior, and persisted iteration records.
10. **Re-evaluation loop:** bounded retries, before/after comparison, remaining gaps, new risks, and stop conditions.
11. **Human review UI:** change diff, evidence links, risks, accept/reject/edit, approval history.
12. **Resume rendering/export:** ATS-safe single-column output, PDF, and DOCX where practical.
13. **AI Copilot:** analysis-aware retrieval, evidence citations, known/inferred/unknown/unsupported distinctions.
14. **GitHub/Portfolio integrations:** modular tools, policy-aware fetching, supporting evidence only.
15. **Observability/security:** structured logs, correlation IDs, metrics, retries, rate limits, SSRF/file controls, secrets, isolation.
16. **Testing:** unit, integration, end-to-end, responsive critical flows, and acceptance-flow verification.
17. **Phase 17 - Responsive and UX refinement:** accessibility, mobile layouts, error/empty/loading states, typography, charts, and final polish.

## Cross-Phase Definition of Done

Typed contracts, persisted provenance, authorization, loading/error states, structured logs, tests for changed behavior, and reproducible local setup must accompany each phase. Seed data must include one realistic resume, multiple job descriptions, skills, projects, experience, and evidence, with all displayed analysis numbers produced by backend calculations.

## Required Developer Experience

Provide `.env.example`, setup, migration, seed, local-development, and production-build instructions. Environment variables include only configured services such as database, Redis, provider keys, GitHub token, API URL, and storage settings. The fresh-clone path must be reproducible.