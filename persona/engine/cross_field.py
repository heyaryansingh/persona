"""Cross-field mechanism translation (BUILD_PLAN 3.6).

Given two claims from different subfields that describe the SAME underlying
mechanism in different vocabulary, try to recognize the alignment.

HONEST LIMITATION: this is a purely LEXICAL (Jaccard-over-tokens) baseline.
It has no notion of synonymy ("synapse" vs "synaptic connection" vs
"neuronal junction" score 0 unless they literally share a token), so it will
miss real cross-field translations that use disjoint vocabulary for the same
concept. H3.6 in BUILD_PLAN ("beats an embedding baseline") is NOT validated
here -- there is no embedding baseline in this module to beat. Real
cross-field translation needs embeddings or an LLM to bridge vocabulary gaps;
this module is a cheap stdlib-only stand-in until that's built and evaluated.
"""
from __future__ import annotations

import re

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


def similarity(a_text: str, b_text: str) -> float:
    """Jaccard similarity over mechanism_tokens; 0..1."""
    a, b = mechanism_tokens(a_text), mechanism_tokens(b_text)
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def align(claims_a: list, claims_b: list, threshold: float = 0.2) -> list:
    """Find cross-field claim pairs whose lexical mechanism overlap is
    >= threshold. Excludes exact-equal strings (trivial, not "cross-field").
    Returns list of dict(a, b, score) sorted by score desc.
    """
    out = []
    for a in claims_a:
        for b in claims_b:
            if a == b:
                continue
            score = similarity(a, b)
            if score >= threshold:
                out.append({"a": a, "b": b, "score": score})
    out.sort(key=lambda d: d["score"], reverse=True)
    return out
