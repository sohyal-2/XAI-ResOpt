from uuid import uuid4

import pytest

from app.models import EvidenceItem, JobRequirement, JobRequirementKind
from app.parsing.models import JobRequirementExtraction, RequirementCategory
from app.rag.hybrid import ATS_SCORE_NAME, HybridRetrievalEngine, decompose_requirement_to_query
from app.rag.lexical import (
    compute_bm25_score,
    compute_exact_keyword_score,
    compute_ngram_similarity,
    compute_normalized_keyword_score,
    tokenize,
)
from app.rag.models import (
    RetrievalMethod,
    RetrievalWeights,
    RetrievedEvidence,
)
from app.rag.semantic import (
    VECTOR_DIMENSION,
    compute_cosine_similarity,
    generate_embedding,
)
from app.rag.service import RetrievalService

MOCK_CORPUS = [
    EvidenceItem(
        id=uuid4(),
        owner_id=uuid4(),
        source_uri="resume.pdf",
        source_type="resume",
        source_document="resume.pdf",
        source_location="Experience > Fintech Corp > Bullet 1",
        evidence_type="experience",
        text="Engineered high-throughput REST APIs and microservices using Python and FastAPI for financial transaction processing.",
        confidence=0.95,
        normalized_text="engineered high-throughput rest apis and microservices using python and fastapi for financial transaction processing.",
        embedding=generate_embedding("Engineered high-throughput REST APIs and microservices using Python and FastAPI for financial transaction processing."),
    ),
    EvidenceItem(
        id=uuid4(),
        owner_id=uuid4(),
        source_uri="resume.pdf",
        source_type="resume",
        source_document="resume.pdf",
        source_location="Experience > WebApp Inc > Bullet 2",
        evidence_type="experience",
        text="Developed responsive web applications with ReactJS, TypeScript, and Tailwind CSS, improving UI performance by 40%.",
        confidence=0.92,
        normalized_text="developed responsive web applications with reactjs, typescript, and tailwind css, improving ui performance by 40%.",
        embedding=generate_embedding("Developed responsive web applications with ReactJS, TypeScript, and Tailwind CSS, improving UI performance by 40%."),
    ),
    EvidenceItem(
        id=uuid4(),
        owner_id=uuid4(),
        source_uri="https://github.com/developer/rag-tools",
        source_type="github",
        source_document="https://github.com/developer/rag-tools",
        source_location="README.md > Overview",
        evidence_type="project",
        text="Open source Agentic RAG framework integrating LangGraph, pgvector, and PostgreSQL for document evaluation.",
        confidence=0.88,
        normalized_text="open source agentic rag framework integrating langgraph, pgvector, and postgresql for document evaluation.",
        embedding=generate_embedding("Open source Agentic RAG framework integrating LangGraph, pgvector, and PostgreSQL for document evaluation."),
    ),
    EvidenceItem(
        id=uuid4(),
        owner_id=uuid4(),
        source_uri="resume.pdf",
        source_type="resume",
        source_document="resume.pdf",
        source_location="Education > University",
        evidence_type="education",
        text="Bachelor of Science in Computer Science with focus on Distributed Systems and Software Architecture.",
        confidence=0.98,
        normalized_text="bachelor of science in computer science with focus on distributed systems and software architecture.",
        embedding=generate_embedding("Bachelor of Science in Computer Science with focus on Distributed Systems and Software Architecture."),
    ),
]


def test_lexical_tokenization_and_ngrams() -> None:
    tokens = tokenize("Building scalable REST APIs with FastAPI & Python!")
    assert "scalable" in tokens
    assert "apis" in tokens or "api" in tokens or "rest" in tokens
    assert "fastapi" in tokens
    assert "python" in tokens
    assert "with" not in tokens  # Stop word removed


