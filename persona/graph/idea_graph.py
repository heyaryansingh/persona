"""Build the idea-evolution graph from the belief-store.

Nodes = claims (sized by load-bearing, colored by provenance, carrying their birth/last-update
time and argument state). Edges = shared-entity links (a real co-mention network extracted
from the claim statements) + any `derives-from` candidate edges present in the store. A
timeline of history events drives the time-scrubber (evolution / spawn / flip over time).

`derives-from` inferential edges are the differentiator (BUILD_PLAN 3.2) but gated by E6;
until then the network is entity-linked + contradiction-typed, which is real and useful.
"""
from __future__ import annotations

import hashlib
import math

from ..engine import load_bearing, state_of_argument, trajectory
from ..engine.cross_field import mechanism_tokens

_MAX_EDGES = 3000


def _layout_xy(claim_id: str, primary_entity: str, lb: float) -> tuple:
    """Cheap deterministic O(1) layout so a canvas renderer can plot 10k+ nodes without a costly
    client force sim: same-entity claims cluster angularly; load-bearing pulls toward the center.
    Returns (x, y) in [-1, 1]."""
    h = int(hashlib.sha1((primary_entity or claim_id).encode()).hexdigest()[:8], 16)
    theta = (h % 3600) / 3600.0 * 2 * math.pi
    r = 0.15 + (1.0 - min(1.0, lb * 20)) * 0.85           # foundational -> nearer center
    hj = int(hashlib.sha1(claim_id.encode()).hexdigest()[:6], 16)
    jr = ((hj % 100) / 100.0 - 0.5) * 0.12                 # jitter so co-entity nodes don't overlap
    jt = (((hj // 100) % 100) / 100.0 - 0.5) * 0.35
    return round((r + jr) * math.cos(theta + jt), 4), round((r + jr) * math.sin(theta + jt), 4)
# relation/direction words are not entities — exclude them so edges link real concepts
_RELN_WORDS = {"increase", "increases", "increased", "decrease", "decreases", "cause",
               "causes", "caused", "associated", "association", "drive", "drives", "driven",
               "inhibit", "inhibits", "requires", "require", "reduces", "reduced", "promotes",
               "promote", "effect", "with", "and", "the", "via", "through", "levels"}


def build_idea_graph(store, max_nodes: int = 400) -> dict:
    claims = store.core_claims()[:max_nodes]
    lb = load_bearing(store)
    toks: dict[str, set] = {}
    nodes = []
    for c in claims:
        t = mechanism_tokens(c.statement) - _RELN_WORDS
        toks[c.claim_id] = t
        hist = store.history(c.claim_id)
        tj = trajectory(store, c.claim_id)
        lb_c = round(lb.get(c.claim_id, 0.0), 4)
        ents = sorted(t)[:6]
        x, y = _layout_xy(c.claim_id, ents[0] if ents else "", lb_c)
        nodes.append({
            "id": c.claim_id,
            "statement": c.statement[:140],
            "calibrated_p": round(c.calibrated_p, 3),
            "provenance_state": c.provenance_state,
            "anchor": c.anchor,
            "load_bearing": lb_c,
            "independent_sources": store.independent_source_count(c.claim_id),
            "n_updates": tj.n_updates,
            "velocity": round(tj.velocity, 3),
            "state": state_of_argument(store, c.claim_id),
            "entities": ents,
            "x": x, "y": y,
            "first_seen": hist[0]["ts"] if hist else None,
            "last_update": hist[-1]["ts"] if hist else None,
        })

    ids = [c.claim_id for c in claims]
    edges = []
    # shared-entity co-mention network via an INVERTED INDEX (entity -> claims) instead of the
    # O(n^2) all-pairs scan, so the graph scales to 10k+ nodes. Pairs accumulate their shared
    # entities; total edges capped at _MAX_EDGES.
    inverted: dict[str, list] = {}
    for cid in ids:
        for t in toks[cid]:
            inverted.setdefault(t, []).append(cid)
    pair_shared: dict[tuple, list] = {}
    for tok, members in inverted.items():
        if len(members) < 2 or len(members) > 200:      # skip ultra-generic tokens (would be O(k^2))
            continue
        for a_i in range(len(members)):
            for b_i in range(a_i + 1, len(members)):
                key = (members[a_i], members[b_i])
                pair_shared.setdefault(key, []).append(tok)
        if len(pair_shared) >= _MAX_EDGES * 4:
            break
    for (src, dst), shared in pair_shared.items():
        edges.append({"source": src, "target": dst, "kind": "shares",
                      "shared": sorted(shared)[:3], "weight": len(shared)})
        if len(edges) >= _MAX_EDGES:
            break
    # any real inferential-dependency candidate edges in the store (the flagship graph)
    node_set = set(ids)
    for cid in ids:
        for rel in ("derives-from", "presupposes", "generalizes"):
            for e in store.edges_from(cid, rel):
                if e["dst"] in node_set:
                    edges.append({"source": e["src"], "target": e["dst"], "kind": rel,
                                  "candidate": True, "confidence": e["confidence"]})

    # timeline for the scrubber
    timeline = []
    for c in claims:
        for h in store.history(c.claim_id):
            timeline.append({"ts": h["ts"], "claim_id": c.claim_id, "cause": h["cause"]})
    timeline.sort(key=lambda x: x["ts"] or "")

    return {"nodes": nodes, "edges": edges, "timeline": timeline,
            "note": "shared-entity network + contradiction typing; derives-from edges are "
                    "candidate/INFERRED (E6 gate)"}
