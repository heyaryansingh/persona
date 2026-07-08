"""T1.2: canonicalization is deterministic, order-independent, and symbol-safe.
Run: python tests/test_canonicalize.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.canonicalize import EntityCanonicalizer, normalize_entity   # noqa: E402


def test_variants_collapse():
    for a, b in [("microglial activation", "microglia"), ("hyperphosphorylated tau", "tau"),
                 ("abeta", "amyloid beta"), ("alzheimer's disease", "AD"),
                 ("neuroinflammatory response", "neuroinflammation")]:
        assert normalize_entity(a) == normalize_entity(b), (a, b, normalize_entity(a), normalize_entity(b))


def test_distinct_symbols_never_merge():
    for a, b in [("il-6", "il-1"), ("nlrp3", "nlrp1"), ("apoe4", "apoe2"), ("tau", "amyloid")]:
        assert normalize_entity(a) != normalize_entity(b), (a, b)


def test_pure_function_is_order_independent():
    ents = ["microglial activation", "microglia", "tau protein", "il-6", "il-1", "amyloid"]
    c1 = EntityCanonicalizer()
    c2 = EntityCanonicalizer()
    fwd = {e: c1.canon(e) for e in ents}
    bwd = {e: c2.canon(e) for e in reversed(ents)}
    assert fwd == bwd, (fwd, bwd)


def test_build_candidate_uses_canon_to_converge():
    from persona.swarm.reader import build_candidate
    c = EntityCanonicalizer()
    a = build_candidate("microglial activation", "neuroinflammatory response", "increases", "g1", "d1", canon=c)
    b = build_candidate("microglia", "neuroinflammation", "increases", "g2", "d2", canon=c)
    assert a.claim_key == b.claim_key, "canonicalized variants must land on the same claim node"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} canonicalize tests passed.")
