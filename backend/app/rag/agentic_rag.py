"""Agentic RAG Engine with explicit State Machine Architecture.

Implements the workflow:
inspect task
-> decompose query
-> identify required evidence
-> retrieve
-> rerank
-> evaluate evidence sufficiency
-> retrieve again when necessary (controlled second cycle)
-> construct grounded context
-> pass structured context to downstream agents
"""

from __future__ import annotations

import re
from typing import Literal

from langgraph.graph import END, StateGraph

from app.parsing.models import RequirementCategory
from app.rag.agentic_models import (
    AgenticRAGLogEntry,
    AgenticRAGOutput,
    AgenticRAGState,
    EvidenceSufficiencyItem,
    EvidenceSufficiencyReport,
    GroundedRequirementContext,
    SupportStatus,
    WorkflowStatus,
)
from app.rag.hybrid import ATS_SCORE_NAME, HybridRetrievalEngine, decompose_requirement_to_query
from app.rag.models import RequirementRetrievalQuery, RequirementRetrievalResult, RetrievedEvidence


# --- Graph Nodes ---


def inspect_task_node(state: AgenticRAGState) -> AgenticRAGState:
    """Validate task inputs, requirements, and evidence corpus."""
    log = AgenticRAGLogEntry(
        step="inspect_task",
        iteration=state.iteration,
        message=f"Inspecting task {state.task_id}: {len(state.requirements)} requirements, {len(state.raw_evidence_corpus)} candidate evidence items.",
        metadata={
            "owner_id": str(state.owner_id),
            "requirements_count": len(state.requirements),
            "corpus_size": len(state.raw_evidence_corpus),
        },
    )
    state.execution_logs.append(log)
    state.status = WorkflowStatus.running
    return state


def decompose_query_node(state: AgenticRAGState) -> AgenticRAGState:
    """Decompose structured job requirements into target queries and expanded synonyms."""
    queries: list[RequirementRetrievalQuery] = []
    for req in state.requirements:
        query = decompose_requirement_to_query(req)
        queries.append(query)

    state.queries = queries
    log = AgenticRAGLogEntry(
        step="decompose_query",
        iteration=state.iteration,
        message=f"Decomposed {len(queries)} requirements into keyword queries and synonyms.",
        metadata={
            "queries": [
                {
                    "text": q.requirement_text,
                    "target_terms": q.target_terms,
                    "synonyms": q.synonym_terms,
                }
                for q in queries
            ]
        },
    )
    state.execution_logs.append(log)
    return state


def identify_evidence_needs_node(state: AgenticRAGState) -> AgenticRAGState:
    """Identify specific evidence types needed for each requirement."""
    needs: dict[str, list[str]] = {}
    for req in state.requirements:
        req_needs: list[str] = []
        cat = (
            req.category
            if isinstance(req.category, RequirementCategory)
            else RequirementCategory(req.category)
            if req.category in RequirementCategory.__members__
            else RequirementCategory.skill
        )

        if cat in {
            RequirementCategory.years_experience,
            RequirementCategory.skill,
            RequirementCategory.mandatory_skill,
            RequirementCategory.preferred_skill,
            RequirementCategory.nice_to_have_skill,
        }:
            req_needs.extend(["experience", "technology", "project"])
        elif cat == RequirementCategory.responsibility:
            req_needs.extend(["experience", "responsibility", "project"])
        elif cat == RequirementCategory.education:
            req_needs.append("education")
        elif cat == RequirementCategory.certification:
            req_needs.append("certification")
        elif cat == RequirementCategory.domain_knowledge:
            req_needs.extend(["experience", "domain", "project"])
        elif cat == RequirementCategory.tooling:
            req_needs.extend(["technology", "tooling", "project"])
        elif cat == RequirementCategory.soft_skill:
            req_needs.extend(["experience", "leadership", "soft_skill"])
        else:
            req_needs.extend(["experience", "technology"])

        # Check for metric/quantitative requirement
        if re.search(
            r"\b(\d+%\b|\$\d+|\bscale\b|\bthroughput\b|\blatency\b|\breduced\b|\bincreased\b|\bimproved\b)",
            req.text,
            re.IGNORECASE,
        ):
            req_needs.append("metric")

        needs[req.text] = list(set(req_needs))

    state.evidence_needs = needs
    log = AgenticRAGLogEntry(
        step="identify_evidence_needs",
        iteration=state.iteration,
        message=f"Mapped evidence requirements for {len(needs)} items.",
        metadata={"needs": needs},
    )
    state.execution_logs.append(log)
    return state


