"""FC-5 · Deterministic admission-routing gate (no model, no network).

`admit_decision` turns a candidate belief into a routing verdict: does it get
committed to the belief store, escalated to a human, or rejected? The decision
is a pure function of fields already carried on the candidate (provenance,
independent-source support, and an optional pre-computed probability) so it is
cheap, reproducible, and testable in isolation.

CALIBRATION STATUS — all numeric thresholds below are PLACEHOLDERS pending
RQ-E16 (conformal calibration). They are engineering defaults chosen to give
sane routing behaviour, NOT empirically validated cut-points. Do not cite any
number here as a calibrated operating point until RQ-E16 fits a conformal
predictor and replaces `_BOUND` with a real per-candidate interval half-width.
"""
from __future__ import annotations

import math
from typing import Any

# --- PLACEHOLDER thresholds (pending RQ-E16 conformal calibration) --------------------------------
_P_COMMIT = 0.70        # calibrated_p at/above which strong support may auto-commit
_P_REJECT = 0.40        # calibrated_p below which a candidate is rejected outright
_MIN_INDEP_COMMIT = 2   # distinct-lab independent sources required to auto-commit
_BOUND = 0.15           # placeholder conformal half-width; RQ-E16 makes this per-candidate

# Provenance states that must never auto-commit — a human owns the call.
_HIGH_STAKES_PROVENANCE = {"HUMAN_CONFIRMED", "TESTED", "CORRECTED_EXTRACTION"}


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _derive_p(candidate: dict[str, Any], indep: int, support: int) -> float:
    """calibrated_p if supplied, else logit->p, else a monotone support proxy.

    The support proxy is a placeholder ramp, NOT a calibrated probability
    (RQ-E16). It only needs to be monotone in evidence so routing is sane.
    """
    p = candidate.get("calibrated_p")
    if isinstance(p, (int, float)):
        return max(0.0, min(1.0, float(p)))
    logit = candidate.get("logit")
    if isinstance(logit, (int, float)):
        return _sigmoid(float(logit))
    # placeholder: 0 sources -> 0.0, saturates toward ~0.9 as independent labs accrue
    return round(min(0.9, 0.3 * indep + 0.05 * support), 4)


def admit_decision(candidate: dict[str, Any]) -> dict[str, Any]:
    """Route a candidate belief. Pure/deterministic; no model or network.

    Returns {admit, calibrated_p, route, reason, bound} where route is one of
    'commit' | 'human' | 'reject'. `admit` is True only for 'commit'.
    """
    provenance = str(candidate.get("provenance_state") or candidate.get("provenance") or "").strip()
    anchored = bool(candidate.get("anchored", False))
    indep = int(candidate.get("independent_source_count") or 0)
    support = int(candidate.get("support_count") or 0)
    p = _derive_p(candidate, indep, support)

    # 1. Anchor or high-stakes provenance -> a human owns this, never auto-decide.
    if anchored or provenance in _HIGH_STAKES_PROVENANCE:
        why = "anchored belief" if anchored else f"high-stakes provenance {provenance!r}"
        return {"admit": False, "calibrated_p": p, "route": "human",
                "reason": f"{why} routed to human", "bound": _BOUND}

    # 2. Strong, independently-supported, high-p -> commit.
    if indep >= _MIN_INDEP_COMMIT and p >= _P_COMMIT:
        return {"admit": True, "calibrated_p": p, "route": "commit",
                "reason": f"{indep} independent labs, p={p:.2f} >= {_P_COMMIT} [placeholder]",
                "bound": _BOUND}

    # 3. Weak / insufficient -> reject.
    if p < _P_REJECT or indep < 1:
        return {"admit": False, "calibrated_p": p, "route": "reject",
                "reason": f"insufficient support (indep={indep}, p={p:.2f} < {_P_REJECT}) [placeholder]",
                "bound": _BOUND}

    # 4. Middle ground — supported but not commit-strong -> defer to human.
    return {"admit": False, "calibrated_p": p, "route": "human",
            "reason": f"borderline (indep={indep}, p={p:.2f}) routed to human [placeholder]",
            "bound": _BOUND}
