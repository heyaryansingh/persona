"""Statistical forensics: exact, code-run reproducibility checks (never a model)."""
from persona.analysis import forensics as F


def test_statcheck_flags_decision_flip():
    # t(12)=1.9 recomputes to ~.082, reported .008 → flips the significance decision
    r = F.statcheck("t", 1.9, 12, 0.008)
    assert r["status"] == "inconsistent" and r["decision_flip"] and r["severity"] == 3
    assert 0.07 < r["computed_p"] < 0.09


def test_statcheck_consistent_passes():
    # t(30)=3.0 → p≈.005, reported .005 → consistent
    r = F.statcheck("t", 3.0, 30, 0.005)
    assert r["status"] == "ok" and not r["decision_flip"]


def test_grim_catches_impossible_mean():
    assert F.grim(5.19, 28)["status"] == "inconsistent"   # 5.19 unreachable for n=28
    assert F.grim(3.5, 4)["status"] == "ok"                # 14/4 = 3.5 reachable


def test_power_flags_underpowered_design():
    r = F.min_detectable_effect(4)
    assert r["status"] == "weak" and r["min_detectable_d"] >= 1.5   # only large effects


def test_pcurve_detects_hacking_vs_evidential():
    assert F.p_curve([0.049, 0.048, 0.047, 0.045])["status"] == "weak"   # bunched at .05
    assert F.p_curve([0.001, 0.002, 0.01, 0.001])["status"] == "ok"      # right-skewed


def test_run_all_returns_flagged_only():
    flags = F.run_all({
        "tests": [{"test": "t", "stat": 1.9, "df1": 12, "reported_p": 0.008, "span": "p.4"}],
        "descriptives": [{"mean": 5.19, "sd": 1.2, "n": 28, "span": "Table 2"}],
        "designs": [{"n_per_group": 4, "span": "Methods"}],
        "p_values": [0.049, 0.048, 0.047, 0.045]})
    checks = {f["check"]: f["status"] for f in flags}
    assert checks.get("statcheck") == "inconsistent" and checks.get("grim") == "inconsistent"
    assert checks.get("power") == "weak" and checks.get("p_curve") == "weak"
    # every reported flag carries its source span (grounding) except the aggregate p_curve
    assert all(f.get("span") or f["check"] == "p_curve" for f in flags)
