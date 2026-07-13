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

# citation-vs-support divergence (F3.3) — all PLACEHOLDER heuristics pending RQ validation:
#   - CITED_MIN: a claim needs at least this many citations on its (subject,object) pair to count as
#     "highly-cited" enough to flag (a 1-citation claim isn't a load-bearing field myth).
#   - UNTESTED_GAP: an experimentally-never-tested claim can't count as fully supported no matter how
#     one-sided its citation intent is — its support gap is floored here. This surfaces the classic
#     "everyone cites it, nobody re-ran it" failure mode divergence is meant to catch.
CITED_MIN = 3
UNTESTED_GAP = 0.5


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


def citation_vs_support_divergence(topic: str = None, kg=None) -> list:
    """F3.3: flag the field's highly-cited-but-thinly-supported (or never-tested) claims.

    Over the topic's claims (same universe as `dependency_graph` — those in DEPENDS_ON edges), a
    claim diverges when it is well-cited on its (subject,object) pair yet its citations don't
    actually *support* it — either the citation intent is contested (FC-3 `citation_support_ratio`
    ratio below THIN_SUPPORT_RATIO) or it was never experimentally TESTED (provenance). The whole
    point: citation volume is a popularity signal, not an evidence signal, and the two can diverge.

    Returns [{claim_id, citations, support_ratio, divergence}] for flagged claims only, sorted by
    divergence desc (claim_id tiebreak). divergence in [0,1]: citation prominence x support gap.
    Read-only: no mutation, no model, no network. Deterministic. `kg` injectable for tests."""
    kg = kg if kg is not None else get_kg()
    if kg is None:
        return []

    # topic-scoped claim universe: the claims touching a DEPENDS_ON edge for this topic (the only
    # read-only, topic-filtered claim source in the KG — reused verbatim, no new KG method).
    edges = kg.dependency_edges(topic)
    cids = set()
    for e in edges:
        cids.add(e["src"])
        cids.add(e["dst"])

    # pass 1: gather citations + support_ratio per claim; max citations normalizes prominence.
    rows, max_cit = {}, 0
    for cid in cids:
        csr = kg.citation_support_ratio(cid)  # {support, contrast, mention, ratio}
        citations = int(csr.get("support", 0)) + int(csr.get("contrast", 0)) + int(csr.get("mention", 0))
        p = kg.provenance(cid) or {}
        # never-tested = not experimentally re-run (provenance != TESTED); a human sign-off
        # (HUMAN_CONFIRMED/anchored) is judgment, not a re-analysis, so it still reads as untested.
        never_tested = p.get("provenance") != "TESTED"
        rows[cid] = {"citations": citations, "ratio": float(csr.get("ratio", 0.0)),
                     "never_tested": never_tested}
        max_cit = max(max_cit, citations)

    out = []
    for cid in sorted(cids):  # deterministic
        r = rows[cid]
        thin = r["ratio"] < THIN_SUPPORT_RATIO
        # flag: cited enough AND (support is thin OR it was never tested).
        if r["citations"] < CITED_MIN or not (thin or r["never_tested"]):
            continue
        support_gap = 1.0 - r["ratio"]
        if r["never_tested"]:
            support_gap = max(support_gap, UNTESTED_GAP)  # floor: untested != fully supported
        prominence = r["citations"] / max_cit if max_cit else 0.0
        divergence = round(prominence * support_gap, 4)
        out.append({"claim_id": cid, "citations": r["citations"],
                    "support_ratio": round(r["ratio"], 4), "divergence": divergence})

    out.sort(key=lambda d: (-d["divergence"], d["claim_id"]))
    return out


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
