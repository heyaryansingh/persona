"""RQ-E07c team-physics harness guards (I1.2): $0, equal-token, post-membrane novelty, gate holds.

The frozen harness must: run offline at $0 with >=20 seeds; count validated novelty ONLY after the
membrane (a non-verbatim/correlated-error extraction is rejected, false_admitted stays 0); refuse any
live model read without the budget greenlight; and never let dry-run make a live topology claim.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parent.parent / "experiments" / "exp_rq_e07c_team_physics_live.py"
_spec = importlib.util.spec_from_file_location("exp_rq_e07c_team_physics_live", _PATH)
e07 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = e07
_spec.loader.exec_module(e07)


def test_dry_run_is_free_and_seeded():
    r = e07.run(seeds=20, base_seed=0, live=False)
    assert r["paid_calls"] == 0 and r["cost_usd"] == 0.0
    assert r["seeds"] >= e07.MIN_SEEDS
    assert "preregistration" in r and r["preregistration"]["arms"]


def test_membrane_rejects_correlated_error_extraction():
    # frozen contract: a non-verbatim extraction never enters belief (false_admitted == 0).
    admitted, false_ct = e07.membrane_admit([1, 2, 3], produced_error=True, already=set())
    assert admitted == set() and false_ct == 0
    # a clean extraction admits only claims not already in the store (novelty).
    admitted2, _ = e07.membrane_admit([1, 2, 3], produced_error=False, already={2})
    assert admitted2 == {1, 3}


def test_equal_token_budget_is_respected():
    # no arm may spend more than the total budget B (equal-token discipline).
    import numpy as np
    uni = e07.build_universe(0)
    for arm in (e07.arm_sequential, e07.arm_marginal_stopping):
        r = arm(uni, e07.TOTAL_BUDGET, np.random.default_rng(0), live=False)
        assert r["tokens"] <= e07.TOTAL_BUDGET
    for k in (2, 5, 14):
        r = e07.arm_parallel_breadth(uni, e07.TOTAL_BUDGET, k, np.random.default_rng(0), live=False)
        assert r["tokens"] <= e07.TOTAL_BUDGET, f"k={k} overspent"


def test_effective_team_size_is_a_swept_k():
    r = e07.run(seeds=20, base_seed=0, live=False)
    assert r["effective_team_size"] in dict(r["parallel_k_curve_npt"])


def test_self_check_passes():
    e07.self_check()


def test_live_read_is_gated(monkeypatch):
    monkeypatch.delenv("PERSONA_E07_LIVE", raising=False)
    with pytest.raises(e07.PaidStageGated):
        e07.require_live("read_source")
    import numpy as np
    with pytest.raises(e07.PaidStageGated):
        e07.arm_sequential(e07.build_universe(0), e07.TOTAL_BUDGET, np.random.default_rng(0), live=True)
