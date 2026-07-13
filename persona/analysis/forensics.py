"""Statistical forensics (v9) — reproducibility checks that run in CODE, never in a model.

LLMs miscompute p-values, so we don't let them: each function here is a faithful, exact implementation
of a published forensic method. The model's only job upstream is to EXTRACT the reported numbers; the
arithmetic is deterministic, unit-tested, and impossible to argue with. If a reported statistic is
arithmetically impossible, we prove it.

- statcheck: recompute every p-value from its test statistic + df; flag decision inconsistencies.
- GRIM: is a reported mean even reachable for the integer sample size?
- GRIMMER: is a reported SD consistent with that mean + n (sum-of-squares parity)?
- power: the smallest effect the design could actually detect (not post-hoc power).
- p-curve: do significant results carry evidential value, or show a p-hacking signature?

Each check returns a flag dict: {check, status, severity: 0-3, detail, ...} where status is one of:
  ok             — the check ran and the statistic is consistent (a PASS).
  inconsistent   — the check ran and the statistic FAILED.
  weak           — the check ran and the design/evidence is weak (a soft FAIL).
  not_applicable — the input is OUT OF DOMAIN for this check; it never ran. Distinct from a pass.
  skipped        — the input was malformed/insufficient to run (missing df, n<3, ...).

The not_applicable vs skipped/ok split is the point of F3.8: a check that does not APPLY must never be
counted as a pass. `debit()` audits every check's ran/passed/failed/not_applicable/skipped disposition.
"""
from __future__ import annotations

import math

from scipy import stats

# Which test statistics statcheck can recompute a p-value for. A test outside this set is out of the
# forensic's DOMAIN (not merely un-runnable) — statcheck must declare not_applicable, not pass it.
_STATCHECK_DOMAIN = {"t", "f", "r", "z", "chi2"}


def _na(check: str, reason: str) -> dict:
    """Applicability-gate result: the check does NOT apply to this input, so it did not run and must not
    be read as a pass. Kept distinct from 'skipped' (malformed/insufficient) and 'ok' (ran + passed)."""
    return {"check": check, "status": "not_applicable", "severity": 0, "reason": reason,
            "detail": f"{check} does not apply to this input: {reason}."}


def _p_from_stat(test: str, stat: float, df1: float, df2: float | None, tail: int = 2) -> float | None:
    """Recompute a p-value from a test statistic + df(s). test ∈ {t,f,r,z,chi2}."""
    try:
        s = abs(float(stat))
        if test == "t":
            p = stats.t.sf(s, df1) * (2 if tail == 2 else 1)
        elif test == "f":
            p = stats.f.sf(s, df1, df2)
        elif test == "chi2":
            p = stats.chi2.sf(s, df1)
        elif test == "z":
            p = stats.norm.sf(s) * (2 if tail == 2 else 1)
        elif test == "r":                       # correlation → t with df
            if abs(s) >= 1:
                return None
            t = s * math.sqrt(df1 / (1 - s * s))
            p = stats.t.sf(t, df1) * (2 if tail == 2 else 1)
        else:
            return None
        return float(min(max(p, 0.0), 1.0))
    except Exception:
        return None


