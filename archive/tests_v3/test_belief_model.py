"""T0.2: belief = NET independent evidence (contrary evidence lowers it).
Run: python tests/test_belief_model.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.store import BeliefStore                     # noqa: E402
from persona.membrane import Membrane                     # noqa: E402
from persona.swarm.reader import build_candidate          # noqa: E402


def _submit(m, subj, obj, reln, groups, conf=0.8):
    for g in groups:
        m.submit(build_candidate(subj, obj, reln, f"J{g}", f"J{g}:{reln}:d", confidence=conf))


def test_contrary_evidence_lowers_belief():
    s = BeliefStore()
    m = Membrane(s)
    key = build_candidate("a", "b", "increases", "J", "x").claim_key
    _submit(m, "a", "b", "increases", ["A", "B", "C"])
    m.harvest()
    p_up = s.get_claim(key).calibrated_p
    assert p_up > 0.7, p_up
    # add independent CONTRARY evidence
    _submit(m, "a", "b", "decreases", ["D", "E"])
    m.harvest()
    p_after = s.get_claim(key).calibrated_p
    assert p_after < p_up, (p_up, p_after)          # net evidence dropped the belief
    s.close()


def test_balanced_evidence_is_uncertain():
    s = BeliefStore()
    m = Membrane(s)
    key = build_candidate("x", "y", "increases", "J", "x").claim_key
    _submit(m, "x", "y", "increases", ["A", "B", "C"])
    _submit(m, "x", "y", "decreases", ["D", "E", "F"])
    m.harvest()
    p = s.get_claim(key).calibrated_p
    assert 0.4 <= p <= 0.6, p                        # balanced -> ~0.5, honest uncertainty
    s.close()


def test_confidence_weights_evidence():
    s = BeliefStore()
    m = Membrane(s)
    key = build_candidate("p", "q", "increases", "J", "x").claim_key
    _submit(m, "p", "q", "increases", ["A", "B"], conf=0.9)
    _submit(m, "p", "q", "decreases", ["C", "D"], conf=0.3)  # weaker contrary evidence
    m.harvest()
    assert s.get_claim(key).calibrated_p > 0.5, "stronger-confidence side should win"
    s.close()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} belief-model tests passed.")
