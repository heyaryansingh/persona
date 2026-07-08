"""Outer loop (BUILD_PLAN 2.2/2.3): reflect on the belief-state -> recompute interests
and agenda -> decide what matters most now -> act. This is where INITIATIVE originates.

Taste (BUILD_PLAN 1.5) is a ranking policy, tested as *functional* (E13): changing the
weights measurably changes the agenda. Interests are attention weights over regions of
the belief-graph, each with a revisable reason (BUILD_PLAN 1.4) — real iff they change
behavior. Contradictions route to the human (ignition is human-gated, §2.7).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..engine import load_bearing, trajectory, value_of_information
from ..membrane import ContradictionEvent


@dataclass
class Interest:
    name: str            # an entity / region key
    weight: float        # attention allocation
    reason: str          # revisable articulation of why


@dataclass
class TasteWeights:
    value: float = 1.0       # w_v · value-of-information
    tractability: float = 0.5
    surprise: float = 0.8    # w_s · violation of current belief (what makes it feel like a mind)
    cost: float = 0.4        # subtracted


@dataclass
class AgendaItem:
    kind: str            # read | deepen | resolve-contradiction | ask-human | run-test
    target: str          # claim_id / entity / contradiction key
    priority: float
    why: str


def surprise_of(store, claim_id: str, window: int = 5) -> float:
    """How much the recent evidence violated the prior belief (0..1). A sign-crossing
    reversal within the recent window is maximally surprising — the 'most interesting
    event of the day' (BUILD_PLAN 1.5) — and stays surprising for a few steps after."""
    hist = store.history(claim_id)
    if not hist:
        return 0.0
    win = hist[-window:]
    start, end = win[0]["logit_before"], win[-1]["logit_after"]
    start_sign = (start > 0) - (start < 0)
    end_sign = (end > 0) - (end < 0)
    crossed = start_sign != 0 and end_sign != 0 and start_sign != end_sign
    mag = min(1.0, abs(end - start) / 4.0)
    return min(1.0, (0.6 if crossed else 0.0) + 0.4 * mag)


def tractability_of(store, claim_id: str) -> float:
    """Cheap proxy: uncertain-but-active claims are more tractable to move than settled or
    barely-seen ones. Peaks at moderate evidence."""
    c = store.get_claim(claim_id)
    if c is None:
        return 0.0
    p = c.calibrated_p
    return 1.0 - 2 * abs(p - 0.5)     # 1 at p=0.5, 0 at certainty


def taste_priority(voi: float, tractability: float, surprise: float, cost: float,
                   w: TasteWeights) -> float:
    return (w.value * voi + w.tractability * tractability
            + w.surprise * surprise - w.cost * cost)


def build_agenda(store, contradictions: list[ContradictionEvent] | None = None,
                 interests: list[Interest] | None = None,
                 weights: TasteWeights | None = None) -> list[AgendaItem]:
    """Rank what to do next. Contradictions become human-gated resolve items; beliefs
    become deepen/read items scored by taste. Interest weights bias toward matching regions."""
    weights = weights or TasteWeights()
    interests = interests or []
    lb = load_bearing(store)
    interest_w = {i.name.lower(): i.weight for i in interests}

    items: list[AgendaItem] = []

    # contradictions first — routed to the human (ignition is human-gated)
    for ev in (contradictions or []):
        kind = "ask-human" if ev.kind in ("true-refutation", "context-divergence") else "read"
        items.append(AgendaItem(
            kind=kind, target=ev.claim_key,
            priority=3.0 + (ev.support_groups + ev.refute_groups) * 0.1,
            why=f"contradiction [{ev.kind}] — {ev.detail}",
        ))

    # beliefs, scored by taste
    for c in store.core_claims():
        voi = value_of_information(store, c.claim_id, lb)
        surprise = surprise_of(store, c.claim_id)
        tract = tractability_of(store, c.claim_id)
        cost = 1.0 - min(1.0, store.independent_source_count(c.claim_id) / 3.0)  # fewer sources = costlier to trust
        base = taste_priority(voi, tract, surprise, cost, weights)
        # interest bias: does the claim mention an interest region?
        bias = 1.0
        low = c.statement.lower()
        for name, wt in interest_w.items():
            if name in low:
                bias += wt
        items.append(AgendaItem(
            kind="deepen" if tract > 0.3 else "read", target=c.claim_id,
            priority=base * bias,
            why=f"voi={voi:.3f} surprise={surprise:.2f} tract={tract:.2f}",
        ))

    items.sort(key=lambda a: a.priority, reverse=True)
    return items


def propose_interests(store, top_k: int = 3) -> list[Interest]:
    """Spawn interests where the graph is high-uncertainty, high-connectivity (load-bearing),
    and fast-moving — 'curious where the science is most alive' (BUILD_PLAN 1.4)."""
    lb = load_bearing(store)
    scored = []
    for c in store.core_claims():
        uncertainty = 1.0 - 2 * abs(c.calibrated_p - 0.5)
        connectivity = lb.get(c.claim_id, 0.0)
        velocity = abs(trajectory(store, c.claim_id).velocity)
        aliveness = uncertainty * (1 + connectivity) * (1 + velocity)
        scored.append((aliveness, c))
    scored.sort(key=lambda t: t[0], reverse=True)
    out = []
    for aliveness, c in scored[:top_k]:
        out.append(Interest(
            name=c.statement.split()[0] if c.statement else c.claim_id,
            weight=round(min(1.0, aliveness), 3),
            reason=f"high-uncertainty, load-bearing, moving (aliveness={aliveness:.2f})",
        ))
    return out