def statcheck(test: str, stat: float, df1: float, reported_p: float, df2: float | None = None,
              tail: int = 2) -> dict:
    """Recompute the p-value and compare to what was reported. A DECISION inconsistency (the recomputed
    value crosses .05 the other way) can flip a paper's headline finding."""
    # APPLICABILITY GATE: statcheck only covers the t/F/r/z/chi2 family. An unknown test type is out of
    # domain — recomputing its p-value would be meaningless, so declare not_applicable (never a pass).
    if test is None or str(test).lower() not in _STATCHECK_DOMAIN:
        return _na("statcheck", f"unsupported test type '{test}' (domain: {sorted(_STATCHECK_DOMAIN)})")
    computed = _p_from_stat(test.lower(), stat, df1, df2, tail)
    if computed is None or reported_p is None:
        return {"check": "statcheck", "status": "skipped"}
    rep = float(reported_p)
    # a reported "p < .05" style bound: treat as consistent if computed is on the same side
    decision_flip = bool((computed > 0.05) != (rep > 0.05))
    gross = bool(abs(computed - rep) > 0.05 and not (rep < 1e-4 and computed < 1e-3))
    status = "inconsistent" if (decision_flip or gross) else "ok"
    sev = 3 if decision_flip else (1 if gross else 0)
    label = f"{test}({df1}{',' + str(df2) if df2 else ''}) = {stat}"
    detail = (f"{label} recomputes to p = {computed:.4f}; reported p = {rep:.4g}."
              + (" Recomputes to the opposite significance decision — the reported value flips the finding."
                 if decision_flip else " Reported value is inconsistent with the statistic." if gross else ""))
    return {"check": "statcheck", "status": status, "severity": sev, "computed_p": round(computed, 5),
            "reported_p": rep, "decision_flip": decision_flip, "detail": detail}


def grim(mean: float, n: int, decimals: int = 2, items: int = 1) -> dict:
    """GRIM: is the reported mean granularity-consistent? A mean of n integer responses (× items) must
    equal round(k / (n·items)) for some integer k — otherwise it is arithmetically impossible."""
    try:
        # APPLICABILITY GATE: GRIM needs a mean reported to ≥1 decimal of an integer-response scale. With
        # decimals ≤ 0 every integer mean is trivially reachable, so the test has no power — out of domain
        # (a not_applicable, NOT a pass). PLACEHOLDER: decimals>0 as the domain proxy is a heuristic.
        if int(decimals) <= 0:
            return _na("grim", f"mean reported to {decimals} decimals has no GRIM granularity")
        n, items = int(n), int(items)
        if n <= 0:
            return {"check": "grim", "status": "skipped"}
        total = round(float(mean) * n * items)
        recon = round(total / (n * items), decimals)
        consistent = abs(recon - round(float(mean), decimals)) < 10 ** (-decimals - 1)
        return {"check": "grim", "status": "ok" if consistent else "inconsistent",
                "severity": 0 if consistent else 2,
                "detail": (f"Mean {mean} is unreachable for n = {n}" + (f" × {items} items" if items > 1 else "")
                           + f" integer responses (nearest reachable: {recon})." if not consistent
                           else f"Mean {mean} is reachable for n = {n}.")}
    except Exception:
        return {"check": "grim", "status": "skipped"}


def grimmer(mean: float, sd: float, n: int, decimals: int = 2, items: int = 1) -> dict:
    """GRIMMER: given a GRIM-consistent mean, is the reported SD achievable? The sum of squared
    deviations implied by the SD must be a non-negative value consistent with an integer sum of squares."""
    try:
        # APPLICABILITY GATE: same domain as GRIM — with decimals ≤ 0 the sum-of-squares parity test has
        # no granularity to bite on, so GRIMMER does not apply (not_applicable, not a pass). PLACEHOLDER.
        if int(decimals) <= 0:
            return _na("grimmer", f"SD/mean reported to {decimals} decimals has no GRIMMER granularity")
        n, items = int(n), int(items)
        if n <= 1:
            return {"check": "grimmer", "status": "skipped"}
        total = round(float(mean) * n * items)          # integer sum of responses (GRIM)
        # sample variance uses (n-1); sum of squares SS = sd^2*(n-1) + total^2/(n)  (for the raw values)
        ss = float(sd) ** 2 * (n - 1) + (total ** 2) / n
        # Σx² must be a NON-NEGATIVE INTEGER (a sum of squares of integer responses). sd is reported
        # to `decimals` places, so the true sd ∈ [sd−½·10⁻ᵈ, sd+½·10⁻ᵈ); GRIMMER-consistent iff an
        # integer Σx² lies in the band that maps to (Anaya 2016). The old `frac = |ss−round(ss)| < 0.5`
        # was a tautology — that distance is always ≤ 0.5 — so GRIMMER passed EVERY input, fabricating
        # 'ok' for arithmetically impossible SDs (the one thing this module exists to catch). S2 review HIGH.
        prec = 0.5 * 10 ** (-int(decimals))
        ss_lo = max(0.0, float(sd) - prec) ** 2 * (n - 1) + (total ** 2) / n
        ss_hi = (float(sd) + prec) ** 2 * (n - 1) + (total ** 2) / n
        consistent = math.floor(ss_hi + 1e-9) >= math.ceil(ss_lo - 1e-9)
        return {"check": "grimmer", "status": "ok" if consistent else "inconsistent",
                "severity": 0 if consistent else 2,
                "detail": (f"SD {sd} is inconsistent with mean {mean} at n = {n} (implied sum-of-squares "
                           f"{ss:.2f} is not achievable)." if not consistent
                           else f"SD {sd} is consistent with mean {mean} at n = {n}.")}
    except Exception:
        return {"check": "grimmer", "status": "skipped"}


