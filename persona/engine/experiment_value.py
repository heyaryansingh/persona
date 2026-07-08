"""Value-of-information / cost ranking for candidate experiments (BUILD_PLAN 3.4).

VoI is EXPERIMENTAL until E7 passes: the baseline to beat for "is this claim
load-bearing" is the Open Targets genetic-evidence prior, not raw citation
counts (# see planning/PHASE0_PLAN.md; E7 evidence gate). Until then treat
`load_bearing_scores` as an externally-supplied hypothesis input, not ground
truth.
"""
from __future__ import annotations

from dataclasses import dataclass

# ponytail: no persona.store import needed — value_of_information only calls
# store.get_claim(...), so `store` is typed loosely (duck-typed) rather than
# adding a hard dependency edge just for a type hint.

COST_TIERS = {
    "existing-data": 1.0,
    "cheap-assay": 3.0,
    "expensive-study": 10.0,
}


@dataclass
class ExperimentCandidate:
    exp_id: str
    question: str
    target_claim_id: str
    resolution_type: str  # one of COST_TIERS
    note: str = ""


def value_of_information(store, target_claim_id: str, load_bearing_scores: dict) -> float:
    claim = store.get_claim(target_claim_id)
    if claim is None:
        raise KeyError(target_claim_id)
    uncertainty = 1 - 2 * abs(claim.calibrated_p - 0.5)  # peaks at p=0.5, 0 at certainty
    return load_bearing_scores.get(target_claim_id, 0.0) * uncertainty


def cost_tier(resolution_type: str) -> float:
    if resolution_type not in COST_TIERS:
        raise ValueError(f"bad resolution_type {resolution_type!r}; expected one of {tuple(COST_TIERS)}")
    return COST_TIERS[resolution_type]


def rank_experiments(store, candidates, load_bearing_scores: dict) -> list:
    scored = []
    for c in candidates:
        voi = value_of_information(store, c.target_claim_id, load_bearing_scores)
        cost = cost_tier(c.resolution_type)
        scored.append({"exp_id": c.exp_id, "voi": voi, "cost": cost, "score": voi / cost})
    scored.sort(key=lambda d: d["score"], reverse=True)
    return scored
