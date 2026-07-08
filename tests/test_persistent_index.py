"""T2.2: the persistent vector index accumulates across restarts and dedups by doc_id.
Uses a deterministic fake embedder (no model download). Run: python tests/test_persistent_index.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np                                               # noqa: E402
from persona.retrieval.index import PersistentIndex             # noqa: E402
from persona.ingest.base import Document                        # noqa: E402

_VOCAB = ["microglia", "tau", "amyloid", "neuroinflammation", "apoe", "synapse", "il", "nlrp"]


class FakeEmbedder:
    """Deterministic bag-of-vocab embedding — same text -> same vector, L2-normalized."""
    def encode(self, texts):
        out = []
        for t in texts:
            v = np.array([t.lower().count(w) for w in _VOCAB], dtype=np.float32)
            n = np.linalg.norm(v)
            out.append(v / n if n else v + 1e-6)
        return np.asarray(out, dtype=np.float32)


def _doc(i, text):
    return Document(doc_id=f"MED:{i}", title="t", text=text, source="s", group=f"lab{i}")


def test_add_accumulates_and_dedups():
    with tempfile.TemporaryDirectory() as d:
        idx = PersistentIndex(d, embedder=FakeEmbedder())
        assert idx.add([_doc(1, "microglia tau"), _doc(2, "amyloid apoe")]) == 2
        assert idx.add([_doc(2, "amyloid apoe"), _doc(3, "synapse")]) == 1   # doc 2 already in
        assert idx.size() == 3


def test_persists_across_restart():
    with tempfile.TemporaryDirectory() as d:
        idx = PersistentIndex(d, embedder=FakeEmbedder())
        idx.add([_doc(1, "microglia neuroinflammation"), _doc(2, "amyloid")])
        # new instance, same dir -> should load the accumulated corpus
        idx2 = PersistentIndex(d, embedder=FakeEmbedder())
        assert idx2.size() == 2
        assert idx2.add([_doc(1, "microglia neuroinflammation")]) == 0   # still deduped after reload


def test_search_returns_most_similar():
    with tempfile.TemporaryDirectory() as d:
        idx = PersistentIndex(d, embedder=FakeEmbedder())
        idx.add([_doc(1, "microglia microglia neuroinflammation"), _doc(2, "amyloid apoe apoe"),
                 _doc(3, "tau synapse")])
        hits = idx.search("amyloid apoe", k=2)
        assert hits and hits[0]["doc_id"] == "MED:2", hits
        assert "score" in hits[0] and "group" in hits[0]


def test_no_embedder_is_graceful():
    with tempfile.TemporaryDirectory() as d:
        idx = PersistentIndex(d, embedder=None)
        idx._embedder_tried = True          # simulate "embedder unavailable"
        assert idx.add([_doc(1, "x")]) == 0
        assert idx.search("x") == []


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} persistent-index tests passed.")
