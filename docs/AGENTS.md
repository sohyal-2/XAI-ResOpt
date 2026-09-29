# XAI-ResOpt Agent Responsibilities

Agents are explicit workflow nodes sharing validated structured state. They are not independent prompt calls. Each run records input/output references, duration, retry count, warnings, and failure details.

## Nodes

- **Intake Agent:** classifies files and URLs, triggers parsing, normalizes inputs, and reports ingestion failures.
- **ATS Agent:** evaluates keyword coverage, exact terminology, section presence/naming, formatting risks, contact/readability/parsability, distribution, and requirement coverage; returns structured JSON.
- **Skill Agent:** evaluates semantic and mandatory/preferred skill coverage, gaps, transferable evidence, seniority, and relevance.
- **Evidence Agent:** evaluates factual support, source provenance, claim confidence, unsupported claims, contradictions, and evidence sufficiency. Important recommendations reference evidence IDs.
- **Explainability layer/agent:** explains scores, penalties, recommendations, rewrite safety, and rejection reasons using concrete evidence rather than generic prose.
- **Optimizer Agent:** proposes targeted bullet, summary, skills, ordering, clarity, impact, and keyword changes using only supported evidence.
- **Critic Agent:** evaluates relevance, clarity, grammar, conciseness, keyword quality, ATS compatibility, professional quality, and factual risk.
- **Fact-Check Agent:** verifies metrics, companies, dates, titles, technologies, responsibilities, certifications, projects, and numerical claims; rejects unsupported content.
- **ATS Re-Evaluator:** reruns the scoring pipeline and returns before score, after score, delta, improved flag, remaining gaps, and new risks.

## Supporting Nodes

The **document parser** performs deterministic parsing first and structured AI extraction only for ambiguity. The **JD analyzer** extracts and classifies mandatory, preferred, nice-to-have, and contextual requirements, including synonyms and seniority indicators. The **RAG engine** decomposes tasks, retrieves/reranks requirement-specific evidence, detects missing context, and builds grounded context.

## Control Rules

Pass/fail validation occurs before re-evaluation. The optimizer loop has an explicit maximum of 2–3 cycles or a configured equivalent, never an infinite loop. Each iteration persists score, changes, rejected changes, validation issues, and evidence used. Human approval is required before final generation.