def retrieve_node(state: AgenticRAGState) -> AgenticRAGState:
    """Execute hybrid retrieval across candidate evidence items."""
    engine = HybridRetrievalEngine(state.weights)
    results = {}

    for query in state.queries:
        # On second iteration/retry, broaden query with all synonyms and context terms
        if state.iteration > 0:
            relaxed_text = f"{query.query_text} {' '.join(query.synonym_terms)}"
            active_query = RequirementRetrievalQuery(
                requirement_id=query.requirement_id,
                requirement_text=query.requirement_text,
                category=query.category,
                kind=query.kind,
                query_text=relaxed_text,
                target_terms=query.target_terms,
                normalized_terms=query.normalized_terms,
                synonym_terms=query.synonym_terms,
            )
        else:
            active_query = query

        matches = engine.search_hybrid(
            query=active_query,
            evidence_items=state.raw_evidence_corpus,
            weights=state.weights,
            limit=5,
        )
        best_score = matches[0].hybrid_score if matches else 0.0

        results[query.requirement_text] = RequirementRetrievalResult(
            requirement_text=query.requirement_text,
            requirement_kind=query.kind,
            query=active_query,
            top_matches=matches,
            best_score=best_score,
            compatibility_score_name=ATS_SCORE_NAME,
        )

        log = AgenticRAGLogEntry(
            step="retrieve",
            iteration=state.iteration,
            query=active_query.query_text,
            retrieval_method="hybrid",
            retrieved_evidence_ids=[str(m.evidence_id) for m in matches],
            scores={str(m.evidence_id): m.hybrid_score for m in matches},
            retries=state.iteration,
            message=f"Retrieved {len(matches)} chunks for: '{query.requirement_text[:50]}...'",
        )
        state.execution_logs.append(log)

    state.retrieval_results = results
    return state


def rerank_node(state: AgenticRAGState) -> AgenticRAGState:
    """Rerank candidate matches based on category alignment and evidence quality."""
    for req_text, result in state.retrieval_results.items():
        needed_types = state.evidence_needs.get(req_text, [])
        reranked: list[RetrievedEvidence] = []

        for match in result.top_matches:
            # Check if match has substantive relevance before adding category bonus
            has_substance = match.lexical_score > 0.05 or match.semantic_score > 0.20
            category_bonus = 0.05 if (has_substance and (match.source_type in needed_types or any(t in match.source_location.lower() for t in needed_types))) else 0.0
            adjusted_score = min(1.0, max(0.0, match.hybrid_score + category_bonus))

            match_dict = match.model_dump()
            match_dict["hybrid_score"] = round(adjusted_score, 4)
            reranked.append(RetrievedEvidence(**match_dict))

        reranked.sort(key=lambda r: r.hybrid_score, reverse=True)
        result.top_matches = reranked
        result.best_score = reranked[0].hybrid_score if reranked else 0.0

    log = AgenticRAGLogEntry(
        step="rerank",
        iteration=state.iteration,
        message="Reranked evidence items with category alignment and evidence bonuses.",
        scores={text: res.best_score for text, res in state.retrieval_results.items()},
    )
    state.execution_logs.append(log)
    return state


