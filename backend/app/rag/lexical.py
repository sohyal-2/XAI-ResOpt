"""Lexical Retrieval Engine.

Implements:
- BM25 retrieval
- Exact keyword matching
- Normalized keyword matching (with taxonomy/synonym awareness)
- Character and word n-gram matching
"""

from __future__ import annotations

import math
import re
from collections import Counter

from app.parsing.taxonomy import normalize_skill_name
from app.rag.models import LexicalScoreBreakdown

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "did", "do", "does", "doing", "don't", "down", "during", "each", "few", "for",
    "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers",
    "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is",
    "it", "its", "itself", "me", "more", "most", "my", "myself", "no", "nor",
    "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our",
    "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so",
    "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "we", "were", "what", "when", "where",
    "which", "while", "who", "whom", "why", "with", "would", "you", "your", "yours",
}


def tokenize(text: str, remove_stopwords: bool = True) -> list[str]:
    """Tokenize string into alphanumeric words, preserving meaningful tokens."""
    tokens = re.findall(r"\b[a-zA-Z0-9_+#.-]+\b", text.lower())
    clean_tokens = [re.sub(r"^[.\-]+|[.\-]+$", "", t) for t in tokens if t.strip()]
    if remove_stopwords:
        return [t for t in clean_tokens if t and t not in STOP_WORDS and len(t) > 1]
    return [t for t in clean_tokens if t]


def generate_ngrams(tokens: list[str], n: int) -> list[str]:
    """Generate token-level n-grams."""
    if len(tokens) < n:
        return []
    return [" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def compute_bm25_score(
    query_tokens: list[str],
    doc_tokens: list[str],
    corpus_token_docs: list[list[str]],
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """Compute BM25 relevance score for a document relative to query and corpus."""
    if not query_tokens or not doc_tokens:
        return 0.0

    n_docs = len(corpus_token_docs) or 1
    avgdl = sum(len(d) for d in corpus_token_docs) / n_docs if corpus_token_docs else len(doc_tokens)
    if avgdl <= 0:
        avgdl = 1.0

    doc_freqs = Counter(doc_tokens)
    doc_len = len(doc_tokens)

    score = 0.0
    for q_token in set(query_tokens):
        # Document frequency in corpus
        n_q = sum(1 for d in corpus_token_docs if q_token in d)
        # Standard BM25 IDF
        idf = math.log((n_docs - n_q + 0.5) / (n_q + 0.5) + 1.0)
        if idf < 0:
            idf = 0.0

        f = doc_freqs.get(q_token, 0)
        numerator = f * (k1 + 1.0)
        denominator = f + k1 * (1.0 - b + b * (doc_len / avgdl))
        score += idf * (numerator / denominator if denominator > 0 else 0.0)

    # Normalize score approximately to [0.0, 1.0]
    max_possible_score = sum(math.log(n_docs + 1.0) * (k1 + 1.0) for _ in set(query_tokens)) or 1.0
    normalized_score = min(1.0, max(0.0, score / max_possible_score))
    return round(normalized_score, 4)


def compute_exact_keyword_score(target_terms: list[str], text: str) -> tuple[float, list[str]]:
    """Calculate exact keyword match score based on presence of target terms in text."""
    if not target_terms:
        return 0.0, []

    matched = []
    lowered_text = text.lower()
    for term in target_terms:
        clean_term = term.strip().lower()
        if not clean_term:
            continue
        pattern = rf"(?<![a-zA-Z0-9_+#]){re.escape(clean_term)}(?![a-zA-Z0-9_+#])"
        if re.search(pattern, lowered_text):
            matched.append(term)

    score = len(matched) / len(target_terms) if target_terms else 0.0
    return round(score, 4), matched


def compute_normalized_keyword_score(
    normalized_query_terms: list[str],
    doc_text: str,
) -> tuple[float, list[str]]:
    """Calculate normalized keyword match score using canonical tech taxonomy slugs."""
    if not normalized_query_terms:
        return 0.0, []

    # Tokenize and normalize doc tokens and bigrams
    doc_words = tokenize(doc_text, remove_stopwords=False)
    doc_bigrams = generate_ngrams(doc_words, 2)
    doc_all_terms = doc_words + doc_bigrams
    doc_canonicals = {normalize_skill_name(t) for t in doc_all_terms}

    matched = []
    for term in normalized_query_terms:
        canonical_target = normalize_skill_name(term)
        if canonical_target in doc_canonicals or any(canonical_target in dc for dc in doc_canonicals):
            matched.append(term)

    score = len(matched) / len(normalized_query_terms) if normalized_query_terms else 0.0
    return round(score, 4), matched


def compute_ngram_similarity(query_text: str, doc_text: str) -> float:
    """Compute character and word n-gram Jaccard similarity."""
    q_tokens = tokenize(query_text, remove_stopwords=True)
    d_tokens = tokenize(doc_text, remove_stopwords=True)

    if not q_tokens or not d_tokens:
        return 0.0

    q_unigrams = set(q_tokens)
    d_unigrams = set(d_tokens)
    unigram_jaccard = len(q_unigrams & d_unigrams) / (len(q_unigrams | d_unigrams) or 1)

    q_bigrams = set(generate_ngrams(q_tokens, 2))
    d_bigrams = set(generate_ngrams(d_tokens, 2))
    bigram_jaccard = (len(q_bigrams & d_bigrams) / (len(q_bigrams | d_bigrams) or 1)) if q_bigrams else unigram_jaccard

    combined = 0.6 * unigram_jaccard + 0.4 * bigram_jaccard
    return round(min(1.0, max(0.0, combined)), 4)


def evaluate_lexical_match(
    query_text: str,
    target_terms: list[str],
    normalized_terms: list[str],
    doc_text: str,
    corpus_token_docs: list[list[str]] | None = None,
) -> tuple[float, LexicalScoreBreakdown, list[str]]:
    """Run full lexical evaluation combining BM25, exact, normalized, and n-gram signals."""
    q_tokens = tokenize(query_text)
    d_tokens = tokenize(doc_text)
    corpus = corpus_token_docs or [d_tokens]

    bm25 = compute_bm25_score(q_tokens, d_tokens, corpus)
    exact_score, exact_matched = compute_exact_keyword_score(target_terms or q_tokens, doc_text)
    norm_score, norm_matched = compute_normalized_keyword_score(normalized_terms or target_terms, doc_text)
    ngram_score = compute_ngram_similarity(query_text, doc_text)

    # Weighted lexical combination
    total = (
        0.35 * bm25
        + 0.35 * exact_score
        + 0.20 * norm_score
        + 0.10 * ngram_score
    )
    total = round(min(1.0, max(0.0, total)), 4)

    all_matched = sorted(set(exact_matched + norm_matched))

    breakdown = LexicalScoreBreakdown(
        bm25_score=bm25,
        exact_match_score=exact_score,
        normalized_keyword_score=norm_score,
        ngram_score=ngram_score,
        total=total,
    )
    return total, breakdown, all_matched
