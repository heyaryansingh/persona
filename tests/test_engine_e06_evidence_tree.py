"""RQ-E06 evidence-tree harness scaffold guards: $0, seeds wired, gate sound, paid arm gated.

The derivation gate must reduce unsupported synthesis statements WITHOUT ever dropping a genuinely
supported one (the anti-gaming guard from I1.1), the qualifier-recall arm (H2) must stay gated in
dry-run, and no paid stage may run without the budget greenlight.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parent.parent / "experiments" / "exp_rq_e06_evidence_tree.py"
_spec = importlib.util.spec_from_file_location("exp_rq_e06_evidence_tree", _PATH)
e06 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = e06          # register before exec so @dataclass can resolve __module__
_spec.loader.exec_module(e06)


def test_dry_run_is_free_and_seeded():
    r = e06.run(case_path=None, seeds=20, base_seed=0, live=False)
    assert r["paid_calls"] == 0 and r["cost_usd"] == 0.0
    assert r["seeds"] >= e06.MIN_SEEDS
    assert r["H2_qualifier_recall_gain"] == "gated"


def test_gate_reduces_unsupported_without_false_drops():
    r = e06.run(case_path=None, seeds=20, base_seed=0, live=False)
    d = r["detail"]
    assert d["unsupported_derivation"] < d["unsupported_free"]
    assert d["false_drops"] == 0                    # never drop a supported statement
    assert d["drop_precision"] == 1.0


def test_qualifier_compat_flags_context_divergence():
    # in_vivo/+ vs in_vitro/- premises must be judged incompatible (context_divergence, not support).
    assert e06.qualifiers_compatible({"model_system": "in_vivo", "direction": "+"},
                                     {"model_system": "in_vitro", "direction": "-"}) is False
    # missing fields don't conflict
    assert e06.qualifiers_compatible({"model_system": "in_vivo"}, {"direction": "+"}) is True


def test_ungrounded_premise_is_unsupported():
    C = e06.Claim
    claims = {"g": C("g", True, {}), "u": C("u", False, {})}
    supported = e06.Statement("s", ["g", "u"], supported=False)
    assert e06.statement_supported(supported, claims) is False


def test_self_check_passes():
    e06.self_check()


def test_paid_stage_is_gated(monkeypatch):
    monkeypatch.delenv("PERSONA_E06_LIVE", raising=False)
    with pytest.raises(e06.PaidStageGated):
        e06.require_live("qualifier_recall")


def test_live_run_refuses_without_greenlight(monkeypatch):
    monkeypatch.delenv("PERSONA_E06_LIVE", raising=False)
    with pytest.raises(e06.PaidStageGated):
        e06.run(case_path=None, seeds=20, base_seed=0, live=True)
