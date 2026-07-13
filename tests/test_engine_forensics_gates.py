"""F3.8 — forensics applicability gates + DEBIT summary. An out-of-domain input must emit a distinct
'not_applicable' state (NOT 'ok'/'passed'), and DEBIT must audit ran/passed/failed/skipped honestly.
All checks run in CODE, never a model (CLAUDE.md)."""
from persona.analysis import forensics as F


def _passed(status):  # the pass verdicts a gated check must NEVER be confused with
    return status in ("ok", "passed")


def test_statcheck_gate_unknown_test_is_not_applicable():
    # A Mann-Whitney U statistic is outside statcheck's t/F/r/z/chi2 domain — gate, don't pass it.
    r = F.statcheck("mannwhitney", 42.0, 30, 0.03)
    assert r["status"] == "not_applicable"
    assert not _passed(r["status"])


def test_grim_gate_no_decimal_granularity_is_not_applicable():
    # A mean reported to 0 decimals has no GRIM granularity — out of domain, not a pass.
    r = F.grim(5.0, 28, decimals=0)
    assert r["status"] == "not_applicable" and not _passed(r["status"])


def test_grimmer_gate_no_decimal_granularity_is_not_applicable():
    r = F.grimmer(5.0, 1.0, 28, decimals=0)
    assert r["status"] == "not_applicable" and not _passed(r["status"])


def test_power_gate_non_two_group_design_is_not_applicable():
    # The MDE closed form is two-sample only; a 4-group ANOVA design is out of domain.
    r = F.min_detectable_effect(30, groups=4)
    assert r["status"] == "not_applicable" and not _passed(r["status"])


def test_pcurve_gate_no_significant_results_is_not_applicable():
    # p-curve interprets significant results; with none there is no curve — gate, don't pass.
    r = F.p_curve([0.2, 0.6, 0.9])
    assert r["status"] == "not_applicable" and not _passed(r["status"])


def test_gate_distinct_from_skipped():
    # not_applicable (out of domain) and skipped (insufficient data) are different states.
    assert F.p_curve([0.2, 0.6]).get("status") == "not_applicable"   # zero significant -> gated
    assert F.p_curve([0.01, 0.02]).get("status") == "skipped"        # 2 significant -> insufficient


def test_debit_counts_gated_check_as_not_applicable_not_passed():
    d = F.debit({
        "tests": [{"test": "wilcoxon", "stat": 10, "df1": 20, "reported_p": 0.04, "span": "p.3"}],
        "descriptives": [{"mean": 5.19, "sd": 1.2, "n": 28, "span": "Table 2"}],  # grim fails
        "p_values": [0.2, 0.6, 0.9]})  # p_curve gated (no significant)
    # the wilcoxon statcheck and the empty-p-curve are gated out, not scored as passes
    assert d["not_applicable"] >= 2
    assert d["failed"] >= 1        # grim on 5.19/28
    assert d["applicable"] == d["passed"] + d["failed"]
    # a gated check never lands in the 'passed' bucket
    gated = [c for c in d["checks"] if c["disposition"] == "not_applicable"]
    assert gated and all(not _passed(c["status"]) for c in gated)


def test_debit_all_gated_yields_zero_applicable():
    d = F.debit({"tests": [{"test": "kruskal", "stat": 3, "df1": 2, "reported_p": 0.1}]})
    assert d["applicable"] == 0 and d["not_applicable"] == 1 and d["passed"] == 0