def evaluate_sufficiency_node(state: AgenticRAGState) -> AgenticRAGState:
    """Evaluate whether retrieved evidence is sufficient or requires another targeted cycle."""
    items: list[EvidenceSufficiencyItem] = []
    sufficient_count = 0
    insufficient_count = 0
    requires_second_pass = False

    for req in state.requirements:
        result = state.retrieval_results.get(req.text)
        best_score = result.best_score if result else 0.0
        matches = result.top_matches if result else []
        top_match = matches[0] if matches else None

        # Evidence is substantively matched if it has lexical or semantic relevance
        has_substantive_match = (
            top_match is not None
            and (top_match.lexical_score > 0.10 or top_match.semantic_score > 0.35)
        )

        if req.kind == "mandatory":
            threshold = 0.35
        elif req.kind == "preferred":
            threshold = 0.30
        else:
            threshold = 0.25

        is_sufficient = best_score >= threshold and has_substantive_match
        missing_types = []

        if not is_sufficient:
            insufficient_count += 1
            missing_types = state.evidence_needs.get(req.text, ["experience", "evidence"])
            # If mandatory/preferred and under max retries, request second pass
            if req.kind in {"mandatory", "preferred"} and state.iteration < state.max_retries:
                requires_second_pass = True
            rationale = f"Best score {best_score:.2f} below threshold {threshold:.2f} or lacks substantive match for {req.kind} requirement."
        else:
            sufficient_count += 1
            rationale = f"Sufficient match found with score {best_score:.2f} >= {threshold:.2f}."

        items.append(
            EvidenceSufficiencyItem(
                requirement_text=req.text,
                requirement_kind=req.kind,
                is_sufficient=is_sufficient,
                best_score=best_score,
                matched_count=len(matches),
                missing_evidence_types=missing_types,
                rationale=rationale,
            )
        )

    # Strictly enforce max_retries boundary
    if state.iteration >= state.max_retries:
        requires_second_pass = False

    report = EvidenceSufficiencyReport(
        is_overall_sufficient=(insufficient_count == 0),
        sufficient_count=sufficient_count,
        insufficient_count=insufficient_count,
        items=items,
        requires_second_pass=requires_second_pass,
    )
    state.sufficiency_report = report

    log = AgenticRAGLogEntry(
        step="evaluate_sufficiency",
        iteration=state.iteration,
        retries=state.iteration,
        message=f"Sufficiency check: {sufficient_count} sufficient, {insufficient_count} insufficient. Second pass needed: {requires_second_pass}.",
        metadata={
            "sufficient_count": sufficient_count,
            "insufficient_count": insufficient_count,
            "requires_second_pass": requires_second_pass,
        },
    )
    state.execution_logs.append(log)
    return state


def prepare_retry_node(state: AgenticRAGState) -> AgenticRAGState:
    """Prepare for next retrieval iteration by incrementing iteration count and logging retry."""
    state.iteration += 1
    log = AgenticRAGLogEntry(
        step="prepare_retry",
        iteration=state.iteration,
        retries=state.iteration,
        message=f"Starting retrieval retry cycle {state.iteration}/{state.max_retries} with relaxed queries and synonyms.",
    )
    state.execution_logs.append(log)
    return state


def construct_grounded_context_node(state: AgenticRAGState) -> AgenticRAGState:
    """Construct structured, grounded context payloads for downstream agents."""
    contexts: list[GroundedRequirementContext] = []

    for req in state.requirements:
        result = state.retrieval_results.get(req.text)
        matches = result.top_matches if result else []
        top_score = result.best_score if result else 0.0
        top_match = matches[0] if matches else None

        has_substance = (
            top_match is not None
            and (len(top_match.matched_terms) > 0 or top_match.lexical_score > 0.08 or top_match.semantic_score > 0.30)
        )

        # Classify support status
        has_direct_keyword_match = bool(top_match and top_match.matched_terms)
        if has_substance and (top_score >= 0.45 or (has_direct_keyword_match and top_score >= 0.40)):
            support_status = SupportStatus.supported
            confidence = min(0.98, max(0.80, top_score))
        elif has_substance and (top_score >= 0.25 or has_direct_keyword_match):
            support_status = SupportStatus.partially_supported
            confidence = min(0.79, max(0.40, top_score))
        else:
            support_status = SupportStatus.unsupported
            confidence = min(0.35, max(0.0, top_score))
            # If unsupported, filter out non-relevant matches from grounded output
            matches = [m for m in matches if m.lexical_score > 0.05 or m.semantic_score > 0.25]

        missing_evidence = []
        if support_status != SupportStatus.supported:
            missing_evidence = state.evidence_needs.get(req.text, [])

        if matches and support_status != SupportStatus.unsupported:
            grounded_summary = f"Grounded by {len(matches)} evidence items. Primary match from {matches[0].source_document} ({matches[0].source_location})."
        else:
            grounded_summary = "No supporting evidence found in resume or external profiles."

        category_str = req.category.value if hasattr(req.category, "value") else str(req.category)

        context = GroundedRequirementContext(
            requirement_text=req.text,
            requirement_kind=req.kind,
            requirement_category=category_str,
            support_status=support_status,
            confidence=round(confidence, 4),
            top_score=round(top_score, 4),
            compatibility_score_name=ATS_SCORE_NAME,
            matched_evidence=matches,
            missing_evidence=missing_evidence,
            grounded_summary=grounded_summary,
        )
        contexts.append(context)

    state.grounded_contexts = contexts
    state.status = WorkflowStatus.completed

    log = AgenticRAGLogEntry(
        step="construct_grounded_context",
        iteration=state.iteration,
        message=f"Synthesized grounded context for {len(contexts)} requirements.",
        metadata={
            "supported": sum(1 for c in contexts if c.support_status == SupportStatus.supported),
            "partially_supported": sum(1 for c in contexts if c.support_status == SupportStatus.partially_supported),
            "unsupported": sum(1 for c in contexts if c.support_status == SupportStatus.unsupported),
        },
    )
    state.execution_logs.append(log)
    return state


