"""Empirically-calibrated replication-likelihood prior — so the auditor's headline % MEANS what it says.

The old auditor anchored only to a field base rate: every paper in a field got the same prior,
regardless of the strength of its own evidence. That number has no resolution — it can't tell a
p<.001 finding from a just-significant one, though those replicate at wildly different rates.

This module replaces it with a curve FITTED on real, published replication outcomes keyed on the
original reported p-value (the single best-established replication predictor). See
`experiments/exp_replication_calibration.py` and `results/FINDINGS.md#RQ-CAL`:
  p_repl = sigmoid(a + b*log10 p),  a=-2.67, b=-1.03  (bootstrap a=-2.76±.22, b=-1.07±.10)
  -> p=.0005:67%  p=.005:43%  p=.02:28%  p=.045:22%   (matches OSC 2015 / Gordon 2021 strata)
Fitted curve beats the flat base rate: Brier 0.218 vs 0.245, resolution 0.032 vs 0.000, reliability
0.004 (well-calibrated). Data: OSC 2015 (Science 349:aac4716), Gordon 2021 (PLOS ONE 16:e0248780),
Camerer 2018 (Nat Hum Behav 2:475), Nuijten 2016 (Behav Res Methods 48:1205).

The arithmetic is exact and deterministic — no model in this file.
"""
from __future__ import annotations

import math

# fitted on 114 labeled replication outcomes — see experiments/exp_replication_calibration.py
_A, _B = -2.673, -1.031
# forensic multipliers (Nuijten 2016: decision-changing errors bias significant results — strong
# non-replication signal; each independent warn compounds).
_WARN_MULT = 0.82          # per soft flag (GRIM-impossible mean, underpowered design, p-curve hacking)
_FLIP_CAP = 0.20           # a code-PROVEN significance flip caps the prior regardless of p-value


def _sig(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def curve(p_min: float) -> float:
    """Raw fitted replication probability from the smallest reported p-value."""
    p = min(max(float(p_min), 1e-6), 0.999)
    return _sig(_A + _B * math.log10(p))


def prior(p_min: float | None, field_base: float, n_fail: int = 0, n_warn: int = 0) -> dict:
    """Empirically-calibrated replication prior for a paper.

    p_min      smallest reported p-value (best evidence-strength proxy); None if no stats extracted.
    field_base the field's base replication rate (weak prior; used alone when p_min is absent).
    n_fail     count of code-PROVEN failures (e.g. statcheck decision flip) — these hard-cap the prior.
    n_warn     count of soft forensic warnings (GRIM/power/p-curve) — each compounds a penalty.

    Returns {likelihood, low, high, rationale, from_pvalue}. Deterministic; cite RQ-CAL.
    """
    fb = min(max(float(field_base), 0.05), 0.9)
    if p_min is None:
        # no reported statistics to key on — fall back to the field base rate, but WIDE (low resolution)
        base = fb
        hw = 0.14
        rat = f"no reported p-values to calibrate on — field base rate {int(fb*100)}%, wide interval"
        from_pv = False
    else:
        c = curve(p_min)
        # blend the p-value curve (the empirical spine) with the field base rate (a weak local prior)
        base = 0.65 * c + 0.35 * fb
        hw = 0.09
        rat = (f"p={p_min:.3g} → fitted curve {int(c*100)}% (RQ-CAL), blended with {int(fb*100)}% "
               f"field base → {int(base*100)}%")
        from_pv = True
    # soft forensic penalties compound multiplicatively
    if n_warn:
        base *= _WARN_MULT ** min(n_warn, 3)
        hw += 0.03
        rat += f"; −{n_warn} soft flag(s)"
    # a proven decision flip is near-fatal for replication — hard cap
    if n_fail:
        base = min(base, _FLIP_CAP)
        hw = max(hw, 0.05)
        rat += f"; {n_fail} code-proven flip → capped at {int(_FLIP_CAP*100)}%"
    like = round(min(max(base, 0.02), 0.97), 2)
    lo = round(max(0.02, like - hw), 2)
    hi = round(min(0.97, like + hw), 2)
    return {"likelihood": like, "low": lo, "high": hi, "rationale": rat, "from_pvalue": from_pv}


def min_p(p_values, tests) -> float | None:
    """Smallest positive reported p-value across the extracted p-list and each test's reported_p."""
    ps = []
    for v in (p_values or []):
        try:
            f = float(v)
            if 0 < f < 1:
                ps.append(f)
        except (TypeError, ValueError):
            pass
    for t in (tests or []):
        try:
            f = float(t.get("reported_p"))
            if 0 < f < 1:
                ps.append(f)
        except (TypeError, ValueError):
            pass
    return min(ps) if ps else None


def demo():
    """Self-check: the calibrated prior tracks the published strata and forensics move it the right way."""
    strong = prior(0.0005, 0.5)          # p<.001 → high
    weak = prior(0.045, 0.5)             # just-significant → low
    flipped = prior(0.045, 0.5, n_fail=1)  # + proven flip → capped
    none = prior(None, 0.5)             # no stats → field base, wide
    assert strong["likelihood"] > weak["likelihood"] + 0.15, (strong, weak)   # resolution
    assert 0.55 <= strong["likelihood"] <= 0.75, strong                        # matches ~63-67%
    assert weak["likelihood"] <= 0.35, weak
    assert flipped["likelihood"] <= _FLIP_CAP, flipped                         # hard cap
    assert none["from_pvalue"] is False and none["high"] - none["low"] >= 0.25, none  # wide
    assert min_p([0.03, 0.2], [{"reported_p": 0.004}]) == 0.004
    print("calibration OK:", {k: strong[k] for k in ("likelihood", "low", "high")}, "| weak",
          weak["likelihood"], "| flipped", flipped["likelihood"])


if __name__ == "__main__":
    demo()
