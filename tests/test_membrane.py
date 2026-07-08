"""Membrane tests (assert-based). Run: python tests/test_membrane.py

Covers convergence-by-independence, citation-echo rejection, the E10 adaptive switch
against correlated poison, and typed contradiction routing.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.store import BeliefStore, Claim          # noqa: E402
from persona.membrane import Membrane                  # noqa: E402
from persona.swarm.reader import Candidate             # noqa: E402


_N = [0]  # each candidate is a DISTINCT document (the store dedups by doc_id)


def _cand(key, direction, group, conf=0.6):
    _N[0] += 1
    return Candidate(claim_key=key, statement=f"{key} claim", direction=direction,
                     group=group, doc_id=f"{group}:doc{_N[0]}", confidence=conf)


def test_independent_convergence_commits():
    m = Membrane(BeliefStore())
    m.submit(_cand("k1", +1, "Journal_A"))
    m.submit(_cand("k1", +1, "Journal_B"))     # 2 independent groups agree
    rep = m.harvest()
    assert "k1" in rep.committed
    assert m.store.get_claim("k1").predicted == 1
    m.store.close()


def test_citation_echo_is_blocked():
    """Five candidates from ONE group is echo, not independent convergence -> held."""
    m = Membrane(BeliefStore())
    for _ in range(5):
        m.submit(_cand("k2", +1, "Journal_A"))
    rep = m.harvest()
    assert "k2" in rep.held and "k2" not in rep.committed
    assert m.store.get_claim("k2") is None      # never committed
    m.store.close()


def test_adaptive_switch_blocks_correlated_poison():
    """An established belief flooded by many correlated (single-group) wrong candidates:
    membrane switches that claim to strict, applies backpressure, and does NOT flip it."""
    s = BeliefStore()
    s.add_claim(Claim("b", "established true belief", logit=3.0, tier="core"))  # established, not anchored
    m = Membrane(s)
    for _ in range(8):
        m.submit(_cand("b", -1, "troll_journal"))    # correlated, sustained, wrong
    rep = m.harvest()
    assert "b" in rep.strict_claims, "should detect the poisoning signature"
    assert m.backpressure < 1.0, "backpressure should narrow fan-out"
    assert "b" not in rep.committed
    assert s.get_claim("b").predicted == 1, "established belief must not flip on correlated echo"
    s.close()


def test_typed_contradiction_context_divergence():
    m = Membrane(BeliefStore())
    for g in ("A", "B"):
        m.submit(_cand("k3", +1, f"J_{g}"))
    for g in ("C", "D"):
        m.submit(_cand("k3", -1, f"J_{g}"))
    rep = m.harvest()
    assert len(rep.contradictions) == 1
    ev = rep.contradictions[0]
    assert ev.kind == "context-divergence", ev.kind   # both sides independently supported
    m.store.close()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} membrane tests passed.")
