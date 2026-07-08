"""VoI/cost ranking tests (assert-based, stdlib only). Run: python tests/test_experiment_value.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.store import BeliefStore, Claim  # noqa: E402
from persona.engine.experiment_value import (  # noqa: E402
    ExperimentCandidate, value_of_information, cost_tier, rank_experiments,
)


def test_value_of_information_peaks_at_uncertainty():
    s = BeliefStore()
    s.add_claim(Claim("c1", "x", logit=0.0))   # p=0.5 -> uncertainty=1
    s.add_claim(Claim("c2", "y", logit=6.0))   # p~0.997 -> uncertainty~0
    scores = {"c1": 0.8, "c2": 0.8}
    v1 = value_of_information(s, "c1", scores)
    v2 = value_of_information(s, "c2", scores)
    assert v1 > v2
    assert abs(v1 - 0.8) < 1e-9
    s.close()


def test_cost_tier_ordering():
    assert cost_tier("existing-data") < cost_tier("cheap-assay") < cost_tier("expensive-study")
    try:
        cost_tier("bogus")
        raise AssertionError("should reject bad resolution_type")
    except ValueError:
        pass


def test_rank_experiments_prefers_high_voi_low_cost():
    s = BeliefStore()
    s.add_claim(Claim("high", "load-bearing uncertain claim", logit=0.0))   # p~0.5
    s.add_claim(Claim("low", "low-load-bearing certain claim", logit=6.0))  # p~0.997
    a = ExperimentCandidate("A", "does X hold?", "high", "existing-data")
    b = ExperimentCandidate("B", "does Y hold?", "low", "expensive-study")
    scores = {"high": 0.8, "low": 0.05}
    ranked = rank_experiments(s, [b, a], scores)
    assert ranked[0]["exp_id"] == "A"
    assert ranked[0]["score"] > ranked[1]["score"]
    s.close()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} experiment_value tests passed.")
