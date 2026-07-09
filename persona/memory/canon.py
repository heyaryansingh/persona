"""Entity canonicalization (v4) — domain-general, so the SAME concept from different papers
converges to ONE node (the thing that makes beliefs light up at scale).

Rule-normalize the string, then cluster by embedding cosine (bge-small). First-seen name is the
stable canonical for a cluster (keeps claim_ids stable across a run). GUARDED against the v3
failure mode: two names whose digit-bearing symbol tokens differ (IL-6 vs IL-1, NLRP3 vs NLRP1)
NEVER merge, however similar their embeddings — that silent false-merge is the worst bug here.

Persisted to .persona/canon.{json,npy} so canonicalization survives restarts.
"""
from __future__ import annotations

import json
import re
import threading

import numpy as np

from .. import config
from . import embed

_THRESHOLD = float(__import__("os").environ.get("PERSONA_CANON_THRESHOLD", "0.86"))


def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .,:;")


def _symbol_sig(s: str) -> frozenset:
    """Digit-bearing tokens (il6, il1, nlrp3, apoe4). Differing sigs block a merge."""
    return frozenset(t.replace("-", "") for t in re.findall(r"[a-z]+-?\d+", s.lower()))


class Canonicalizer:
    def __init__(self, threshold: float = None):
        self.threshold = threshold if threshold is not None else _THRESHOLD
        self._lock = threading.Lock()
        self.canon_names: list[str] = []          # canonical form per cluster (first-seen)
        self.sigs: list[frozenset] = []
        self.emb: np.ndarray | None = None
        self.cache: dict[str, str] = {}           # normalized-string -> canonical
        self._load()

    def _load(self):
        j = config.OPS_DIR / "canon.json"
        e = config.OPS_DIR / "canon.npy"
        if j.exists():
            d = json.loads(j.read_text(encoding="utf-8"))
            self.canon_names = d["names"]
            self.sigs = [frozenset(x) for x in d["sigs"]]
            self.cache = d.get("cache", {})
        if e.exists():
            self.emb = np.load(e)

    def _save(self):
        (config.OPS_DIR / "canon.json").write_text(json.dumps(
            {"names": self.canon_names, "sigs": [sorted(s) for s in self.sigs],
             "cache": self.cache}), encoding="utf-8")
        if self.emb is not None:
            np.save(config.OPS_DIR / "canon.npy", self.emb)

    def canon(self, name: str) -> str:
        norm = _norm(name)
        if not norm:
            return name.strip()
        with self._lock:
            if norm in self.cache:
                return self.cache[norm]
            sig = _symbol_sig(norm)
            v = embed.encode([norm])[0]
            chosen = norm
            if self.emb is not None and len(self.canon_names):
                sims = self.emb @ v
                order = np.argsort(-sims)
                for j in order:
                    if sims[j] < self.threshold:
                        break
                    if self.sigs[j] != sig:                 # symbol guard: il6 != il1
                        continue
                    chosen = self.canon_names[j]             # merge into existing cluster
                    break
            if chosen == norm:                              # new cluster
                self.canon_names.append(norm)
                self.sigs.append(sig)
                self.emb = v[None, :] if self.emb is None else np.vstack([self.emb, v])
            self.cache[norm] = chosen
            self._save()
            return chosen