def test_lexical_bm25_scoring() -> None:
    q_tokens = ["python", "fastapi"]
    doc_1_tokens = ["engineered", "rest", "apis", "python", "fastapi"]
    doc_2_tokens = ["developed", "reactjs", "typescript", "tailwind"]
    corpus = [doc_1_tokens, doc_2_tokens]

    score_1 = compute_bm25_score(q_tokens, doc_1_tokens, corpus)
    score_2 = compute_bm25_score(q_tokens, doc_2_tokens, corpus)

    assert score_1 > score_2
    assert score_1 > 0.0
    assert score_2 == 0.0


def test_lexical_exact_and_normalized_keyword_matching() -> None:
    # Exact keyword matching
    score_exact, matched_exact = compute_exact_keyword_score(["Python", "FastAPI"], MOCK_CORPUS[0].text)
    assert score_exact == 1.0
    assert len(matched_exact) == 2

    # Normalized keyword matching (React.js query matching ReactJS in text)
    score_norm, matched_norm = compute_normalized_keyword_score(["react"], MOCK_CORPUS[1].text)
    assert score_norm == 1.0
    assert "react" in matched_norm


def test_lexical_ngram_similarity() -> None:
    sim_high = compute_ngram_similarity("Distributed Systems Architecture", "Distributed Systems and Software Architecture")
    sim_low = compute_ngram_similarity("Distributed Systems Architecture", "React Frontend Development")
    assert sim_high > sim_low
    assert sim_high > 0.4


def test_semantic_embedding_generation_and_cosine_similarity() -> None:
    emb_1 = generate_embedding("Python FastAPI backend development")
    emb_2 = generate_embedding("FastAPI Python backend API engineering")
    emb_3 = generate_embedding("Ancient Roman history and archaeology")

    assert len(emb_1) == VECTOR_DIMENSION
    assert len(emb_2) == VECTOR_DIMENSION

    # Close semantic vectors have higher similarity
    sim_related = compute_cosine_similarity(emb_1, emb_2)
    sim_unrelated = compute_cosine_similarity(emb_1, emb_3)

    assert sim_related > sim_unrelated
    assert sim_related > 0.50


def test_requirement_aware_query_decomposition() -> None:
    req = JobRequirementExtraction(
        text="3+ years experience with React.js and TypeScript building accessible frontend UIs",
        kind="mandatory",
        category=RequirementCategory.skill,
        source_location="Mandatory Skills > line 2",
        original_terms=["React.js", "TypeScript"],
        normalized_terms=["react", "typescript"],
        years_experience=3,
        confidence=0.95,
    )
    query = decompose_requirement_to_query(req)
    assert "React.js" in query.target_terms
    assert "TypeScript" in query.target_terms
    assert "react" in query.normalized_terms
    assert any("ReactJS" in syn for syn in query.synonym_terms)
    assert query.category == "skill"
    assert query.kind == "mandatory"


def test_compares_lexical_semantic_and_hybrid_retrieval() -> None:
    engine = HybridRetrievalEngine()
    req = JobRequirementExtraction(
        text="Experience with React.js and frontend user interfaces",
        kind="mandatory",
        category=RequirementCategory.skill,
        source_location="Skills > line 1",
        original_terms=["React.js"],
        normalized_terms=["react"],
        confidence=0.90,
    )
    query = decompose_requirement_to_query(req)

    # 1. Lexical-only retrieval
    lexical_results = engine.search_lexical(query, MOCK_CORPUS, limit=4)
    assert len(lexical_results) > 0
    assert lexical_results[0].retrieval_method == RetrievalMethod.lexical_only
    assert lexical_results[0].lexical_score > 0
    # React chunk should be #1
    assert "ReactJS" in lexical_results[0].chunk_text

    # 2. Semantic-only retrieval
    semantic_results = engine.search_semantic(query, MOCK_CORPUS, limit=4)
    assert len(semantic_results) > 0
    assert semantic_results[0].retrieval_method == RetrievalMethod.semantic_only
    assert semantic_results[0].semantic_score > 0

    # 3. Hybrid retrieval
    hybrid_results = engine.search_hybrid(
        query,
        MOCK_CORPUS,
        weights=RetrievalWeights(lexical_weight=0.50, semantic_weight=0.40, evidence_weight=0.10),
        limit=4,
    )
    assert len(hybrid_results) > 0
    top = hybrid_results[0]
    assert top.retrieval_method == RetrievalMethod.hybrid
    assert top.score_name == ATS_SCORE_NAME
    assert 0.0 <= top.hybrid_score <= 1.0
    assert top.lexical_score > 0
    assert top.semantic_score > 0
    assert top.evidence_score > 0