def min_detectable_effect(n_per_group: int, alpha: float = 0.05, power: float = 0.80,
                          groups: int = 2) -> dict:
    """The smallest standardized effect (Cohen's d) a two-group design could detect at `power` — NOT
    post-hoc power. A design that only reaches power for large d likely reports an inflated effect."""
    try:
        # APPLICABILITY GATE: the closed form below is the TWO-sample normal approximation. For any other
        # number of groups the d_min formula does not hold — declare not_applicable rather than return a
        # number that looks like a pass. PLACEHOLDER: extend with the k-group (ANOVA f) MDE if needed.
        if int(groups) != 2:
            return _na("power", f"{groups}-group design is outside the two-sample MDE formula")
        n = int(n_per_group)
        if n < 2:
            return {"check": "power", "status": "skipped"}
        za = float(stats.norm.ppf(1 - alpha / 2))
        zb = float(stats.norm.ppf(power))
        d_min = (za + zb) * math.sqrt(2.0 / n)          # two-sample normal approximation
        weak = bool(d_min >= 0.8)                        # only powered for large effects
        return {"check": "power", "status": "weak" if weak else "ok", "severity": 2 if weak else 0,
                "min_detectable_d": round(float(d_min), 2), "n_per_group": n,
                "detail": (f"n = {n}/group has {int(power*100)}% power only for d ≥ {d_min:.2f} "
                           + ("(large effects only) — the observed effect is likely inflated."
                              if weak else "— adequately powered for moderate effects."))}
    except Exception:
        return {"check": "power", "status": "skipped"}


def p_curve(p_values: list) -> dict:
    """p-curve: do the SIGNIFICANT p-values (< .05) carry evidential value (right-skewed, concentrated
    near 0) or show a p-hacking signature (bunched just under .05)? Uses the binomial right-skew test on
    pp-values (p/.05)."""
    try:
        sig = [float(p) for p in p_values if p is not None and 0 < float(p) < 0.05]
        # APPLICABILITY GATE: p-curve only interprets SIGNIFICANT results. With zero significant p-values
        # there is no curve to evaluate — out of domain (not_applicable), distinct from having 1–2 (below).
        if not sig:
            return _na("p_curve", "no significant (p < .05) results to curve")
        if len(sig) < 3:
            return {"check": "p_curve", "status": "skipped", "n_significant": len(sig)}
        # right-skew: proportion of significant p-values below .025 (evidential studies pile up near 0)
        low = sum(1 for p in sig if p < 0.025)
        prop_low = low / len(sig)
        # binomial test vs the null (uniform → expect half below .025)
        pv = float(stats.binomtest(low, len(sig), 0.5, alternative="less").pvalue)
        hacking = bool(prop_low < 0.5 and pv < 0.10)    # left-skewed / bunched near .05
        return {"check": "p_curve", "status": "weak" if hacking else "ok", "severity": 2 if hacking else 0,
                "n_significant": len(sig), "prop_below_.025": round(float(prop_low), 2),
                "detail": (f"{len(sig)} significant p-values bunch just under .05 (only {int(prop_low*100)}% "
                           f"below .025) — a p-hacking signature, not a strong true effect." if hacking
                           else f"{len(sig)} significant p-values are right-skewed (concentrated near 0) — "
                           "consistent with a real effect.")}
    except Exception:
        return {"check": "p_curve", "status": "skipped"}


