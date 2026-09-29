# XAI-ResOpt Testing Strategy

## Unit Tests

Cover deterministic document parsing and normalization, JD requirement classification and synonym handling, TF-IDF/BM25 keyword matching, embedding/reranking score combination, evidence/provenance validation, unsupported-claim rejection, deterministic score dimensions/penalties, optimization stop conditions, and hallucination/fact checks.

## Integration Tests

Exercise authenticated API contracts, PostgreSQL schemas and foreign keys, pgvector retrieval, Redis job/status behavior, file/storage abstraction, parser-to-evidence persistence, agent state transitions, structured output validation, score persistence, optimization iterations, approval history, and rendering/export services.

## End-to-End Acceptance Flow

Test the complete user path:

```text
Sign up -> upload resume -> provide JD -> optional integrations
-> start analysis -> observe real progress -> view baseline
-> inspect ATS/skills/evidence -> ask Copilot
-> optimize -> review changes/evidence -> fact-check
-> re-score -> compare -> accept/reject -> download PDF
```

Also verify version/history behavior, failure and retry states, malformed files, invalid URLs, missing provider keys, timeouts, retrieval failures, database failures, malformed model outputs, agent failure, and validation failure.

## Responsive and Accessibility Tests

Run critical flows at approximately 375, 768, 1024, 1440, and 1920px. Verify drawer/collapsed layouts, readable tables/charts, touch targets, keyboard navigation, focus states, labels, headings, dialogs, contrast, file upload accessibility, and usable Copilot behavior.

## Quality Gates

No fake scores or agent activity, unsupported claims cannot silently pass, navigation has no dead actions, normal usage has no console errors, loading/empty/success/failure/retry states exist, and blocking failures stop phase progression. Seed/demo data must exercise real backend calculations rather than disconnected static numbers.

## Automated Test Execution & Verification

### Running All Automated Backend Tests
```powershell
# Set backend directory on pythonpath
$env:PYTHONPATH='backend'
python -m pytest backend/tests -v
```

### Running All Frontend Tests & Quality Gates
```powershell
# Run frontend unit tests
npm --prefix frontend run test

# Run TypeScript type safety check
npm --prefix frontend run typecheck

# Run Next.js 15 production build
npm --prefix frontend run build
```

### Verified Backend Test Suites (119 Passed, 0 Failed, 0 Skipped)
1. **Unit Tests**:
   - `test_ingestion.py`: Parsing text, PDF, and DOCX documents with section boundary extraction and provenance tracking.
   - `test_job_intelligence.py`: JD requirement parsing, taxonomy classification (mandatory, preferred, nice-to-have), and term normalization.
   - `test_rag_retrieval.py`: TF-IDF/BM25 lexical scoring, n-grams, semantic cosine similarity, hybrid combination, and reranking.
   - `test_evidence.py`: Evidence extraction, candidate claim grounding, and contradiction detection.
   - `test_scoring_engine.py`: Deterministic 8-dimension scoring, custom weights normalization, penalties, and traceability graphs.
   - `test_optimization_agents.py`: Fact-checker hallucination detection (unsupported metrics, invented skills, invented employers).
   - `test_analysis_agents.py`: Individual analysis agent execution and structured output schemas.

2. **Integration Tests**:
   - `test_auth.py`: User registration, authentication, JWT tokens, and tenant isolation.
   - `test_baseline_analysis.py`: Ingestion to baseline analysis orchestration.
   - `test_closed_loop_optimization.py`: Iterative optimization loops, convergence, and re-scoring.
   - `test_human_review.py`: Human-in-the-loop review, change approval/rejection, and version branching.
   - `test_resume_generation.py`: Deterministic document builders, PDF & DOCX rendering, and export downloads.
   - `test_agent_observability.py`: Redis-backed real-time progress, duration tracking, and agent telemetry.
   - `test_agentic_rag.py`: Multi-turn retrieval-augmented generation flows.
   - `test_ai_providers.py`: Provider abstraction adapters (OpenAI, Anthropic, Gemini, OpenRouter, Ollama, Mock).
   - `test_external_integrations.py`: GitHub search, repository reader, and portfolio scraper integration tools.
   - `test_health.py`: Live PostgreSQL + pgvector and Redis dependency health checks.
   - `test_security_audit.py`: Authentication enforcement, tenant isolation, magic bytes, SSRF blockers, and rate limiting.

3. **End-to-End User Flow**:
   - `test_e2e_complete_flow.py`: Complete 16-step user journey from Sign up → Login → Upload Resume → Add JD → Analyze → View Baseline → Inspect Evidence → Optimize → Critic → Fact Check → Re-score → Compare → Review Changes → Approve → Generate Resume → Download.

4. **Failure Resilience & Edge Cases**:
   - `test_failure_resilience_and_edge_cases.py`: Invalid/empty/oversized/poisoned files, corrupt PDF/DOCX headers, malformed LLM outputs, failed agent telemetry & error tracking, fact-checker hallucination penalties, repeated optimization stability, and missing API key offline fallbacks.

5. **Development / Demo Seed Dataset**:
   - `test_demo_seed.py`: Verifies realistic candidate resume, 3 distinct JDs, structured skills/projects/experiences, supported & unsupported claims, 100% computed baseline scores across all 8 dimensions, closed-loop optimization, and rejected unsupported claims.
   - Run seed script directly: `python backend/scripts/seed_demo_data.py` (seeds `demo@xairesopt.dev` / `DemoPassword123!#`).