def test_hybrid_score_calculation_with_custom_weights() -> None:
    engine = HybridRetrievalEngine()
    req = JobRequirementExtraction(
        text="FastAPI backend engineer with Python experience",
        kind="mandatory",
        category=RequirementCategory.skill,
        source_location="Skills > line 1",
        original_terms=["FastAPI", "Python"],
        normalized_terms=["fastapi", "python"],
        confidence=0.95,
    )
    query = decompose_requirement_to_query(req)

    # Weight set A: Heavily lexical
    weights_lex = RetrievalWeights(lexical_weight=0.80, semantic_weight=0.10, evidence_weight=0.10)
    res_lex = engine.search_hybrid(query, MOCK_CORPUS, weights=weights_lex, limit=1)[0]

    # Weight set B: Heavily semantic
    weights_sem = RetrievalWeights(lexical_weight=0.10, semantic_weight=0.80, evidence_weight=0.10)
    res_sem = engine.search_hybrid(query, MOCK_CORPUS, weights=weights_sem, limit=1)[0]

    assert res_lex.score_name == "XAI-ResOpt ATS Compatibility Score"
    assert res_sem.score_name == "XAI-ResOpt ATS Compatibility Score"
    assert res_lex.hybrid_score != res_sem.hybrid_score or res_lex.lexical_score == res_sem.semantic_score


def test_provenance_and_metadata_preservation() -> None:
    engine = HybridRetrievalEngine()
    req = JobRequirementExtraction(
        text="Knowledge of Agentic RAG and vector search",
        kind="nice_to_have",
        category=RequirementCategory.skill,
        source_location="Nice to Have > line 3",
        original_terms=["Agentic RAG"],
        normalized_terms=["rag"],
        confidence=0.90,
    )
    result = engine.retrieve_for_requirement(req, MOCK_CORPUS, limit=2)

    assert result.compatibility_score_name == ATS_SCORE_NAME
    assert len(result.top_matches) > 0

    top_match = result.top_matches[0]
    assert isinstance(top_match, RetrievedEvidence)
    assert top_match.evidence_id is not None
    assert top_match.source_document == "https://github.com/developer/rag-tools"
    assert top_match.source_type == "github"
    assert top_match.source_location == "README.md > Overview"
    assert "Agentic RAG" in top_match.chunk_text
    assert top_match.provenance["requirement_kind"] == "nice_to_have"
    assert "timestamp" in top_match.provenance
    assert "weights" in top_match.provenance
    assert "lexical_breakdown" in top_match.provenance
    assert "semantic_breakdown" in top_match.provenance


@pytest.mark.asyncio
async def test_retrieval_service_orchestration() -> None:
    service = RetrievalService()
    user_id = uuid4()
    req = JobRequirement(
        id=uuid4(),
        job_description_id=uuid4(),
        text="Python backend developer",
        kind=JobRequirementKind.mandatory,
        category="skill",
        source_location="Requirements > line 1",
        original_terms=["Python"],
        normalized_terms=["python"],
        confidence=0.90,
    )

    class MockAsyncSession:
        async def scalars(self, stmt):
            class MockResult:
                def all(self):
                    return MOCK_CORPUS
            return MockResult()

    mock_db = MockAsyncSession()
    result = await service.retrieve_for_requirement_db(mock_db, user_id, req, limit=3)

    assert result.compatibility_score_name == ATS_SCORE_NAME
    assert len(result.top_matches) > 0
    assert result.top_matches[0].score_name == ATS_SCORE_NAME
    assert result.best_score > 0.0
