"""Cross-field mechanism translation tests (T4: embedding similarity + Jaccard fallback).
Uses a fake embedder so the suite never loads MiniLM. Run: python tests/test_cross_field.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np                                                        # noqa: E402
from persona.engine.cross_field import (mechanism_tokens, similarity,     # noqa: E402
                                         jaccard_similarity, align)


class FakeEmbedder:
    """'synapse'/'connection'/'prune'/'eliminate' share an axis so a disjoint-vocab, same-
    mechanism pair scores high; off-topic words load other axes."""
    _AX = {"synapse": 0, "connection": 0, "neuron": 0, "prune": 0, "eliminate": 0, "immune": 0,
           "glucose": 1, "insulin": 1, "pancreas": 1, "ocean": 2, "salinity": 2}

    def encode(self, texts):
        out = []
        for t in texts:
            v = np.zeros(3, dtype=np.float32)
            for w, ax in self._AX.items():
                if w in t.lower():
                    v[ax] += 1.0
            n = np.linalg.norm(v)
            out.append(v / n if n else v)
        return np.asarray(out, dtype=np.float32)


def test_mechanism_tokens_strips_stopwords_and_short_words():
    toks = mechanism_tokens("The activation of a cell is in the synapse")
    assert "the" not in toks and "of" not in toks and "is" not in toks
    assert "activation" in toks and "synapse" in toks and "cell" in toks


def test_jaccard_identity_and_disjoint():
    assert jaccard_similarity("microglia drives synapse loss", "microglia drives synapse loss") == 1.0
    assert jaccard_similarity("microglia drives synapse", "unrelated ocean salinity trends") == 0.0


def test_embedding_bridges_disjoint_vocabulary():
    e = FakeEmbedder()
    # same mechanism, DISJOINT vocabulary -> Jaccard 0 but embedding high
    assert jaccard_similarity("prune synapse", "eliminate connection") == 0.0
    assert similarity("prune synapse", "eliminate connection", embedder=e) > 0.9
    # off-topic -> low
    assert similarity("prune synapse", "insulin glucose pancreas", embedder=e) < 0.1


def test_align_uses_embedding_and_excludes_exact():
    e = FakeEmbedder()
    pairs = align(["prune synapse"],
                  ["eliminate connection", "ocean salinity"], threshold=0.5, embedder=e)
    assert len(pairs) == 1 and pairs[0]["b"] == "eliminate connection"
    assert align(["x prune"], ["x prune"], threshold=0.0, embedder=e) == []   # exact-equal excluded


def test_falls_back_to_jaccard_without_embedder():
    import persona.engine.cross_field as cf
    cf._EMBEDDER = None
    cf._EMBEDDER_TRIED = True                      # simulate "no embedder installed"
    assert similarity("tau neuron loss", "tau neuron loss") == 1.0        # jaccard identity
    assert similarity("tau neuron", "ocean salinity") == 0.0               # jaccard disjoint


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} cross-field tests passed.")
