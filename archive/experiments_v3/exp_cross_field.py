"""exp_cross_field (T4) — does embedding similarity bridge disjoint vocabulary where Jaccard can't?

BUILD_PLAN 3.6 wants cross-field mechanism alignment: two subfields describing the SAME mechanism
in DIFFERENT words. Jaccard scores such pairs ~0 (no shared tokens). Claim: MiniLM cosine
separates same-mechanism-different-vocab pairs from unrelated pairs where Jaccard collapses.

Labeled pairs (synonymous = same mechanism, deliberately disjoint vocabulary; unrelated = off-topic).
Report mean score + separation for embedding vs Jaccard. Loads MiniLM (manual experiment).
Run: python experiments/exp_cross_field.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from persona.engine.cross_field import similarity, jaccard_similarity   # noqa: E402

SYNONYMOUS = [
    ("microglia prune synapses", "brain immune cells eliminate neuronal connections"),
    ("amyloid-beta aggregates into plaques", "misfolded peptides accumulate as extracellular deposits"),
    ("tau spreads between neurons", "pathological protein propagates trans-synaptically across cells"),
    ("neuroinflammation drives cognitive decline", "brain immune activation worsens memory performance"),
    ("APOE4 raises Alzheimer risk", "the e4 lipoprotein variant increases dementia susceptibility"),
]
UNRELATED = [
    ("microglia prune synapses", "insulin regulates blood glucose in the pancreas"),
    ("tau spreads between neurons", "quarterly revenue fell on weak demand"),
    ("amyloid-beta aggregates into plaques", "the bridge was repainted last summer"),
    ("neuroinflammation drives cognitive decline", "photosynthesis converts light to sugar"),
    ("APOE4 raises Alzheimer risk", "the train departs at nine"),
]


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def main():
    try:
        from persona.retrieval import Embedder
        emb = Embedder()
        emb.encode(["warmup"])
    except Exception as e:
        print(f"SKIP: embedder unavailable ({e})")
        return
    es = [similarity(a, b, embedder=emb) for a, b in SYNONYMOUS]
    eu = [similarity(a, b, embedder=emb) for a, b in UNRELATED]
    js = [jaccard_similarity(a, b) for a, b in SYNONYMOUS]
    ju = [jaccard_similarity(a, b) for a, b in UNRELATED]
    print("                    synonymous(mean)   unrelated(mean)   separation")
    print(f"  embedding cosine   {_mean(es):.3f}             {_mean(eu):.3f}            {_mean(es)-_mean(eu):+.3f}")
    print(f"  jaccard (lexical)  {_mean(js):.3f}             {_mean(ju):.3f}            {_mean(js)-_mean(ju):+.3f}")
    # a midpoint threshold between the hardest synonymous and the strongest unrelated
    best = (min(es) + max(eu)) / 2
    correct = sum(s > best for s in es) + sum(u <= best for u in eu)
    print(f"\n  embedding separates {correct}/{len(es)+len(eu)} labeled pairs at thr={best:.2f}")
    print(f"  jaccard scores synonymous pairs ~{_mean(js):.2f} (disjoint vocabulary -> can't bridge)")
    verdict = "PASS: embedding bridges disjoint vocabulary; Jaccard does not" \
        if (_mean(es) - _mean(eu)) > (_mean(js) - _mean(ju)) + 0.1 else "INCONCLUSIVE"
    print(f"\nVERDICT: {verdict}")


if __name__ == "__main__":
    main()
