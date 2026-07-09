"""Per-persona vector index (v5 P5) — numpy + bge-small (fastembed), no server, no extra dep.

Episodic/semantic retrieval layer over synthesis notes (and, later, claim quotes): "what do I
know about X". Simple append-only .npy + JSON sidecar; rewritten on add — fine for the note counts
here (hundreds–thousands). Swap to sqlite-vec/FAISS if it ever grows past ~1e5.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class VectorIndex:
    def __init__(self, path):
        self.dir = Path(path).parent / "vectors"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.emb_path = self.dir / "emb.npy"
        self.meta_path = self.dir / "meta.json"
        self.ids: list = []
        self.meta: dict = {}
        self._emb = None
        if self.meta_path.exists():
            d = json.loads(self.meta_path.read_text(encoding="utf-8"))
            self.ids, self.meta = d["ids"], d["meta"]
        if self.emb_path.exists():
            self._emb = np.load(self.emb_path)

    def _encode(self, texts):
        from .embed import encode
        return encode(texts)

    def _save(self):
        self.meta_path.write_text(json.dumps({"ids": self.ids, "meta": self.meta}), encoding="utf-8")
        if self._emb is not None:
            np.save(self.emb_path, self._emb)

    def upsert(self, key: str, text: str, meta: dict = None) -> None:
        try:
            v = self._encode([text])[0].astype(np.float32)
        except Exception:
            return
        if key in self.meta:                              # replace existing row
            i = self.ids.index(key)
            self._emb[i] = v
        else:
            self.ids.append(key)
            self._emb = v[None, :] if self._emb is None else np.vstack([self._emb, v])
        self.meta[key] = meta or {}
        self._save()

    def search(self, query: str, k: int = 6) -> list:
        if self._emb is None or not self.ids:
            return []
        try:
            q = self._encode([query])[0]
        except Exception:
            return []
        sims = self._emb @ q
        order = np.argsort(-sims)[:k]
        return [{"key": self.ids[int(i)], "score": float(sims[int(i)]), **self.meta.get(self.ids[int(i)], {})}
                for i in order]

    def size(self) -> int:
        return len(self.ids)
