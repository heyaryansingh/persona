"""The intellectual engine (BUILD_PLAN Part 3): treat the literature as a structured,
moving system. Instruments: trajectory (3.1), dependency/load-bearing + fragility
(3.2/3.3), experiment-value (3.4), silence (3.5), cross-field (3.6).

Each instrument is gated by a pre-registered experiment (E5/E6/E7/H3.x). Until its gate
passes, forecasts render DESCRIPTIVE and dependency edges render as CANDIDATE, not fact
(planning/PHASE0_PLAN.md §2, §5).
"""
from .trajectory import Trajectory, trajectory, state_of_argument
from .dependency import load_bearing, fragility_cascade
from .experiment_value import ExperimentCandidate, value_of_information, cost_tier, rank_experiments
from .silence import entity_year_counts, abandonment_score, detect_abandoned
from .cross_field import mechanism_tokens, similarity, align

__all__ = [
    "Trajectory", "trajectory", "state_of_argument",
    "load_bearing", "fragility_cascade",
    "ExperimentCandidate", "value_of_information", "cost_tier", "rank_experiments",
    "entity_year_counts", "abandonment_score", "detect_abandoned",
    "mechanism_tokens", "similarity", "align",
]
