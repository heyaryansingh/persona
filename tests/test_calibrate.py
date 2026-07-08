"""Calibration/escalation tests. Run: python tests/test_calibrate.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np                                          # noqa: E402
from persona.calibrate import (conformal_threshold, uncertainty,   # noqa: E402
                               should_escalate, rank_for_escalation)


def test_conformal_coverage():
    """Split-conformal: >= 1-alpha of correct items fall under the threshold."""
    rng = np.random.default_rng(0)
    cal = rng.uniform(0, 1, 400)                 # nonconformity scores of correct cal items
    thr = conformal_threshold(cal, alpha=0.1)
    test_correct = rng.uniform(0, 1, 4000)
    coverage = float((test_correct <= thr).mean())
    assert coverage >= 0.88, coverage           # ~0.90 target, sampling slack


def test_uncertainty_and_escalation():
    assert uncertainty(0.5) == 1.0 and uncertainty(0.99) < 0.05
    # high stakes -> escalate even at moderate uncertainty
    assert should_escalate(0.6, stakes=1.0, threshold=0.3)
    assert not should_escalate(0.6, stakes=0.05, threshold=0.3)


def test_rank_puts_uncertain_highstakes_first():
    items = [
        {"id": "settled_low", "calibrated_p": 0.99, "stakes": 0.9},
        {"id": "uncertain_high", "calibrated_p": 0.5, "stakes": 0.9},
        {"id": "uncertain_low", "calibrated_p": 0.5, "stakes": 0.05},
    ]
    ranked = rank_for_escalation(items)
    assert ranked[0]["id"] == "uncertain_high"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} calibrate tests passed.")
