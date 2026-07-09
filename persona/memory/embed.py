"""Local embeddings (v4) — bge-small via fastembed. Free, fast, CPU, no API cost, so the always-on
daemon can embed continuously. Used for entity canonicalization (convergence) and, later, retrieval.
"""
from __future__ import annotations

import numpy as np

_MODEL_NAME = "BAAI/bge-small-en-v1.5"      # 384-dim, strong small retrieval model
_model = None


def _get_model():
    global _model
    if _model is None:
        from fastembed import TextEmbedding
        _model = TextEmbedding(_MODEL_NAME)
    return _model


def encode(texts) -> np.ndarray:
    """L2-normalized embeddings (cosine == dot)."""
    vecs = np.array(list(_get_model().embed(list(texts))), dtype=np.float32)
    if vecs.ndim == 1:
        vecs = vecs[None, :]
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms
