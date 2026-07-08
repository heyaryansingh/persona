"""Build the idea-evolution graph from the belief-store.

Nodes = claims (sized by load-bearing, colored by provenance, carrying their birth/last-update
time and argument state). Edges = shared-entity links (a real co-mention network extracted
from the claim statements) + any `derives-from` candidate edges present in the store. A
timeline of history events drives the time-scrubber (evolution / spawn / flip over time).

`derives-from` inferential edges are the differentiator (BUILD_PLAN 3.2) but gated by E6;
until then the network is entity-linked + contradiction-typed, which is real and useful.
"""
from __future__ import annotations

from ..engine import load_bearing, state_of_argument, trajectory
from ..engine.cross_field import mechanism_tokens

_MAX_EDGES = 3000
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
        nodes.append({
            "id": c.claim_id,
            "statement": c.statement[:140],
            "calibrated_p": round(c.calibrated_p, 3),
            "provenance_state": c.provenance_state,
            "anchor": c.anchor,
            "load_bearing": round(lb.get(c.claim_id, 0.0), 4),
            "independent_sources": store.independent_source_count(c.claim_id),
            "n_updates": tj.n_updates,
            "velocity": round(tj.velocity, 3),
            "state": state_of_argument(store, c.claim_id),
            "entities": sorted(t)[:6],
            "first_seen": hist[0]["ts"] if hist else None,
            "last_update": hist[-1]["ts"] if hist else None,
        })

    ids = [c.claim_id for c in claims]
    edges = []
    # shared-entity co-mention network
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            shared = toks[ids[i]] & toks[ids[j]]
            if shared:
                edges.append({"source": ids[i], "target": ids[j], "kind": "shares",
                              "shared": sorted(shared)[:3], "weight": len(shared)})
                if len(edges) >= _MAX_EDGES:
                    break
        if len(edges) >= _MAX_EDGES:
            break
    # any real derives-from candidate edges in the store
    node_set = set(ids)
    for cid in ids:
        for e in store.edges_from(cid, "derives-from"):
            if e["dst"] in node_set:
                edges.append({"source": e["src"], "target": e["dst"], "kind": "derives-from",
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
