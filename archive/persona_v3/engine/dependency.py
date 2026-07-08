"""Load-bearing / fragility view over the derives-from dependency graph.

# see planning/PHASE0_PLAN.md §3.2/3.3 — dependency edges here are extracted
# CANDIDATE/INFERRED relations (gate E6, human/tested confirmation of the
# extraction pipeline, has not been passed); treat load_bearing/fragility
# output as a hypothesis-ranking tool, not a verified fact.

stdlib + numpy only. PageRank is hand-rolled power iteration (no networkx),
per the frozen contract.
"""
from __future__ import annotations

import numpy as np

DAMPING = 0.85
ITERS = 50


def _derives_from_edges(store):
    """All valid dependency edges (derives-from + presupposes) as (src, dst, confidence).
    Both relations mean the same thing structurally: src depends on dst (dst is more foundational)."""
    edges = []
    for c in store.claims(valid_only=True):
        for rel in ("derives-from", "presupposes"):
            edges.extend(
                (e["src"], e["dst"], e["confidence"])
                for e in store.edges_from(c.claim_id, rel)
            )
    return edges


def load_bearing(store) -> dict:
    """PageRank over derives-from edges (rank flows a->b, i.e. toward the
    foundation b that a depends on), scaled by inverse independent-source
    support so an under-replicated foundation ranks higher.
    """
    edges = _derives_from_edges(store)
    nodes = sorted({n for s, d, _ in edges for n in (s, d)})
    if not nodes:
        return {}
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)

    # out-neighbors per node (unweighted by edge confidence for the walk
    # itself — confidence is used in fragility_cascade, not here)
    out = [[] for _ in range(n)]
    for s, d, _ in edges:
        out[idx[s]].append(idx[d])
    outdeg = np.array([len(o) for o in out], dtype=float)
    dangling = outdeg == 0

    rank = np.full(n, 1.0 / n)
    for _ in range(ITERS):
        new = np.full(n, (1.0 - DAMPING) / n)
        # dangling nodes (no outgoing derives-from edge, e.g. the true
        # foundation) redistribute their mass uniformly, standard PageRank fix
        dangling_mass = rank[dangling].sum()
        new += DAMPING * dangling_mass / n
        for i in range(n):
            if outdeg[i] == 0:
                continue
            share = DAMPING * rank[i] / outdeg[i]
            for j in out[i]:
                new[j] += share
        rank = new

    scores = {}
    for node, i in idx.items():
        inv_support = 1.0 / (1.0 + store.independent_source_count(node))
        scores[node] = rank[i] * inv_support

    total = sum(scores.values())
    if total > 0:
        scores = {k: v / total for k, v in scores.items()}
    return scores


def fragility_cascade(store, claim_id: str, max_depth: int = 4) -> list:
    """Downstream claims that (transitively) derive-from `claim_id`.

    Reverse of the dependency direction: if a --derives-from--> claim_id,
    then `a` is one step downstream (breaks if claim_id breaks). BFS capped
    at max_depth; weight = product of edge confidences along the path.
    """
    edges = _derives_from_edges(store)
    reverse: dict = {}
    for s, d, conf in edges:
        reverse.setdefault(d, []).append((s, conf))

    out = []
    seen = {claim_id}
    frontier = [(claim_id, 0, 1.0)]
    while frontier:
        node, depth, weight = frontier.pop(0)
        if depth >= max_depth:
            continue
        for src, conf in reverse.get(node, []):
            if src in seen:
                continue
            seen.add(src)
            w = weight * conf
            out.append({"claim_id": src, "depth": depth + 1, "weight": w})
            frontier.append((src, depth + 1, w))
    return out
