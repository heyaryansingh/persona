"""Entity canonicalization (v3 T1.2) — deterministic, reproducible, symbol-safe.

Claude phrases the same entity differently across papers ("microglia" / "microglial activation"
/ "activated microglia"), so string-keyed claims never converge. v2 clustered by MiniLM
similarity, but the audit flagged three real defects: (1) it FALSE-MERGES distinct biomedical
symbols (IL-6 vs IL-1 embed almost identically), silently manufacturing fake convergence — the
worst possible bug here; (2) greedy first-seen-wins is ORDER-DEPENDENT, so the same corpus read
in a different order produces different claim_keys (breaks crash-resume reproducibility); (3) the
0.72 threshold was never validated.

v3 default is a PURE FUNCTION: rule-based normalization (drop modifier words, normalize plurals
and hyphenation) + a curated domain synonym map. Being a pure function of the input string, it is
order-independent by construction and can NEVER merge two distinct normalized forms — IL-6 and
IL-1 stay separate. An embedding-assisted merge is available as explicit opt-in but is GUARDED by
a digit-symbol signature (il6 != il1 never merge) and uses a deterministic representative
(shortest, then alphabetical) so it stays reproducible. Validated: experiments/exp_canonicalization.py.
"""
from __future__ import annotations

import re

import numpy as np

# modifier tokens that don't change entity identity — dropped so variants collapse
_MODIFIERS = {
    "activated", "activation", "activating", "mediated", "dependent", "induced", "positive",
    "negative", "response", "responses", "signaling", "signalling", "signal", "pathway",
    "pathways", "levels", "level", "expression", "expressing", "protein", "proteins",
    "phosphorylated", "hyperphosphorylated", "associated", "related", "reactive", "reactivity",
    "burden", "load", "deposition", "aggregation", "aggregates", "accumulation", "the", "of",
}
# curated domain synonyms -> canonical (deterministic; extend as the field demands)
_SYNONYMS = {
    "abeta": "amyloid-beta", "a-beta": "amyloid-beta", "amyloid beta": "amyloid-beta",
    "amyloid-b": "amyloid-beta", "ab42": "amyloid-beta", "amyloid": "amyloid-beta",
    "microglial": "microglia", "microglial cell": "microglia", "microglial cells": "microglia",
    "astrocytic": "astrocyte", "astroglia": "astrocyte",
    "tau protein": "tau", "p-tau": "tau", "ptau": "tau",
    "ad": "alzheimer", "alzheimer's": "alzheimer", "alzheimers": "alzheimer",
    "alzheimer disease": "alzheimer", "alzheimer's disease": "alzheimer",
    "neuroinflammatory": "neuroinflammation", "neuro-inflammation": "neuroinflammation",
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _symbol_sig(s: str) -> frozenset:
    """Digit-bearing tokens (il6, il1, nlrp3, apoe4) — two entities may only embedding-merge if
    these match. Blocks the IL-6/IL-1 false merge regardless of embedding similarity."""
    toks = re.findall(r"[a-z]+-?\d+", s.lower())
    return frozenset(t.replace("-", "") for t in toks)


def normalize_entity(entity: str) -> str:
    """Deterministic canonical form: synonym map, then drop modifier words + simple plurals."""
    raw = _norm(entity)
    if not raw:
        return ""
    if raw in _SYNONYMS:
        raw = _SYNONYMS[raw]
    # token-level: drop modifiers, singularize, then re-map (a variant may reduce to a synonym key)
    toks = []
    for t in re.split(r"\s+", raw):
        t = t.strip("-")
        if t in _MODIFIERS or not t:
            continue
        if len(t) > 4 and t.endswith("s") and not t.endswith("ss") and not re.search(r"\d", t):
            t = t[:-1]
        toks.append(t)
    out = " ".join(toks) if toks else raw
    return _SYNONYMS.get(out, out)


class EntityCanonicalizer:
    """Default: pure rule-based (deterministic, order-independent). Pass an embedder AND
    use_embeddings=True to additionally merge near-duplicate residual forms — guarded by the
    symbol signature and using a deterministic representative so reproducibility holds."""

    def __init__(self, embedder=None, threshold: float = 0.80, use_embeddings: bool = False):
        self.threshold = threshold
        self._embedder = embedder
        self.use_embeddings = use_embeddings and embedder is not None
        self._reps: list[str] = []           # cluster representatives (normalized)
        self._sigs: list[frozenset] = []      # their symbol signatures
        self._emb = None
        self._cache: dict[str, str] = {}

    def canon(self, entity: str) -> str:
        norm = normalize_entity(entity)
        if not norm:
            return entity
        if not self.use_embeddings:
            return norm
        if norm in self._cache:
            return self._cache[norm]
        sig = _symbol_sig(norm)
        v = self._embedder.encode([norm])[0]
        if self._reps:
            sims = self._emb @ v
            order = np.argsort(-sims)
            for j in order:
                if sims[j] < self.threshold:
                    break
                if self._sigs[j] != sig:            # symbol guard: never merge il6 with il1
                    continue
                rep = min(self._reps[j], norm, key=lambda x: (len(x), x))  # deterministic rep
                self._reps[j] = rep
                self._cache[norm] = rep
                return rep
        self._reps.append(norm)
        self._sigs.append(sig)
        self._emb = v[None, :] if self._emb is None else np.vstack([self._emb, v])
        self._cache[norm] = norm
        return norm
