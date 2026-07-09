"""Community detection over the claim graph (v5 P5) — find the SUBTOPICS.

Entities are nodes; claims are weighted edges (weight = independent-source support). Greedy
modularity communities (networkx) partition the graph into subtopics; each community becomes a
synthesis note. Deterministic given the graph. Small communities (<2 entities) are dropped.
"""
from __future__ import annotations


def detect(kg, min_size: int = 3, max_communities: int = 40) -> list[dict]:
    """Return communities as [{entities:[...], n_claims:int}] over the persona's claim graph."""
    snap = kg.graph_snapshot(limit=5000)
    import networkx as nx
    G = nx.Graph()
    for n in snap["nodes"]:
        G.add_node(n["id"])
    for e in snap["edges"]:
        w = (e.get("independent_sources") or 1) + (e.get("confidence") or 0.5)
        if G.has_edge(e["source"], e["target"]):
            G[e["source"]][e["target"]]["weight"] += w
        else:
            G.add_edge(e["source"], e["target"], weight=w)
    if G.number_of_edges() == 0:
        return []
    try:
        comms = nx.community.greedy_modularity_communities(G, weight="weight")
    except Exception:
        comms = list(nx.connected_components(G))
    out = []
    for c in comms:
        ents = sorted(c)
        if len(ents) < min_size:
            continue
        # degree-rank entities so the note names the hubs first
        ents = sorted(ents, key=lambda n: -G.degree(n, weight="weight"))
        out.append({"entities": ents, "size": len(ents)})
    out.sort(key=lambda d: -d["size"])
    return out[:max_communities]