def _run_all_raw(stats_extracted: dict) -> list[dict]:
    """Every check's result, unfiltered (ok / inconsistent / weak / not_applicable / skipped). This is the
    ground truth `debit()` audits; `run_all()` filters it down to the flagged (actionable) subset."""
    flags = []
    for t in stats_extracted.get("tests", []):
        r = statcheck(t.get("test", ""), t.get("stat"), t.get("df1"), t.get("reported_p"),
                      t.get("df2"), t.get("tail", 2))
        r["span"] = t.get("span", "")
        flags.append(r)
    for d in stats_extracted.get("descriptives", []):
        if d.get("mean") is not None and d.get("n"):
            g = grim(d["mean"], d["n"], d.get("decimals", 2), d.get("items", 1))
            g["span"] = d.get("span", "")
            flags.append(g)
            if d.get("sd") is not None:
                gm = grimmer(d["mean"], d["sd"], d["n"], d.get("decimals", 2), d.get("items", 1))
                gm["span"] = d.get("span", "")
                flags.append(gm)
    for de in stats_extracted.get("designs", []):
        if de.get("n_per_group"):
            # thread the extracted group count so the two-sample applicability gate is reachable
            # (a k!=2 design gets not_applicable, not a bogus two-sample d). Defaults to 2.
            p = min_detectable_effect(de["n_per_group"], groups=de.get("n_groups") or 2)
            p["span"] = de.get("span", "")
            flags.append(p)
    pv = stats_extracted.get("p_values") or []
    if pv:
        flags.append(p_curve(pv))
    return flags


# status → DEBIT disposition. A check "ran" only if it produced a verdict (passed or failed); a gate that
# fired (not_applicable) or a malformed input (skipped) did NOT run and is never scored as a pass.
_DISPOSITION = {"ok": "passed", "inconsistent": "failed", "weak": "failed",
                "not_applicable": "not_applicable", "skipped": "skipped"}


def run_all(stats_extracted: dict) -> list[dict]:
    """Run every applicable check over the model-extracted numbers. `stats_extracted` shape:
    {tests:[{test,stat,df1,df2,reported_p,tail,span}], descriptives:[{mean,sd,n,decimals,items,span}],
     designs:[{n_per_group,span}], p_values:[..]}. Returns the assessable checks (ok + flagged); skipped
     and the new not_applicable (out-of-domain, gated) are dropped so a gate never reads as a pass to
     downstream counters. Use `debit()` for the full ran/passed/failed/not_applicable/skipped audit."""
    return [f for f in _run_all_raw(stats_extracted)
            if f.get("status") not in (None, "not_applicable", "skipped")]


def debit(stats_extracted: dict) -> dict:
    """DEBIT — Disposition of Every Bit of the Integrity Toolkit. An honest audit of what the forensics
    actually did: which checks ran, passed, failed, were not applicable (gated out of domain), or skipped
    (malformed/insufficient). The point of F3.8: a gated check is reported as such, never silently as a
    pass. `applicable` = passed+failed (checks that genuinely bore on this paper)."""
    raw = _run_all_raw(stats_extracted)
    counts = {"passed": 0, "failed": 0, "not_applicable": 0, "skipped": 0}
    checks = []
    for f in raw:
        disp = _DISPOSITION.get(f.get("status"), "skipped")
        counts[disp] += 1
        checks.append({"check": f.get("check"), "status": f.get("status"), "disposition": disp,
                       "reason": f.get("reason") or f.get("detail", "")})
    total = len(raw)
    applicable = counts["passed"] + counts["failed"]
    return {"total": total, "applicable": applicable, "ran": applicable, **counts, "checks": checks,
            "summary": (f"{total} checks: {counts['passed']} passed, {counts['failed']} failed, "
                        f"{counts['not_applicable']} not applicable, {counts['skipped']} skipped.")}
