"""T4.2 — RQ-E05 retrieval harness scaffold guards.

The scaffold must (1) run end-to-end at $0 with >=20 bootstrap seeds, (2) keep answer correctness
GATED in dry-run (no paid grader), and (3) genuinely refuse to spend on any paid stage unless the
human budget greenlight (PERSONA_E05_LIVE=1) is set. These are the properties S0 gated T4.2 on.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parent.parent / "experiments" / "exp_rq_e05_retrieval.py"
_spec = importlib.util.spec_from_file_location("exp_rq_e05_retrieval", _PATH)
e05 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = e05          # register before exec so @dataclass can resolve __module__
_spec.loader.exec_module(e05)


def test_dry_run_is_free_and_seeded():
    r = e05.run(questions_path=None, seeds=20, base_seed=0, live=False)
    assert r["paid_calls"] == 0 and r["cost_usd"] == 0.0
    assert r["seeds"] >= e05.MIN_SEEDS
    assert r["metrics"]["correctness"] == "gated"
    assert r["n_items"] == 5


def test_self_check_passes():
    e05.self_check()                      # asserts internally; raises on any wiring regression


def test_paid_stage_is_gated(monkeypatch):
    monkeypatch.delenv("PERSONA_E05_LIVE", raising=False)
    with pytest.raises(e05.PaidStageGated):
        e05.require_live("rerank")


def test_live_run_refuses_without_greenlight(monkeypatch):
    monkeypatch.delenv("PERSONA_E05_LIVE", raising=False)
    with pytest.raises(e05.PaidStageGated):
        e05.run(questions_path=None, seeds=20, base_seed=0, live=True)