# --- Routing & Transition Logic ---


def route_after_sufficiency(state: AgenticRAGState) -> Literal["prepare_retry", "construct_context"]:
    """Conditional routing: route to prepare_retry if second pass is needed, else construct_context."""
    if state.sufficiency_report and state.sufficiency_report.requires_second_pass and state.iteration < state.max_retries:
        return "prepare_retry"
    return "construct_context"


# --- LangGraph State Machine Builder ---


def build_agentic_rag_graph() -> StateGraph:
    """Build the LangGraph explicit StateGraph for Agentic RAG."""
    builder = StateGraph(AgenticRAGState)

    builder.add_node("inspect_task", inspect_task_node)
    builder.add_node("decompose_query", decompose_query_node)
    builder.add_node("identify_evidence_needs", identify_evidence_needs_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("rerank", rerank_node)
    builder.add_node("evaluate_sufficiency", evaluate_sufficiency_node)
    builder.add_node("prepare_retry", prepare_retry_node)
    builder.add_node("construct_context", construct_grounded_context_node)

    builder.set_entry_point("inspect_task")
    builder.add_edge("inspect_task", "decompose_query")
    builder.add_edge("decompose_query", "identify_evidence_needs")
    builder.add_edge("identify_evidence_needs", "retrieve")
    builder.add_edge("retrieve", "rerank")
    builder.add_edge("rerank", "evaluate_sufficiency")

    builder.add_conditional_edges(
        "evaluate_sufficiency",
        route_after_sufficiency,
        {
            "prepare_retry": "prepare_retry",
            "construct_context": "construct_context",
        },
    )

    builder.add_edge("prepare_retry", "retrieve")
    builder.add_edge("construct_context", END)
    return builder


_COMPILED_GRAPH = build_agentic_rag_graph().compile()


class AgenticRAGEngine:
    """Orchestrator for executing Agentic RAG workflow."""

    def __init__(self, compiled_graph=None) -> None:
        self.graph = compiled_graph or _COMPILED_GRAPH

    async def ainvoke(self, state: AgenticRAGState) -> AgenticRAGOutput:
        """Run the Agentic RAG state machine asynchronously and return structured output."""
        result_state_dict = await self.graph.ainvoke(state)
        return self._format_output(AgenticRAGState(**result_state_dict))

    def invoke(self, state: AgenticRAGState) -> AgenticRAGOutput:
        """Run the Agentic RAG state machine synchronously and return structured output."""
        result_state_dict = self.graph.invoke(state)
        return self._format_output(AgenticRAGState(**result_state_dict))

    def _format_output(self, final_state: AgenticRAGState) -> AgenticRAGOutput:
        contexts = final_state.grounded_contexts
        supported = sum(1 for c in contexts if c.support_status == SupportStatus.supported)
        partially = sum(1 for c in contexts if c.support_status == SupportStatus.partially_supported)
        unsupported = sum(1 for c in contexts if c.support_status == SupportStatus.unsupported)

        overall_score = (
            sum(c.top_score for c in contexts) / len(contexts)
            if contexts
            else 0.0
        )
        overall_score = round(min(1.0, max(0.0, overall_score)), 4)

        return AgenticRAGOutput(
            task_id=final_state.task_id,
            owner_id=final_state.owner_id,
            job_description_id=final_state.job_description_id,
            resume_version_id=final_state.resume_version_id,
            status=final_state.status,
            total_requirements=len(contexts),
            supported_count=supported,
            partially_supported_count=partially,
            unsupported_count=unsupported,
            overall_compatibility_score=overall_score,
            compatibility_score_name=ATS_SCORE_NAME,
            grounded_contexts=contexts,
            sufficiency_report=final_state.sufficiency_report or EvidenceSufficiencyReport(
                is_overall_sufficient=(unsupported == 0),
                sufficient_count=supported + partially,
                insufficient_count=unsupported,
                items=[],
            ),
            iteration_count=final_state.iteration,
            execution_logs=final_state.execution_logs,
        )
