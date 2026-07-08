"""Outer-loop / taste tests (assert-based). Run: python tests/test_outer.py

Includes the E13 property in miniature: changing taste weights changes the agenda
(taste is functional, not anthropomorphic theater — BUILD_PLAN 0.3/1.5).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.store import BeliefStore, Claim               # noqa: E402
from persona.membrane import ContradictionEvent            # noqa: E402
from persona.loops.outer import (                          # noqa: E402
    build_agenda, propose_interests, TasteWeights, surprise_of,
)


def _flipped_claim(s, cid):
    """A claim whose belief recently reversed sign -> high surprise."""
    s.add_claim(Claim(cid, f"{cid} used to look true", tier="core"))
    for _ in range(4):
        s.update_belief(cid, +1.0)          # build it up positive
    for _ in range(6):
        s.update_belief(cid, -1.0)          # then reverse across zero
    return cid


def test_surprise_high_after_sign_flip():
    s = BeliefStore()
    _flipped_claim(s, "x")
    assert surprise_of(s, "x") > 0.5
    s.close()


def test_taste_is_functional_weights_change_agenda():
    s = BeliefStore()
    # a load-bearing, uncertain foundation -> high value-of-information, low surprise
    s.add_claim(Claim("found", "foundational uncertain claim", logit=0.2, tier="core"))
    s.add_claim(Claim("app", "downstream application", logit=1.0, tier="core"))
    s.add_edge("app", "found", "derives-from", confidence=0.9)
    s.add_source("found", "PMID:1", "labA")
    # a recently-flipped claim -> high surprise, no dependency mass
    _flipped_claim(s, "flip")

    top_value = build_agenda(s, weights=TasteWeights(value=4.0, surprise=0.0))[0].target
    top_surprise = build_agenda(s, weights=TasteWeights(value=0.0, surprise=4.0))[0].target
    assert top_value != top_surprise, "different dispositions must rank differently"
    assert top_value == "found", top_value        # value-driven -> the load-bearing foundation
    assert top_surprise == "flip", top_surprise   # surprise-driven -> the reversal
    s.close()


def test_contradictions_route_to_human():
    s = BeliefStore()
    s.add_claim(Claim("c", "some belief", logit=1.0, tier="core"))
    ev = ContradictionEvent("c", "c vs c", "true-refutation", 2, 1, "one side single-source")
    agenda = build_agenda(s, contradictions=[ev])
    top = agenda[0]
    assert top.kind == "ask-human" and top.priority >= 3.0
    s.close()


def test_propose_interests_prefers_alive_regions():
    s = BeliefStore()
    s.add_claim(Claim("settled", "very settled", logit=6.0, tier="core"))
    s.add_claim(Claim("alive", "uncertain and moving", logit=0.1, tier="core"))
    for d in (+1.0, -1.0, +1.0):
        s.update_belief("alive", d)
    interests = propose_interests(s, top_k=1)
    assert interests and interests[0].weight > 0
    s.close()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} outer-loop tests passed.")
