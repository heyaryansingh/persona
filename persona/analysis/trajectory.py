"""Trajectory dynamics (PRD F3.4) — how a belief about a topic developed over time, and whether
it is still moving or has settled.

Read-only over the temporal KG. The KG stores each claim as ONE node (subject, object, effect_sign)
whose `confidence` is the current aggregate and whose `valid_from` is when it first entered belief.
So the trajectory of a *topic* over time is the ordered emergence of claims touching that topic:
each claim appears at its `valid_from`, carrying its confidence. Sorted chronologically this is the
arc of the argument — claims accumulating, confidence rising/falling as evidence lands.

The velocity/settling signal answers the screen question "where is the argument heading?" (CLAUDE.md
§5): if recent claims still swing confidence, the belief is MOVING; if the tail is flat, it has
SETTLED. The arithmetic is exact and deterministic — no model, no network in this file.

Thresholds here are unvalidated heuristics (PLACEHOLDER) — they set a sensible default for the
legibility layer, not an evidence-backed claim; tune against real trajectories before trusting them.
"""
from __future__ import annotations

# PLACEHOLDER: settling thresholds — not yet calibrated on real belief trajectories.
_SETTLE_EPS = 0.05      # mean |Δconfidence| per step below this in the recent window ⇒ "settled"
_FLAT_EPS = 0.03        # net recent change below this magnitude ⇒ direction "flat"
_WINDOW = 3             # number of most-recent consecutive steps that define "recent"


def _order(claims: list) -> list:
    """Pure: reduce raw claim rows to the time-ordered trajectory points the PRD asks for.

    Each row is a dict with at least claim_id, confidence, valid_from. Points missing a confidence
    or a timestamp are dropped (a trajectory point needs both). Ties on valid_from break on claim_id
    so the order is deterministic."""
    pts = []
    for c in claims or []:
        cid, conf, vf = c.get("claim_id"), c.get("confidence"), c.get("valid_from")
        if cid is None or conf is None or not vf:
            continue
        pts.append({"claim_id": cid, "confidence": float(conf), "valid_from": str(vf)})
    pts.sort(key=lambda p: (p["valid_from"], p["claim_id"]))
    return pts


def settling(series: list, window: int = _WINDOW, eps: float = _SETTLE_EPS) -> dict:
    """Pure velocity/settling signal over a time-ordered `series` of trajectory points.

    velocity        mean |Δconfidence| per step across the whole series (overall churn rate).
    recent_velocity same, over the last `window` steps (has belief stopped moving lately?).
    direction       net recent change: rising / falling / flat.
    state           settled | moving | insufficient (<2 points can't show motion).

    Deterministic. Thresholds are PLACEHOLDER heuristics (see module header)."""
    confs = [p["confidence"] for p in series]
    n = len(confs)
    if n < 2:
        return {"state": "insufficient", "velocity": 0.0, "recent_velocity": 0.0,
                "direction": "flat", "n_points": n}
    deltas = [confs[i] - confs[i - 1] for i in range(1, n)]
    velocity = sum(abs(d) for d in deltas) / len(deltas)
    recent = deltas[-window:]
    recent_velocity = sum(abs(d) for d in recent) / len(recent)
    net_recent = sum(recent)          # signed: where the tail is heading
    direction = "flat" if abs(net_recent) < _FLAT_EPS else ("rising" if net_recent > 0 else "falling")
    state = "settled" if recent_velocity <= eps else "moving"
    return {"state": state, "velocity": round(velocity, 4),
            "recent_velocity": round(recent_velocity, 4), "direction": direction,
            "net_recent": round(net_recent, 4), "n_points": n}


def _resolve_entities(kg, topic: str) -> list:
    """Reuse kg.search to map a free-text topic to canonical entity names (read-only)."""
    hits = kg.search(topic, limit=12)
    return [h["label"] for h in hits if h.get("type") == "entity" and h.get("label")]


def _fetch(kg, entities: list, limit: int) -> list:
    """Read-only pull of live claims touching any topic entity, with the timestamp the PRD needs.
    Reuses the KG's own query engine (kg._q) — `claims_about` omits valid_from, which is the axis
    this whole module turns on, so we ask for it directly. No writes, no model."""
    if not entities:
        return []
    rows = kg._q(
        """
        MATCH (c:Claim)-[:ABOUT_SUBJECT|ABOUT_OBJECT]->(e:Entity)
        WHERE e.name IN $ents AND c.valid_to IS NULL
        RETURN DISTINCT c.claim_id, c.confidence, c.valid_from, c.subject, c.effect_sign, c.object
        LIMIT $lim
        """, {"ents": list(entities), "lim": limit}).result_set
    return [{"claim_id": r[0], "confidence": r[1], "valid_from": r[2],
             "subject": r[3], "effect_sign": r[4], "object": r[5]} for r in rows]


def trajectory(kg, topic: str, limit: int = 200) -> dict:
    """PRD F3.4: the time-ordered belief trajectory for `topic` + a velocity/settling signal.

    Returns {topic, entities, series:[{claim_id, confidence, valid_from}, ...], signal:{...}}.
    Read-only over the KG, deterministic, no model/network."""
    entities = _resolve_entities(kg, topic)
    series = _order(_fetch(kg, entities, limit))
    return {"topic": topic, "entities": entities, "series": series,
            "signal": settling(series)}


def demo():
    """Self-check on the pure signal — a settling arc reads settled, a swinging tail reads moving."""
    settled = _order([
        {"claim_id": "c1", "confidence": 0.50, "valid_from": "2024-01-01T00:00:00+00:00"},
        {"claim_id": "c2", "confidence": 0.72, "valid_from": "2024-03-01T00:00:00+00:00"},
        {"claim_id": "c3", "confidence": 0.80, "valid_from": "2024-06-01T00:00:00+00:00"},
        {"claim_id": "c4", "confidence": 0.81, "valid_from": "2024-09-01T00:00:00+00:00"},
        {"claim_id": "c5", "confidence": 0.82, "valid_from": "2024-12-01T00:00:00+00:00"},
    ])
    moving = _order([
        {"claim_id": "d1", "confidence": 0.40, "valid_from": "2024-01-01T00:00:00+00:00"},
        {"claim_id": "d2", "confidence": 0.75, "valid_from": "2024-04-01T00:00:00+00:00"},
        {"claim_id": "d3", "confidence": 0.35, "valid_from": "2024-08-01T00:00:00+00:00"},
        {"claim_id": "d4", "confidence": 0.70, "valid_from": "2024-12-01T00:00:00+00:00"},
    ])
    s, m = settling(settled), settling(moving)
    assert [p["claim_id"] for p in settled] == ["c1", "c2", "c3", "c4", "c5"], settled
    assert s["state"] == "settled" and s["direction"] in ("flat", "rising"), s
    assert m["state"] == "moving", m
    assert settling([])["state"] == "insufficient"
    assert m["recent_velocity"] > s["recent_velocity"], (s, m)
    print("trajectory OK: settled", s["state"], s["recent_velocity"],
          "| moving", m["state"], m["recent_velocity"])


if __name__ == "__main__":
    demo()
