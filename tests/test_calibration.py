"""Empirical replication calibration — the fitted curve must track published strata + move correctly."""
from persona.analysis import calibration as C


def test_curve_matches_published_strata():
    # OSC 2015 / Gordon 2021: p<.001 replicates ~63-74%, just-significant ~14-28%
    assert 0.58 <= C.curve(0.0005) <= 0.75
    assert 0.15 <= C.curve(0.045) <= 0.32
    # strictly monotone: stronger evidence (smaller p) -> higher replication probability
    assert C.curve(0.0005) > C.curve(0.005) > C.curve(0.02) > C.curve(0.045)


def test_prior_has_resolution():
    strong = C.prior(0.0005, 0.5)["likelihood"]
    weak = C.prior(0.045, 0.5)["likelihood"]
    assert strong - weak >= 0.15          # the whole point: it discriminates, unlike a flat base rate


def test_decision_flip_hard_caps():
    r = C.prior(0.0005, 0.5, n_fail=1)    # even a strong p-value is capped by a proven flip
    assert r["likelihood"] <= 0.20


def test_soft_warnings_penalize():
    base = C.prior(0.01, 0.5)["likelihood"]
    warned = C.prior(0.01, 0.5, n_warn=2)["likelihood"]
    assert warned < base


def test_no_pvalue_falls_back_wide():
    r = C.prior(None, 0.5)
    assert r["from_pvalue"] is False and (r["high"] - r["low"]) >= 0.25   # low resolution -> wide band


def test_min_p_picks_smallest():
    assert C.min_p([0.03, 0.2], [{"reported_p": 0.004}]) == 0.004
    assert C.min_p([], []) is None
    assert C.min_p([1.5, -0.1, 0.02], []) == 0.02   # ignores out-of-range values
