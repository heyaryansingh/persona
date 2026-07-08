"""Dependency/fragility tests (assert-based, stdlib only). Run: python tests/test_dependency.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.store import BeliefStore, Claim  # noqa: E402
from persona.engine.dependency import load_bearing, fragility_cascade  # noqa: E402


def _chain_store():
    s = BeliefStore()
    s.add_claim(Claim("c_app", "application-level claim"))
    s.add_claim(Claim("c_mid", "mid-level claim"))
    s.add_claim(Claim("c_foundation", "foundational claim"))
    s.add_edge("c_app", "c_mid", "derives-from", confidence=0.9)
    s.add_edge("c_mid", "c_foundation", "derives-from", confidence=0.8)
    return s


def test_load_bearing_ranks_foundation_highest():
    s = _chain_store()
    scores = load_bearing(s)
    assert set(scores) == {"c_app", "c_mid", "c_foundation"}
    assert scores["c_foundation"] == max(scores.values())
    assert abs(sum(scores.values()) - 1.0) < 1e-9
    s.close()


def test_load_bearing_penalizes_under_replicated_more():
    # foundation with independent sources should score lower than one w/o sources
    s = _chain_store()
    s.add_source("c_foundation", "PMID:1", "lab_A")
    s.add_source("c_foundation", "PMID:2", "lab_B")
    scores = load_bearing(s)
    s2 = _chain_store()
    scores_bare = load_bearing(s2)
    assert scores["c_foundation"] < scores_bare["c_foundation"]
    s.close()
    s2.close()


def test_fragility_cascade_depths():
    s = _chain_store()
    cascade = fragility_cascade(s, "c_foundation")
    by_id = {c["claim_id"]: c for c in cascade}
    assert "c_mid" in by_id and by_id["c_mid"]["depth"] == 1
    assert "c_app" in by_id and by_id["c_app"]["depth"] == 2
    assert abs(by_id["c_app"]["weight"] - 0.8 * 0.9) < 1e-9
    s.close()


def test_fragility_cascade_respects_max_depth():
    s = _chain_store()
    cascade = fragility_cascade(s, "c_foundation", max_depth=1)
    ids = {c["claim_id"] for c in cascade}
    assert ids == {"c_mid"}
    s.close()


def test_fragility_cascade_no_downstream():
    s = _chain_store()
    cascade = fragility_cascade(s, "c_app")
    assert cascade == []
    s.close()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} dependency tests passed.")
