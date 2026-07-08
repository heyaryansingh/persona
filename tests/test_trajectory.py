"""Trajectory tests (assert-based, stdlib only). Run: python tests/test_trajectory.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.store import BeliefStore, Claim  # noqa: E402
from persona.engine.trajectory import trajectory, state_of_argument  # noqa: E402


def test_velocity_positive_after_supporting_updates():
    s = BeliefStore()
    s.add_claim(Claim("c1", "x"))
    for _ in range(3):
        s.update_belief("c1", +1.0, strength=0.5)
    t = trajectory(s, "c1")
    assert t.velocity > 0
    assert t.n_updates == 3
    s.close()


def test_acceleration_reflects_reversal():
    s = BeliefStore()
    s.add_claim(Claim("c1", "x"))
    for _ in range(3):
        s.update_belief("c1", +1.0, strength=0.5)   # rising
    for _ in range(3):
        s.update_belief("c1", -1.0, strength=0.5)   # then reversed
    t = trajectory(s, "c1")
    # newer half of the last-5 window is negative deltas, older half positive
    assert t.acceleration < 0
    s.close()


def test_independence_ratio_half():
    s = BeliefStore()
    s.add_claim(Claim("c1", "x"))
    s.add_source("c1", "PMID:1", "lab_A")
    s.add_source("c1", "PMID:2", "lab_B")
    for _ in range(4):
        s.update_belief("c1", +1.0)
    t = trajectory(s, "c1")
    assert t.independence_ratio == 0.5
    s.close()


def test_state_emerging_then_active_front():
    s = BeliefStore()
    s.add_claim(Claim("c1", "x"))
    s.update_belief("c1", +1.0)
    assert state_of_argument(s, "c1") == "emerging"
    s.update_belief("c1", +1.0)
    s.update_belief("c1", +1.0)
    # all-positive history, low logit -> not settled -> active front
    assert state_of_argument(s, "c1") == "active front"
    s.close()


def test_state_contested_on_sign_flip():
    s = BeliefStore()
    s.add_claim(Claim("c1", "x"))
    s.update_belief("c1", +1.0, strength=2.0)
    s.update_belief("c1", -1.0, strength=5.0)
    s.update_belief("c1", +1.0, strength=1.0)
    assert state_of_argument(s, "c1") == "contested"
    s.close()


def test_state_settled_with_independent_sources():
    s = BeliefStore()
    s.add_claim(Claim("c1", "x"))
    s.add_source("c1", "PMID:1", "lab_A")
    s.add_source("c1", "PMID:2", "lab_B")
    for _ in range(3):
        s.update_belief("c1", +1.0, strength=2.0)
    c = s.get_claim("c1")
    assert abs(c.logit) >= 4
    assert state_of_argument(s, "c1") == "settled"
    s.close()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} trajectory tests passed.")
