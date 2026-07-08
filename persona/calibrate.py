"""Calibration & escalation (v2, P7). Two pieces the tech sweep (planning §2.5) recommends:

1. split-conformal threshold — set an admit/abstain cutoff for a PROVABLE target error rate
   from a calibration set (distribution-free); the principled way to gate the membrane and
   the human-escalation trigger, instead of a hand-picked probability.
2. decision-theoretic escalation — escalate on uncertainty × stakes, not uncertainty alone.

E11 (which uncertainty ESTIMATOR — semantic entropy / self-consistency / verbalized) needs a
labeled biomedical QA set to select and is pending; the mechanism here is estimator-agnostic
(feed it any per-claim nonconformity score).
"""
from __future__ import annotations

import numpy as np


def uncertainty(calibrated_p: float) -> float:
    """0 at certainty (p→0 or 1), 1 at maximal uncertainty (p=0.5)."""
    return 1.0 - 2.0 * abs(calibrated_p - 0.5)


def conformal_threshold(cal_scores, alpha: float = 0.1) -> float:
    """Split-conformal cutoff: admit items whose nonconformity score <= threshold to control
    the error rate at ~alpha. cal_scores = scores of CORRECT calibration items (higher = more
    uncertain)."""
    s = np.asarray([x for x in cal_scores], dtype=float)
    n = len(s)
    if n == 0:
        return float("inf")
    level = min(1.0, np.ceil((n + 1) * (1 - alpha)) / n)
    return float(np.quantile(s, level, method="higher"))


def should_escalate(calibrated_p: float, stakes: float, threshold: float) -> bool:
    """Decision-theoretic: route to a human when uncertainty x stakes crosses the threshold.
    High-stakes claims escalate at a lower uncertainty bar."""
    return uncertainty(calibrated_p) * max(0.0, stakes) >= threshold


def rank_for_escalation(items) -> list:
    """items: iterable of dicts with 'calibrated_p' and 'stakes'. Returns them sorted by
    escalation priority (uncertainty x stakes) desc — the human sees the highest-leverage
    judgment calls first."""
    scored = [{**it, "priority": round(uncertainty(it.get("calibrated_p", 0.5))
                                       * max(0.0, it.get("stakes", 0.0)), 4)} for it in items]
    scored.sort(key=lambda d: d["priority"], reverse=True)
    return scored
