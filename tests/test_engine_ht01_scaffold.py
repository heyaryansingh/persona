"""RQ-HT01 branch-vs-linear scaffold guards: $0, seeds wired, grounded in the REAL plans, gate holds.

The scaffold must run offline at $0 with ≥20 seeds, derive its base step-counts from the ACTUAL
`_branch_plan`/`DEFAULT_PLAN` (not invented numbers), reproduce the mechanism (branch grounds ≥ linear
because sub-claims are verified independently), report an honest go/no-go, and refuse any live analyst
run without the budget greenlight.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parent.parent / "experiments" / "exp_ht01_branch_vs_linear.py"
_spec = importlib.util.spec_from_file_location("exp_ht01_branch_vs_linear", _PATH)
ht01 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = ht01
_spec.loader.exec_module(ht01)


def test_dry_run_is_free_and_seeded():
    r = ht01.run(seeds=20, base_seed=0, live=False)
    assert r["paid_calls"] == 0 and r["cost_usd"] == 0.0
    assert r["seeds"] >= ht01.MIN_SEEDS
    assert "go_no_go" in r and isinstance(r["go_no_go"]["PASS"], bool)


def test_base_counts_come_from_real_plans():
    # linear DEFAULT_PLAN has exactly one `investigate`; a 2-sub branch plan has exactly two.
    r = ht01.run(seeds=20, base_seed=0, live=False)
    assert r["real_plan_base"]["linear"][1] == 1
    assert r["real_plan_base"]["branch_2sub"][1] == 2


def test_branch_grounds_at_least_as_well_as_linear():
    r = ht01.run(seeds=50, base_seed=1, live=False)
    assert r["branch_grounding"]["mean"] >= r["linear_grounding"]["mean"]


def test_self_check_passes():
    ht01.self_check()


def test_live_run_is_gated(monkeypatch):
    monkeypatch.delenv("PERSONA_HT01_LIVE", raising=False)
    with pytest.raises(ht01.PaidStageGated):
        ht01.require_live("analyst_run")
