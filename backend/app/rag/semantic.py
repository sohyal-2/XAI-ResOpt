"""Semantic Retrieval Engine.

Implements:
- 1536-dimensional embedding generation
- Cosine similarity and vector distance calculation
- Semantic similarity scoring
"""

from __future__ import annotations

import hashlib
import math
import re

from app.rag.models import SemanticScoreBreakdown

VECTOR_DIMENSION = 1536


def generate_embedding(text: str, dim: int = VECTOR_DIMENSION) -> list[float]:
    """Generate a deterministic 1536-dimensional unit embedding vector for any text."""
    if not text.strip():
        return [0.0] * dim

    clean_text = text.lower().strip()
    words = re.findall(r"\b\w+\b", clean_text)

    # Base projection vector
    vector = [0.0] * dim

    # Combine word-level and character n-gram projections
    features = words + [clean_text[i : i + 3] for i in range(len(clean_text) - 2)]

    for feature in features:
        # Use SHA-256 for deterministic hashing across dimensions
        digest = hashlib.sha256(feature.encode("utf-8")).digest()
        for i in range(0, min(len(digest), 32), 4):
            val = int.from_bytes(digest[i : i + 4], "big", signed=True)
            idx = abs(val) % dim
            vector[idx] += (val / 2147483648.0)

    # Normalize vector to unit length (L2 norm = 1.0)
    norm = math.sqrt(sum(x * x for x in vector))
    if norm > 0:
        return [round(x / norm, 6) for x in vector]
    return [0.0] * dim


def compute_cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two float vectors bounded in [0.0, 1.0]."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    raw_cosine = dot / (norm_a * norm_b)
    # Clip negative orthogonality to 0.0, bound positive cosine in [0.0, 1.0]
    similarity = max(0.0, min(1.0, raw_cosine))
    return round(similarity, 4)


def evaluate_semantic_match(
    query_text: str,
    doc_text: str,
    query_embedding: list[float] | None = None,
    doc_embedding: list[float] | None = None,
) -> tuple[float, SemanticScoreBreakdown]:
    """Evaluate semantic similarity between query and document."""
    q_emb = query_embedding or generate_embedding(query_text)
    d_emb = doc_embedding or generate_embedding(doc_text)

    cos_sim = compute_cosine_similarity(q_emb, d_emb)
    # Cosine distance = 1.0 - raw cosine
    vec_distance = round(1.0 - cos_sim, 4)

    breakdown = SemanticScoreBreakdown(
        cosine_similarity=cos_sim,
        vector_distance=vec_distance,
        total=cos_sim,
    )
    return cos_sim, breakdown
