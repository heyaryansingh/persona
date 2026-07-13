"""FC-4 (part 1): the claim-dependency graph, read-only over the KG.

`dependency_graph(topic)` renders the field's argument structure for a topic: the typed
DEPENDS_ON edges among claims (verbatim from FC-3 `kg.dependency_edges`) plus a node per
participating claim, each carrying the signals a researcher needs to see what the argument
rests on — how load-bearing it is, how many *independent labs* back it, its citation-support
ratio, its provenance, and whether it's fragile.

Read-only: never mutates the KG, spawns no model, makes no network call. Every number is
either read straight from a Claim field or computed deterministically from the edge set.
"""
from ..memory.membrane import get_kg

# fragile rule (documented, deterministic):
#   - a claim resting on fewer than 2 independent labs is fragile (a single-lab result can't
#     be triangulated — independence, not citation volume, is the anchor; see FINDINGS.md).
#   - an ANCHORED claim whose citation support is thin (ratio < 0.5, i.e. as many contrasting
#     citations as supporting) is also fragile: a human sign-off resting on contested evidence.
FRAGILE_MIN_LABS = 2
THIN_SUPPORT_RATIO = 0.5


def dependency_graph(topic: str = None, kg=None) -> dict:
    """{nodes:[{claim_id, statement, load_bearing, independent_labs, support_ratio, provenance,
    fragile}], edges:[{src, dst, rel_type, confidence, span}]}. Read-only. `kg` is injectable
    for tests; defaults to the current persona's KG (None -> empty graph if FalkorDB is down)."""
    kg = kg if kg is not None else get_kg()
    if kg is None:
        return {"nodes": [], "edges": []}

    edges = kg.dependency_edges(topic)  # verbatim, per contract

    # Downstream count: edge (a)-[DEPENDS_ON]->(b) means a depends on b, so b is *depended upon*.
    # A node's load-bearing raw score is how many claims depend on it (in-degree on dst).
    depended_on = {}
    node_ids = set()
    for e in edges:
        node_ids.add(e["src"])
        node_ids.add(e["dst"])
        depended_on[e["dst"]] = depended_on.get(e["dst"], 0) + 1
    max_dep = max(depended_on.values()) if depended_on else 0

    nodes = []
    for cid in sorted(node_ids):  # deterministic order
        p = kg.provenance(cid)  # subject/relation/object/provenance/anchored/independent_sources
        if not p:
            # add_dependency_edge silently no-ops on a missing claim, but a stale edge could still
            # reference a retired/deleted claim; emit a minimal node rather than dropping the edge.
            nodes.append({"claim_id": cid, "statement": cid, "load_bearing": 0.0,
                          "independent_labs": 0, "support_ratio": 0.0,
                          "provenance": None, "fragile": True})
            continue
        labs = int(p.get("independent_sources") or 0)
        ratio = kg.citation_support_ratio(cid).get("ratio", 0.0)
        anchored = bool(p.get("anchored"))
        # PLACEHOLDER load_bearing: normalized downstream-dependent count in [0,1]. This is a
        # structural proxy only — I1.3 wants it weighted by DOWNSTREAM calibrated_p, pending
        # RQ-E06/E17 validation. Do NOT present as a validated importance metric until then.
        load_bearing = round(depended_on.get(cid, 0) / max_dep, 4) if max_dep else 0.0
        fragile = labs < FRAGILE_MIN_LABS or (anchored and ratio < THIN_SUPPORT_RATIO)
        statement = " ".join(str(p.get(k) or "") for k in ("subject", "relation", "object")).strip()
        nodes.append({"claim_id": cid, "statement": statement, "load_bearing": load_bearing,
                      "independent_labs": labs, "support_ratio": ratio,
                      "provenance": p.get("provenance"), "fragile": fragile})

    return {"nodes": nodes, "edges": edges}


if __name__ == "__main__":  # ponytail: runnable self-check, no DB needed (fake KG)
    class _FakeKG:
        _claims = {
            "clm_a": {"subject": "drugX", "relation": "raises", "object": "outcomeY",
                      "provenance": "READ", "anchored": False, "independent_sources": 3},
            "clm_b": {"subject": "geneG", "relation": "drives", "object": "drugX",
                      "provenance": "READ", "anchored": False, "independent_sources": 1},
            "clm_c": {"subject": "pathP", "relation": "gates", "object": "geneG",
                      "provenance": "HUMAN_CONFIRMED", "anchored": True, "independent_sources": 1},
        }
        _ratios = {"clm_a": 0.9, "clm_b": 0.8, "clm_c": 0.3}

        def dependency_edges(self, topic=None):
            # a depends on b, b depends on c  =>  b and c are depended upon (c most load-bearing... no:
            # c has in-degree 1, b has in-degree 1, a has 0). Both b,c depended-on once.
            return [{"src": "clm_a", "dst": "clm_b", "rel_type": "presupposes",
                     "confidence": 0.7, "span": "x"},
                    {"src": "clm_b", "dst": "clm_c", "rel_type": "derives_from",
                     "confidence": 0.6, "span": "y"}]

        def provenance(self, cid):
            c = self._claims.get(cid)
            return dict(c, claim_id=cid) if c else {}

        def citation_support_ratio(self, cid):
            return {"ratio": self._ratios.get(cid, 0.0)}

    g = dependency_graph(kg=_FakeKG())
    by = {n["claim_id"]: n for n in g["nodes"]}
    assert len(g["edges"]) == 2
    assert len(g["nodes"]) == 3
    # load_bearing: b and c each depended-on once (max=1) -> 1.0; a depended-on 0 -> 0.0
    assert by["clm_a"]["load_bearing"] == 0.0
    assert by["clm_b"]["load_bearing"] == 1.0 and by["clm_c"]["load_bearing"] == 1.0
    # fragile: a has 3 labs, ratio .9 -> not fragile; b has 1 lab -> fragile;
    #          c anchored but ratio .3 < .5 -> fragile (also 1 lab)
    assert by["clm_a"]["fragile"] is False
    assert by["clm_b"]["fragile"] is True and by["clm_c"]["fragile"] is True
    assert by["clm_a"]["statement"] == "drugX raises outcomeY"
    print("dependency.py self-check OK")
