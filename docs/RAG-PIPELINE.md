# Agentic RAG and Retrieval Pipeline

## Ingestion and Knowledge Model

Inputs include resume PDF/DOCX/text, JD text/document/URL, optional GitHub URL, portfolio URL, certifications, and public profile evidence. Parse deterministic structure first, then extract ambiguous fields into typed items with ID, type, text, source, location, and confidence. Normalize names, skills, synonyms, sections, dates, and source metadata.

The evidence model connects Person, Experience, Company, Role, Responsibility, Technology, Metric, Project, Achievement, Repository, Skill, Certification, Education, and External Evidence. Meaningful claims must be traceable to source evidence and have support status and confidence.

## Requirement-Aware Agentic Cycle

1. Inspect the analysis task and decompose it by job requirement.
2. Determine the evidence needed for each requirement.
3. Retrieve candidate chunks from resume, JD, and permitted external sources.
4. Rerank for lexical match, semantic meaning, evidence strength, source location, and requirement relevance.
5. Identify missing or conflicting context.
6. Optionally perform another targeted retrieval cycle.
7. Construct grounded context with evidence IDs and provenance.
8. Pass validated context to ATS, Skill, Evidence, Explainability, and downstream nodes.

The engine must not retrieve random resume text. A request such as Next.js performance optimization should target Next.js projects, optimization experience, performance metrics, and related technologies.

## Hybrid Retrieval

The lexical channel uses TF-IDF and/or BM25, n-grams, exact matching, and normalized keyword matching for ATS terminology. The semantic channel uses embeddings and pgvector similarity. Combine configurable signals:

```text
HybridScore = lexical_score * lexical_weight
            + semantic_score * semantic_weight
            + evidence_score * evidence_weight
```

Persist channel scores, weights, rank, query, requirement ID, and selected evidence. Do not claim the result is an industry-standard ATS formula.

## External Sources

GitHub profile metadata, repositories, README text, languages, descriptions, and available activity; portfolio public-page content; and other public evidence become supporting evidence only. Repository presence does not automatically prove a skill. Respect robots.txt, rate limits, API policies, and platform terms.

## Grounding Contract

Downstream context must distinguish known from evidence, inferred, unknown, and unsupported. Unsupported claims are rejected. The Copilot uses the same analysis/evidence retrieval path rather than answering blindly from general knowledge.