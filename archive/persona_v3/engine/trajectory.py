"""Trajectory of a claim's evidence: the derivative of belief over time (BUILD_PLAN 3.1).

Descriptive only — this is NOT a forecast/collapse predictor (E5 gate not passed).
velocity/acceleration are computed from the tail of `history()` so the engine reacts
to recent evidence without re-scanning the whole belief lifetime.
"""
from __future__ import annotations

from dataclasses import dataclass

WINDOW = 5  # see planning/PHASE0_PLAN.md §3.1 — last-5 window keeps velocity reactive to recent evidence


@dataclass
class Trajectory:
    velocity: float
    acceleration: float
    independence_ratio: float
    n_updates: int


def trajectory(store, claim_id: str) -> Trajectory:
    hist = store.history(claim_id)
    n_updates = len(hist)
    window = hist[-WINDOW:]
    deltas = [h["logit_after"] - h["logit_before"] for h in window]
    velocity = sum(deltas) / len(deltas) if deltas else 0.0

    if len(deltas) >= 2:
        mid = len(deltas) // 2
        older, newer = deltas[:mid], deltas[mid:]
        # odd-length window: give the middle element to both halves so neither is empty
        if not older:
            older = deltas[:1]
        acceleration = (sum(newer) / len(newer)) - (sum(older) / len(older))
    else:
        acceleration = 0.0

    independence_ratio = store.independent_source_count(claim_id) / max(1, n_updates)

    return Trajectory(velocity=velocity, acceleration=acceleration,
                       independence_ratio=independence_ratio, n_updates=n_updates)


def state_of_argument(store, claim_id: str) -> str:
    """Prose label for where an argument stands. Descriptive, not predictive."""
    hist = store.history(claim_id)
    n_updates = len(hist)
    if n_updates < 3:
        return "emerging"

    signs = {1 if h["logit_after"] > 0 else -1 for h in hist if h["logit_after"] != 0}
    if len(signs) > 1:
        return "contested"

    traj = trajectory(store, claim_id)
    current_logit = hist[-1]["logit_after"]
    if abs(current_logit) >= 4 and traj.independence_ratio >= 0.5:
        return "settled"
    return "active front"
