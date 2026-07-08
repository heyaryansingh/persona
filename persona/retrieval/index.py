"""Persistent vector index (v3 T2.2) — the corpus accumulates instead of being re-embedded.

Audit #8: `Researcher.retrieve` re-embedded <=40 fresh docs every call; nothing accumulated, so
"reading a large corpus" wasn't real. This is an on-disk dense index keyed by doc_id: each new
doc is embedded ONCE and appended; search runs over the whole accumulated corpus and survives
restarts. Dense-only (MiniLM) by default; a hybrid rerank can layer on via Retriever.

ponytail: numpy .npy matrix + JSON sidecar, rewritten on append — fine for the thousands-of-
abstracts scale here. Swap to FAISS/memmap + append-only when the corpus reaches ~1e5 docs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np


class PersistentIndex:
    def __init__(self, root: str | Path, embedder=None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._embedder = embedder
        self._embedder_tried = embedder is not None
        self.ids: list = []
        self.meta: dict = {}
        self._emb: Optional[np.ndarray] = None
        self._load()

    # ------------------------------------------------------------- persistence
    @property
    def _emb_path(self):
        return self.root / "emb.npy"

    @property
    def _meta_path(self):
        return self.root / "meta.json"

    def _load(self):
        if self._meta_path.exists():
            d = json.loads(self._meta_path.read_text(encoding="utf-8"))
            self.ids = d["ids"]
            self.meta = d["meta"]
        if self._emb_path.exists():
            self._emb = np.load(self._emb_path)

    def _save(self):
        self._meta_path.write_text(json.dumps({"ids": self.ids, "meta": self.meta}),
                                   encoding="utf-8")
        if self._emb is not None:
            np.save(self._emb_path, self._emb)

    # ------------------------------------------------------------- embedder
    def _get_embedder(self):
        if self._embedder is None and not self._embedder_tried:
            self._embedder_tried = True
            try:
                from .retriever import Embedder
                self._embedder = Embedder()
            except Exception:
                self._embedder = None
        return self._embedder

    # ------------------------------------------------------------- api
    def add(self, docs) -> int:
        """Embed + append only docs not already indexed. Returns the number newly added."""
        new = [d for d in docs if getattr(d, "doc_id", None) and d.doc_id not in self.meta]
        if not new:
            return 0
        emb = self._get_embedder()
        if emb is None:
            return 0
        texts = [f"{getattr(d, 'title', '')}. {getattr(d, 'text', '')}".strip() for d in new]
        vecs = emb.encode(texts).astype(np.float32)
        self._emb = vecs if self._emb is None else np.vstack([self._emb, vecs])
        for d in new:
            self.ids.append(d.doc_id)
            self.meta[d.doc_id] = {"title": getattr(d, "title", ""), "group": getattr(d, "group", None),
                                   "year": getattr(d, "year", None), "url": getattr(d, "url", None)}
        self._save()
        return len(new)

    def search(self, query: str, k: int = 10) -> list:
        """Top-k over the WHOLE accumulated corpus. [{doc_id,title,group,year,url,score}]."""
        if self._emb is None or not self.ids:
            return []
        emb = self._get_embedder()
        if emb is None:
            return []
        q = emb.encode([query])[0]
        sims = self._emb @ q
        order = np.argsort(-sims)[:k]
        out = []
        for i in order:
            did = self.ids[int(i)]
            out.append({"doc_id": did, "score": float(sims[int(i)]), **self.meta.get(did, {})})
        return out

    def size(self) -> int:
        return len(self.ids)
