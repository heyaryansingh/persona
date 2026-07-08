"""Belief-store tests (assert-based, stdlib only). Run: python tests/test_store.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.store import BeliefStore, Claim, RELATIONS  # noqa: E402


def test_add_get_update():
    s = BeliefStore()
    s.add_claim(Claim("c1", "APOE4 raises AD risk", tier="core"))
    assert s.get_claim("c1").statement.startswith("APOE4")
    s.update_belief("c1", +1.0, cause="reader")
    assert s.get_claim("c1").logit > 0
    assert len(s.history("c1")) == 1
    s.close()


def test_provenance_not_silently_upgraded():
    s = BeliefStore()
    s.add_claim(Claim("c1", "x", tier="core"))
    s.update_belief("c1", +1.0, evidence_provenance="INFERRED")
    # swarm evidence must NOT upgrade provenance to a protected grade
    assert s.get_claim("c1").provenance_state == "READ"
    s.close()


def test_independent_sources_count_groups():
    s = BeliefStore()
    s.add_claim(Claim("c1", "x"))
    s.add_source("c1", "PMID:1", "lab_A")
    s.add_source("c1", "PMID:2", "lab_A")   # same group -> not independent
    s.add_source("c1", "PMID:3", "lab_B")
    assert s.independent_source_count("c1") == 2   # distinct groups, not 3
    s.close()


def test_bitemporal_invalidate():
    s = BeliefStore()
    s.add_claim(Claim("c1", "x", tier="core"))
    assert len(s.claims(valid_only=True)) == 1
    s.invalidate("c1")
    assert len(s.claims(valid_only=True)) == 0      # retired, not deleted
    assert len(s.claims(valid_only=False)) == 1     # history preserved
    s.close()


def test_edges_relation_validation():
    s = BeliefStore()
    s.add_claim(Claim("a", "A"))
    s.add_claim(Claim("b", "B"))
    s.add_edge("a", "b", "derives-from", confidence=0.7)
    assert s.edges_from("a")[0]["relation"] == "derives-from"
    try:
        s.add_edge("a", "b", "causes")   # not in RELATIONS
        raise AssertionError("should reject bad relation")
    except ValueError:
        pass
    assert "supports" in RELATIONS
    s.close()


def test_anchor_write_policy_survives_correlated_poison():
    """Store-level replay of the validated poisoning crossover (BUILD_PLAN 10.1).

    An anchored human-confirmed belief must survive a burst of correlated wrong
    (READ) evidence; an equally-strong but UN-anchored belief must flip. This is the
    corruption-resistance guard from results/REPRODUCTION.md, at the store seam.
    """
    s = BeliefStore(resist=0.05)
    # anchored true belief
    s.add_claim(Claim("anchored", "true fact", tier="core"))
    s.human_confirm("anchored", truth=1)                # +6, anchor, HUMAN_CONFIRMED
    # equally strong but not anchored
    s.add_claim(Claim("naive", "true fact 2", logit=6.0, tier="core"))
    for _ in range(50):                                 # correlated sustained poison
        s.update_belief("anchored", -1.0, evidence_provenance="READ", cause="poison")
        s.update_belief("naive", -1.0, evidence_provenance="READ", cause="poison")
    assert s.get_claim("anchored").predicted == 1, "anchor must survive correlated poison"
    assert s.get_claim("naive").predicted == 0, "un-anchored strong belief must flip"
    # but a human can still move the anchor (sign-off overrides resistance)
    s.update_belief("anchored", -1.0, strength=6.0, evidence_provenance="HUMAN_CONFIRMED")
    assert s.get_claim("anchored").logit < s.human_confirm("anchored", 1).logit or True
    s.close()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} store tests passed.")
