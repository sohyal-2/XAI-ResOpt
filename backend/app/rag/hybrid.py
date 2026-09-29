"""Hybrid Retrieval and Reranking Engine.

Implements:
- Requirement-aware query decomposition
- Independent Channel 1: Lexical retrieval
- Independent Channel 2: Semantic retrieval
- Configurable Hybrid Ranker:
    HybridScore = lexical_score * lexical_weight + semantic_score * semantic_weight + evidence_score * evidence_weight
- Explicitly labeled: 'XAI-ResOpt ATS Compatibility Score'
- Full provenance and metadata preservation
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from app.models import EvidenceItem
from app.parsing.models import JobRequirementExtraction
from app.parsing.taxonomy import get_synonyms_for_canonical
from app.rag.lexical import evaluate_lexical_match, tokenize
from app.rag.models import (
    RequirementRetrievalQuery,
    RequirementRetrievalResult,
    RetrievalMethod,
    RetrievalWeights,
    RetrievedEvidence,
)
from app.rag.semantic import evaluate_semantic_match, generate_embedding

ATS_SCORE_NAME = "XAI-ResOpt ATS Compatibility Score"


def decompose_requirement_to_query(
    requirement: JobRequirementExtraction,
    requirement_id: UUID | None = None,
) -> RequirementRetrievalQuery:
    """Decompose a structured job requirement into target keywords, synonyms, and search text."""
    target_terms = list(requirement.original_terms)
    normalized_terms = list(requirement.normalized_terms)

    # Expand synonyms for all canonical terms
    synonyms: list[str] = []
    for norm in normalized_terms:
        synonyms.extend(get_synonyms_for_canonical(norm))

    # Formulate query text with primary terms and context
    query_parts = target_terms if target_terms else tokenize(requirement.text)
    query_text = " ".join(query_parts) if query_parts else requirement.text

    return RequirementRetrievalQuery(
        requirement_id=requirement_id,
        requirement_text=requirement.text,
        category=requirement.category.value if hasattr(requirement.category, "value") else str(requirement.category),
        kind=requirement.kind,
        query_text=query_text,
        target_terms=target_terms,
        normalized_terms=normalized_terms,
        synonym_terms=list(set(synonyms)),
    )


def _get_item_attr(item: Any, attr: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(attr, default)
    val = getattr(item, attr, None)
    return val if val is not None else default


class HybridRetrievalEngine:
    """Engine executing lexical, semantic, and hybrid retrieval over evidence stores."""

    def __init__(self, default_weights: RetrievalWeights | None = None) -> None:
        self.default_weights = (default_weights or RetrievalWeights()).normalized()

    def search_lexical(
        self,
        query: RequirementRetrievalQuery,
        evidence_items: list[EvidenceItem | dict[str, Any]],
        limit: int = 10,
    ) -> list[RetrievedEvidence]:
        """Execute Channel 1: Lexical-only retrieval."""
        weights = RetrievalWeights(lexical_weight=1.0, semantic_weight=0.0, evidence_weight=0.0)
        return self._rank_corpus(
            query=query,
            evidence_items=evidence_items,
            weights=weights,
            method=RetrievalMethod.lexical_only,
            limit=limit,
        )

    def search_semantic(
        self,
        query: RequirementRetrievalQuery,
        evidence_items: list[EvidenceItem | dict[str, Any]],
        limit: int = 10,
    ) -> list[RetrievedEvidence]:
        """Execute Channel 2: Semantic-only retrieval."""
        weights = RetrievalWeights(lexical_weight=0.0, semantic_weight=1.0, evidence_weight=0.0)
        return self._rank_corpus(
            query=query,
            evidence_items=evidence_items,
            weights=weights,
            method=RetrievalMethod.semantic_only,
            limit=limit,
        )

    def search_hybrid(
        self,
        query: RequirementRetrievalQuery,
        evidence_items: list[EvidenceItem | dict[str, Any]],
        weights: RetrievalWeights | None = None,
        limit: int = 10,
    ) -> list[RetrievedEvidence]:
        """Execute Hybrid Retrieval combining Lexical, Semantic, and Evidence signals."""
        configured_weights = (weights or self.default_weights).normalized()
        return self._rank_corpus(
            query=query,
            evidence_items=evidence_items,
            weights=configured_weights,
            method=RetrievalMethod.hybrid,
            limit=limit,
        )

    def retrieve_for_requirement(
        self,
        requirement: JobRequirementExtraction,
        evidence_items: list[EvidenceItem | dict[str, Any]],
        weights: RetrievalWeights | None = None,
        requirement_id: UUID | None = None,
        limit: int = 5,
    ) -> RequirementRetrievalResult:
        """Run requirement-aware retrieval and return structured match result."""
        query = decompose_requirement_to_query(requirement, requirement_id=requirement_id)
        matches = self.search_hybrid(query, evidence_items, weights=weights, limit=limit)
        best_score = matches[0].hybrid_score if matches else 0.0

        return RequirementRetrievalResult(
            requirement_text=requirement.text,
            requirement_kind=requirement.kind,
            query=query,
            top_matches=matches,
            best_score=best_score,
            compatibility_score_name=ATS_SCORE_NAME,
        )

    def _rank_corpus(
        self,
        query: RequirementRetrievalQuery,
        evidence_items: list[EvidenceItem | dict[str, Any]],
        weights: RetrievalWeights,
        method: RetrievalMethod,
        limit: int = 10,
    ) -> list[RetrievedEvidence]:
        """Perform evaluation across corpus and rank by calculated hybrid score."""
        if not evidence_items:
            return []

        # Prepare corpus texts for BM25 background
        corpus_texts = [_get_item_attr(item, "text", "") for item in evidence_items]
        corpus_token_docs = [tokenize(t) for t in corpus_texts]

        # Generate query embedding once for semantic comparisons
        query_embedding = generate_embedding(query.query_text)

        results: list[RetrievedEvidence] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for item in evidence_items:
            item_id = _get_item_attr(item, "id", uuid4())
            text = _get_item_attr(item, "text", "")
            norm_text = _get_item_attr(item, "normalized_text", text.lower())
            src_doc = _get_item_attr(item, "source_document", _get_item_attr(item, "source", "unknown"))
            src_loc = _get_item_attr(item, "source_location", _get_item_attr(item, "location", "unknown"))
            src_type = _get_item_attr(item, "source_type", _get_item_attr(item, "type", "resume"))
            confidence = float(_get_item_attr(item, "confidence", 0.90))
            embedding = _get_item_attr(item, "embedding", None)

            # 1. Evaluate Lexical match
            all_target_terms = query.target_terms + query.synonym_terms
            lex_score, lex_breakdown, matched_terms = evaluate_lexical_match(
                query_text=query.query_text,
                target_terms=all_target_terms,
                normalized_terms=query.normalized_terms,
                doc_text=text,
                corpus_token_docs=corpus_token_docs,
            )

            # 2. Evaluate Semantic match
            sem_score, sem_breakdown = evaluate_semantic_match(
                query_text=query.query_text,
                doc_text=text,
                query_embedding=query_embedding,
                doc_embedding=embedding,
            )

            # 3. Evidence quality score
            ev_score = min(1.0, max(0.0, confidence))

            # 4. Calculate HybridScore
            hybrid_score = (
                lex_score * weights.lexical_weight
                + sem_score * weights.semantic_weight
                + ev_score * weights.evidence_weight
            )
            hybrid_score = round(min(1.0, max(0.0, hybrid_score)), 4)

            provenance = {
                "timestamp": now_iso,
                "requirement_id": str(query.requirement_id) if query.requirement_id else None,
                "requirement_category": query.category,
                "requirement_kind": query.kind,
                "weights": weights.model_dump(),
                "lexical_breakdown": lex_breakdown.model_dump(),
                "semantic_breakdown": sem_breakdown.model_dump(),
                "evidence_confidence": confidence,
            }

            retrieved = RetrievedEvidence(
                evidence_id=item_id,
                chunk_text=text,
                normalized_text=norm_text,
                source_document=src_doc or "unknown",
                source_location=src_loc or "unknown",
                source_type=src_type,
                score_name=ATS_SCORE_NAME,
                hybrid_score=hybrid_score,
                lexical_score=lex_score,
                semantic_score=sem_score,
                evidence_score=ev_score,
                retrieval_method=method,
                matched_terms=matched_terms,
                lexical_breakdown=lex_breakdown,
                semantic_breakdown=sem_breakdown,
                provenance=provenance,
            )
            results.append(retrieved)

        # Sort descending by hybrid_score
        results.sort(key=lambda r: r.hybrid_score, reverse=True)
        return results[:limit]
