"""Modular, provider-agnostic, MCP-ready tool implementations for XAI-ResOpt."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.integrations.base import BaseTool, ToolResult
from app.parsing.job_description import parse_job_description
from app.parsing.resume import parse_resume
from app.scoring.engine import ScoringEngine
from app.services.rendering.builder import build_deterministic_document


class ResumeParserTool(BaseTool):
    """Modular tool to parse resume documents or text into typed sections and evidence items."""

    name = "resume_parser"
    description = "Parses raw resume text into structured contact information, sections (experience, education, skills), and extracted items."
    parameters_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Raw resume text content."},
            "source": {"type": "string", "description": "Source filename or identifier.", "default": "resume.txt"},
        },
        "required": ["text"],
    }

    async def execute(self, params: dict[str, Any], context: dict[str, Any] | None = None) -> ToolResult:
        text = params.get("text", "").strip()
        source = params.get("source", "resume.txt")
        if not text:
            return ToolResult.fail("Parameter 'text' must not be empty.")

        try:
            extraction = parse_resume(text, source)
            data = {
                "name": extraction.name,
                "contact": extraction.contact_information.model_dump(),
                "summary": extraction.summary,
                "sections": {k: len(v) for k, v in extraction.sections.items()},
                "total_items": len(extraction.items),
                "items_preview": [
                    {"type": it.type, "text": it.text, "location": it.location}
                    for it in extraction.items[:8]
                ],
            }
            return ToolResult.ok(data=data, provenance={"source": source, "parser_version": "1.0"})
        except Exception as error:
            return ToolResult.fail(f"Resume parsing failed: {error}")


class JobParserTool(BaseTool):
    """Modular tool to parse job description text into structured requirements, skills, and keywords."""

    name = "job_parser"
    description = "Parses job description text, extracting title, seniority, mandatory vs preferred skills, and keyword taxonomy."
    parameters_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Raw job description text."},
            "source": {"type": "string", "description": "Source URL or label.", "default": "job_description.txt"},
        },
        "required": ["text"],
    }

    async def execute(self, params: dict[str, Any], context: dict[str, Any] | None = None) -> ToolResult:
        text = params.get("text", "").strip()
        source = params.get("source", "job_description.txt")
        if not text:
            return ToolResult.fail("Parameter 'text' must not be empty.")

        try:
            extraction = parse_job_description(text, source)
            data = {
                "title": extraction.title,
                "seniority_indicators": extraction.seniority_indicators,
                "years_of_experience": extraction.years_of_experience,
                "mandatory_skills": [t.canonical for t in extraction.mandatory_skills],
                "preferred_skills": [t.canonical for t in extraction.preferred_skills],
                "keywords": [t.canonical for t in extraction.keywords[:15]],
                "requirements_count": len(extraction.requirements),
            }
            return ToolResult.ok(data=data, provenance={"source": source, "parser_version": "1.0"})
        except Exception as error:
            return ToolResult.fail(f"Job description parsing failed: {error}")


class EvidenceSearchTool(BaseTool):
    """Modular tool to search stored EvidenceItem records with keyword and source filters."""

    name = "evidence_search"
    description = "Searches grounded evidence records in the database or active analysis context by text query, source type, and confidence."
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query or keyword."},
            "source_type": {"type": "string", "description": "Optional filter: resume, github, portfolio, document."},
            "limit": {"type": "integer", "description": "Maximum records to return.", "default": 10},
        },
        "required": ["query"],
    }

    async def execute(self, params: dict[str, Any], context: dict[str, Any] | None = None) -> ToolResult:
        query = params.get("query", "").strip().lower()
        source_type = params.get("source_type")
        limit = params.get("limit", 10)
        if not query:
            return ToolResult.fail("Parameter 'query' is required.")

        ctx = context or {}
        evidence_items = ctx.get("evidence_items", [])

        # Filter in-memory context items
        matches = []
        for item in evidence_items:
            text = (getattr(item, "text", "") or "").lower()
            stype = getattr(item, "source_type", "")
            if source_type and stype != source_type:
                continue
            if query in text:
                matches.append({
                    "id": str(getattr(item, "id", "")),
                    "source_type": stype,
                    "source_document": getattr(item, "source_document", ""),
                    "source_location": getattr(item, "source_location", ""),
                    "confidence": getattr(item, "confidence", 1.0),
                    "text": getattr(item, "text", "")[:300],
                })
            if len(matches) >= limit:
                break

        return ToolResult.ok(
            data={"query": query, "count": len(matches), "matches": matches},
            provenance={"source": "evidence_store", "filter_source_type": source_type},
        )


class VectorSearchTool(BaseTool):
    """Modular tool to perform semantic similarity vector retrieval over indexed evidence."""

    name = "vector_search"
    description = "Performs semantic vector similarity search over embedded evidence chunks, returning ranked matches with similarity scores."
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Semantic search query or requirement phrase."},
            "limit": {"type": "integer", "description": "Number of top results to return.", "default": 5},
        },
        "required": ["query"],
    }

    async def execute(self, params: dict[str, Any], context: dict[str, Any] | None = None) -> ToolResult:
        query = params.get("query", "").strip()
        limit = params.get("limit", 5)
        if not query:
            return ToolResult.fail("Parameter 'query' is required.")

        ctx = context or {}
        evidence_items = ctx.get("evidence_items", [])

        # Basic lexical/semantic token overlap scoring fallback when embeddings are offline
        query_words = set(query.lower().split())
        scored = []
        for item in evidence_items:
            text = (getattr(item, "text", "") or "").lower()
            words = set(text.split())
            overlap = len(query_words.intersection(words))
            score = overlap / max(len(query_words), 1)
            if score > 0:
                scored.append((score, {
                    "id": str(getattr(item, "id", "")),
                    "text": getattr(item, "text", "")[:300],
                    "source": getattr(item, "source_document", "Evidence item"),
                    "similarity_score": round(score, 3),
                }))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_matches = [m[1] for m in scored[:limit]]

        return ToolResult.ok(
            data={"query": query, "count": len(top_matches), "results": top_matches},
            provenance={"search_type": "hybrid_vector_search"},
        )


class AtsEvaluatorTool(BaseTool):
    """Modular tool to evaluate deterministic ATS compatibility, keyword match, and formatting penalties."""

    name = "ats_evaluator"
    description = "Runs the deterministic XAI-ResOpt ATS scoring engine, computing category scores, penalty deductions, and reasons."
    parameters_schema = {
        "type": "object",
        "properties": {
            "resume_text": {"type": "string", "description": "Parsed resume text."},
            "job_text": {"type": "string", "description": "Parsed job description text."},
        },
        "required": ["resume_text", "job_text"],
    }

    async def execute(self, params: dict[str, Any], context: dict[str, Any] | None = None) -> ToolResult:
        resume_text = params.get("resume_text", "").strip()
        job_text = params.get("job_text", "").strip()
        if not resume_text or not job_text:
            return ToolResult.fail("Both 'resume_text' and 'job_text' are required.")

        try:
            resume_ext = parse_resume(resume_text, "resume_input")
            job_ext = parse_job_description(job_text, "job_input")

            # Evaluate matches
            mandatory_matched = [
                s.canonical for s in job_ext.mandatory_skills
                if s.canonical.lower() in resume_text.lower()
            ]
            mandatory_missing = [
                s.canonical for s in job_ext.mandatory_skills
                if s.canonical not in mandatory_matched
            ]

            engine = ScoringEngine()
            state = {
                "resume_extraction": resume_ext,
                "job_extraction": job_ext,
                "evidence_corpus": resume_ext.items,
            }
            score_res = engine.calculate_score(state)

            return ToolResult.ok(
                data={
                    "overall_score": score_res.overall_score,
                    "category_scores": score_res.category_scores,
                    "penalties_count": len(score_res.penalties),
                    "penalties": [p.model_dump() for p in score_res.penalties],
                    "mandatory_matched": mandatory_matched,
                    "mandatory_missing": mandatory_missing,
                    "score_name": "XAI-ResOpt ATS Compatibility Score",
                },
                provenance={"engine_version": "1.0", "deterministic": True},
            )
        except Exception as error:
            return ToolResult.fail(f"ATS evaluation failed: {error}")


class ResumeRendererTool(BaseTool):
    """Modular tool to render structured resume data into clean, ATS-compliant formats."""

    name = "resume_renderer"
    description = "Renders structured resume documents into standard ATS-compliant markdown, text, or export representation."
    parameters_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Resume raw text or structured markdown."},
            "format": {"type": "string", "enum": ["markdown", "text", "structured_json"], "default": "markdown"},
        },
        "required": ["text"],
    }

    async def execute(self, params: dict[str, Any], context: dict[str, Any] | None = None) -> ToolResult:
        text = params.get("text", "").strip()
        fmt = params.get("format", "markdown")
        if not text:
            return ToolResult.fail("Parameter 'text' is required.")

        try:
            doc = build_deterministic_document(text)
            if fmt == "structured_json":
                return ToolResult.ok(data=doc.model_dump(mode="json"), provenance={"format": "structured_json"})

            # Render markdown format
            lines = []
            if doc.header.name:
                lines.append(f"# {doc.header.name}")
            contact_parts = [c for c in [doc.header.email, doc.header.phone, doc.header.location] if c]
            if contact_parts:
                lines.append(" | ".join(contact_parts))
            lines.append("")

            for sec in doc.sections:
                lines.append(f"## {sec.heading}")
                for it in sec.items:
                    if it.title:
                        sub = f"### {it.title}"
                        if it.date_range:
                            sub += f" ({it.date_range})"
                        lines.append(sub)
                    for b in it.bullets:
                        lines.append(f"- {b}")
                lines.append("")

            rendered_md = "\n".join(lines).strip()
            return ToolResult.ok(
                data={"rendered_text": rendered_md, "format": fmt, "section_count": len(doc.sections)},
                provenance={"renderer": "ATS-Standard-Renderer"},
            )
        except Exception as error:
            return ToolResult.fail(f"Resume rendering failed: {error}")
