"""FC-4 (part 1) dependency_graph: pure aggregation over a fake KG (no DB, no model, no network).

The logic under test is the node-set derivation, load_bearing normalization, and the fragile
rule; a fake KG exercises those deterministically. The FC-3 KG methods it consumes have their
own live-DB coverage in test_data_fc3_kg.py.
"""
from persona.analysis.dependency import dependency_graph, FRAGILE_MIN_LABS


class FakeKG:
    def __init__(self, edges, claims, ratios):
        self._edges = edges
        self._claims = claims
        self._ratios = ratios

    def dependency_edges(self, topic=None):
        return list(self._edges)

    def provenance(self, cid):
        c = self._claims.get(cid)
        return dict(c, claim_id=cid) if c else {}

    def citation_support_ratio(self, cid):
        return {"ratio": self._ratios.get(cid, 0.0)}


def _kg():
    edges = [
        {"src": "clm_a", "dst": "clm_b", "rel_type": "presupposes", "confidence": 0.7, "span": "s1"},
        {"src": "clm_c", "dst": "clm_b", "rel_type": "supports", "confidence": 0.8, "span": "s2"},
        {"src": "clm_b", "dst": "clm_d", "rel_type": "derives_from", "confidence": 0.6, "span": "s3"},
    ]
    claims = {
        "clm_a": {"subject": "drugX", "relation": "raises", "object": "outcomeY",
                  "provenance": "READ", "anchored": False, "independent_sources": 3},
        "clm_b": {"subject": "geneG", "relation": "drives", "object": "drugX",
                  "provenance": "INFERRED", "anchored": False, "independent_sources": 4},
        "clm_c": {"subject": "pathP", "relation": "gates", "object": "geneG",
                  "provenance": "READ", "anchored": False, "independent_sources": 1},
        "clm_d": {"subject": "hallmark", "relation": "underlies", "object": "pathP",
                  "provenance": "HUMAN_CONFIRMED", "anchored": True, "independent_sources": 1},
    }
    ratios = {"clm_a": 0.9, "clm_b": 0.85, "clm_c": 0.5, "clm_d": 0.3}
    return FakeKG(edges, claims, ratios)


def test_edges_verbatim_and_node_set():
    g = dependency_graph("cancer", kg=_kg())
    assert g["edges"] == _kg()._edges  # passed through unchanged
    assert {n["claim_id"] for n in g["nodes"]} == {"clm_a", "clm_b", "clm_c", "clm_d"}


def test_load_bearing_normalized_by_downstream_dependents():
    by = {n["claim_id"]: n for n in dependency_graph(kg=_kg())["nodes"]}
    # depended-on counts: b<-{a,c}=2, d<-{b}=1, a=0, c=0. max=2.
    assert by["clm_b"]["load_bearing"] == 1.0      # 2/2
    assert by["clm_d"]["load_bearing"] == 0.5      # 1/2
    assert by["clm_a"]["load_bearing"] == 0.0
    assert by["clm_c"]["load_bearing"] == 0.0
    for n in by.values():
        assert 0.0 <= n["load_bearing"] <= 1.0


def test_fields_from_claim_and_citation_ratio():
    by = {n["claim_id"]: n for n in dependency_graph(kg=_kg())["nodes"]}
    assert by["clm_a"]["independent_labs"] == 3          # from independent_source_count
    assert by["clm_a"]["support_ratio"] == 0.9           # from citation_support_ratio
    assert by["clm_b"]["provenance"] == "INFERRED"
    assert by["clm_a"]["statement"] == "drugX raises outcomeY"


def test_fragile_rule():
    by = {n["claim_id"]: n for n in dependency_graph(kg=_kg())["nodes"]}
    assert by["clm_a"]["fragile"] is False               # 3 labs, ratio .9
    assert by["clm_b"]["fragile"] is False               # 4 labs
    assert by["clm_c"]["fragile"] is True                # 1 lab < FRAGILE_MIN_LABS
    assert by["clm_d"]["fragile"] is True                # anchored + thin support (ratio .3)
    assert FRAGILE_MIN_LABS == 2


def test_anchored_thin_support_fragile_even_with_enough_labs():
    kg = _kg()
    kg._claims["clm_d"]["independent_sources"] = 5       # plenty of labs...
    kg._ratios["clm_d"] = 0.2                            # ...but anchored on contested citations
    by = {n["claim_id"]: n for n in dependency_graph(kg=kg)["nodes"]}
    assert by["clm_d"]["fragile"] is True


def test_missing_claim_emits_minimal_node_not_dropped():
    kg = _kg()
    del kg._claims["clm_d"]                              # edge still references it
    g = dependency_graph(kg=kg)
    d = next(n for n in g["nodes"] if n["claim_id"] == "clm_d")
    assert d["provenance"] is None and d["fragile"] is True and d["load_bearing"] == 0.0
    assert len(g["edges"]) == 3                          # edge kept


def test_empty_graph_no_edges():
    g = dependency_graph(kg=FakeKG([], {}, {}))
    assert g == {"nodes": [], "edges": []}
