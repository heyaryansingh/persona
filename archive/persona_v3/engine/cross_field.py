"""Cross-field mechanism translation (BUILD_PLAN 3.6).

Given two claims from different subfields that describe the SAME underlying mechanism in
different vocabulary, recognize the alignment.

v3 T4: the lexical Jaccard baseline (below) cannot bridge disjoint vocabulary ("synaptic pruning
by microglia" vs "neuronal connection elimination by immune cells" -> Jaccard 0). `similarity()`
now uses EMBEDDING cosine (MiniLM via the retrieval Embedder) when available, and falls back to
Jaccard when no embedder is installed. Validated in experiments/exp_cross_field.py (embedding
recovers disjoint-vocab pairs Jaccard scores ~0).
"""
from __future__ import annotations

import re

import numpy as np

_STOP = {
    "the", "a", "an", "of", "and", "in", "to", "is", "are", "was", "were",
    "for", "on", "with", "by", "at", "as", "that", "this", "it", "its",
    "be", "been", "being", "or", "but", "not", "from", "into", "than",
    "via", "these", "those", "such", "can", "may", "also",
}

_TOKEN_RE = re.compile(r"[a-z0-9-]{3,}")


def mechanism_tokens(text: str) -> set:
    """Lowercase word tokens (regex [a-z0-9-]{3,}) minus stopwords."""
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP}


def jaccard_similarity(a_text: str, b_text: str) -> float:
    """Lexical Jaccard over mechanism_tokens; 0..1. The fallback when no embedder is present."""
    a, b = mechanism_tokens(a_text), mechanism_tokens(b_text)
    union = a | b
    return len(a & b) / len(union) if union else 0.0


_EMBEDDER = None
_EMBEDDER_TRIED = False


def _get_embedder(embedder=None):
    global _EMBEDDER, _EMBEDDER_TRIED
    if embedder is not None:
        return embedder
    if not _EMBEDDER_TRIED:
        _EMBEDDER_TRIED = True
        try:
            from ..retrieval import Embedder
            _EMBEDDER = Embedder()
        except Exception:
            _EMBEDDER = None
    return _EMBEDDER


def similarity(a_text: str, b_text: str, embedder=None) -> float:
    """EMBEDDING cosine similarity (MiniLM) when an embedder is available, else lexical Jaccard.
    Embeddings bridge disjoint vocabulary for the same mechanism; Jaccard cannot."""
    emb = _get_embedder(embedder)
    if emb is None:
        return jaccard_similarity(a_text, b_text)
    v = emb.encode([a_text, b_text])
    cos = float(np.dot(v[0], v[1]))       # Embedder normalizes -> dot == cosine
    return max(0.0, cos)                    # clamp (embeddings can be slightly negative)


def align(claims_a: list, claims_b: list, threshold: float = 0.2, embedder=None) -> list:
    """Cross-field claim pairs with mechanism similarity >= threshold (embedding by default).
    Excludes exact-equal strings (trivial). Returns dict(a, b, score) sorted by score desc."""
    out = []
    for a in claims_a:
        for b in claims_b:
            if a == b:
                continue
            score = similarity(a, b, embedder=embedder)
            if score >= threshold:
                out.append({"a": a, "b": b, "score": score})
    out.sort(key=lambda d: d["score"], reverse=True)
    return out
