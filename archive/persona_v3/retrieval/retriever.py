"""Hybrid retriever: dense (MiniLM) + lexical (TF-IDF) fused with Reciprocal Rank Fusion.

RRF (Cormack 2009) is the fusion the tech sweep recommends — robust, parameter-light.
Swap Embedder's model for a biomedical encoder (MedCPT/SPECTER2) and the numpy index for
FAISS to scale; the Retriever API stays the same.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np

_DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class Embedder:
    def __init__(self, model_name: str = _DEFAULT_MODEL):
        self.name = model_name
        self._m = None

    def _model(self):
        if self._m is None:
            from sentence_transformers import SentenceTransformer
            self._m = SentenceTransformer(self.name)
        return self._m

    def encode(self, texts) -> np.ndarray:
        v = self._model().encode(list(texts), normalize_embeddings=True,
                                 show_progress_bar=False)
        return np.asarray(v, dtype=np.float32)


class Retriever:
    """Index a set of documents; retrieve top-k by dense / lexical / hybrid (RRF)."""

    def __init__(self, embedder: Embedder | None = None, rrf_k: int = 60):
        self.embedder = embedder or Embedder()
        self.rrf_k = rrf_k
        self.docs: list = []
        self._emb = None
        self._tfidf = None
        self._tfmat = None

    def index(self, docs) -> "Retriever":
        self.docs = list(docs)
        texts = [f"{getattr(d, 'title', '')}. {getattr(d, 'text', '')}".strip() for d in self.docs]
        if not texts:
            return self
        self._emb = self.embedder.encode(texts)
        from sklearn.feature_extraction.text import TfidfVectorizer
        self._tfidf = TfidfVectorizer(stop_words="english", max_features=20000)
        self._tfmat = self._tfidf.fit_transform(texts)
        return self

    def _dense_order(self, query: str) -> list:
        q = self.embedder.encode([query])[0]
        sims = self._emb @ q
        return list(np.argsort(-sims))

    def _lexical_order(self, query: str) -> list:
        qv = self._tfidf.transform([query])
        sims = (self._tfmat @ qv.T).toarray().ravel()
        return list(np.argsort(-sims))

    def retrieve(self, query: str, k: int = 10, mode: str = "hybrid") -> list:
        if not self.docs:
            return []
        if mode == "dense":
            idx = self._dense_order(query)[:k]
        elif mode == "lexical":
            idx = self._lexical_order(query)[:k]
        else:                                  # RRF fusion of dense + lexical
            rrf = defaultdict(float)
            for r, i in enumerate(self._dense_order(query)):
                rrf[int(i)] += 1.0 / (self.rrf_k + r)
            for r, i in enumerate(self._lexical_order(query)):
                rrf[int(i)] += 1.0 / (self.rrf_k + r)
            idx = [i for i, _ in sorted(rrf.items(), key=lambda x: -x[1])[:k]]
        return [self.docs[int(i)] for i in idx]
