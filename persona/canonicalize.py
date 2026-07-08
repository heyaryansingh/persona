"""Entity canonicalization (v2) — the fix for the convergence tail.

Claude phrases the same entity differently across papers ("microglia" vs "microglial
activation" vs "activated microglia"), so string-keyed claims never converge. This clusters
entity strings by embedding similarity into a canonical form, so equivalent claims from
different papers land on the SAME claim_key and converge — while DIRECTION is still handled
separately by the membrane, so opposing claims about the same entity pair correctly become a
contradiction rather than being merged away.

Uses the retrieval Embedder (MiniLM); falls back to identity (no clustering) without it.
"""
from __future__ import annotations

import re

import numpy as np


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


class EntityCanonicalizer:
    def __init__(self, embedder=None, threshold: float = 0.72):
        self.threshold = threshold
        self._embedder = embedder
        self._canon: list[str] = []          # canonical entity strings (first-seen wins)
        self._emb = None                     # np.ndarray of their embeddings
        self._cache: dict[str, str] = {}     # raw -> canonical

    def _get_embedder(self):
        if self._embedder is None:
            try:
                from .retrieval import Embedder
                self._embedder = Embedder()
            except Exception:
                self._embedder = False        # unavailable -> identity fallback
        return self._embedder or None

    def canon(self, entity: str) -> str:
        raw = _norm(entity)
        if not raw:
            return entity
        if raw in self._cache:
            return self._cache[raw]
        emb = self._get_embedder()
        if emb is None:
            self._cache[raw] = raw
            return raw
        v = emb.encode([raw])[0]
        if self._canon:
            sims = self._emb @ v
            j = int(np.argmax(sims))
            if sims[j] >= self.threshold:
                self._cache[raw] = self._canon[j]
                return self._canon[j]
        # new canonical entity
        self._canon.append(raw)
        self._emb = v[None, :] if self._emb is None else np.vstack([self._emb, v])
        self._cache[raw] = raw
        return raw
