"""T1.3: contradictions are typed from population; poison detection catches NEW-belief fabrication.
Run: python tests/test_contradiction_typing.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.store import BeliefStore, Claim                     # noqa: E402
from persona.membrane import Membrane                            # noqa: E402
from persona.swarm.reader import build_candidate                 # noqa: E402


def _sub(m, subj, obj, rel, grp, doc, pop):
    m.submit(build_candidate(subj, obj, rel, grp, doc, confidence=0.7, population=pop))


def test_different_population_is_context_divergence():
    s = BeliefStore(); m = Membrane(s)
    _sub(m, "drugX", "outcome", "improves" if False else "increases", "labA", "d1", "elderly")
    _sub(m, "drugX", "outcome", "decreases", "labB", "d2", "young")
    ev = [e for e in m.harvest().contradictions if e.claim_key.startswith("clm_")]
    assert ev and ev[0].kind == "context-divergence", ev
    assert "DIFFERENT populations" in ev[0].detail
    s.close()


def test_same_population_is_true_refutation():
    s = BeliefStore(); m = Membrane(s)
    _sub(m, "drugX", "outcome", "increases", "labA", "d1", "elderly")
    _sub(m, "drugX", "outcome", "decreases", "labB", "d2", "elderly")
    ev = [e for e in m.harvest().contradictions if e.claim_key.startswith("clm_")]
    assert ev and ev[0].kind == "true-refutation", ev
    assert "SAME population" in ev[0].detail
    s.close()


def test_new_belief_fabrication_is_flagged_strict():
    # many candidates from very few groups, no established belief -> manufacture-by-volume
    s = BeliefStore(); m = Membrane(s)
    for i in range(12):
        _sub(m, "fakeA", "fakeB", "increases", f"g{i % 2}", f"doc{i}", None)  # 12 cands, 2 groups
    rep = m.harvest()
    assert rep.strict_claims, "high-volume low-independence NEW belief must be flagged strict"
    s.close()


def test_legitimate_new_belief_not_flagged():
    # same volume but every candidate is an independent group -> NOT poison
    s = BeliefStore(); m = Membrane(s)
    for i in range(12):
        _sub(m, "realA", "realB", "increases", f"lab{i}", f"doc{i}", None)   # 12 cands, 12 groups
    rep = m.harvest()
    assert not rep.strict_claims, "a genuinely independent new belief must NOT be flagged"
    s.close()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} contradiction-typing tests passed.")
