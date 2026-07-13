"""FC-3 KG surface: provenance audit, typed claim-dependency graph, citation support ratio.
Real FalkorDB behavior (skips without a graph DB); the rel_type-validation test needs no DB.
"""
import os
import socket

import pytest

from persona.memory.kg import KG


def _falkor_up() -> bool:
    host = os.environ.get("PERSONA_FALKOR_HOST", "127.0.0.1")
    port = int(os.environ.get("PERSONA_FALKOR_PORT", "6379"))
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except OSError:
        return False


def test_invalid_rel_type_rejected():
    # Validation happens before any DB query, so no live graph is needed.
    kg = object.__new__(KG)
    with pytest.raises(ValueError):
        kg.add_dependency_edge("clm_a", "clm_b", "bogus_rel", 0.9, "some span")


@pytest.mark.skipif(not _falkor_up(), reason="FalkorDB not reachable on :6379")
def test_fc3_provenance_dependency_and_citation_ratio():
    kg = KG(name="kg_fc3_test")
    kg.g.query("MATCH (n) DETACH DELETE n")

    # Two independent labs support drugX -[+]-> outcomeY; one lab reports the opposite (-).
    kg.upsert_source({"slug": "A", "title": "A", "year": 2020, "affiliations": ["MIT"]})
    kg.upsert_source({"slug": "B", "title": "B", "year": 2021, "affiliations": ["Stanford"]})
    kg.upsert_source({"slug": "C", "title": "C", "year": 2022, "affiliations": ["Yale"]})
    pos = kg.add_claim({"subject": "drugX", "relation": "raises", "object": "outcomeY",
                        "effect_sign": "+", "confidence": 0.8, "provenance": "READ"}, "A")
    kg.add_claim({"subject": "drugX", "relation": "raises", "object": "outcomeY",
                  "effect_sign": "+", "confidence": 0.8, "provenance": "READ"}, "B")
    neg = kg.add_claim({"subject": "drugX", "relation": "lowers", "object": "outcomeY",
                        "effect_sign": "-", "confidence": 0.7, "provenance": "READ"}, "C")

    # ---- citation_support_ratio: 2 supporting sources, 1 contrasting -> 2/3.
    csr = kg.citation_support_ratio(pos)
    assert csr["support"] == 2 and csr["contrast"] == 1 and csr["mention"] == 0
    assert csr["ratio"] == round(2 / 3, 4)
    # From the negative claim's viewpoint the roles flip.
    assert kg.citation_support_ratio(neg)["support"] == 1
    assert kg.citation_support_ratio("clm_missing")["ratio"] == 0.0

    # ---- provenance_breakdown: all READ, none confirmed yet.
    pb = kg.provenance_breakdown()
    assert pb["READ"] == 2  # two distinct (subject,object,sign) live claims
    assert pb["HUMAN_CONFIRMED"] == 0 and pb["TESTED"] == 0
    assert set(pb["never_confirmed"]) == {pos, neg}
    assert pb["stale"] == []  # freshly ingested

    # Confirm one side -> it leaves never_confirmed and the count moves.
    kg.human_resolve(pos, truth=True)
    pb2 = kg.provenance_breakdown()
    assert pb2["HUMAN_CONFIRMED"] == 1
    assert pos not in pb2["never_confirmed"] and neg in pb2["never_confirmed"]

    # Age the still-unconfirmed neg claim past the staleness horizon -> it shows up in stale.
    kg.g.query("MATCH (c:Claim {claim_id:$cid}) SET c.ingest_time='2000-01-01T00:00:00+00:00'",
               {"cid": neg})
    stale = kg.provenance_breakdown()["stale"]
    assert any(s["claim_id"] == neg and s["age_days"] > 180 for s in stale)

    # ---- dependency graph: typed edge, topic filter, upsert.
    kg.add_dependency_edge(pos, neg, "contradicts", 0.6, "opposite sign on same pair")
    kg.add_dependency_edge(neg, pos, "qualifies", 0.5, "only in vitro")
    edges = kg.dependency_edges()
    assert len(edges) == 2
    e = next(x for x in edges if x["src"] == pos and x["dst"] == neg)
    assert e["rel_type"] == "contradicts" and e["confidence"] == 0.6
    assert e["span"] == "opposite sign on same pair"
    # topic filter matches (both claims are about drugX); a miss returns nothing.
    assert len(kg.dependency_edges(topic="drugX")) == 2
    assert kg.dependency_edges(topic="zzz_nomatch") == []
    # re-add same (src,dst,rel_type) updates in place, does not duplicate.
    kg.add_dependency_edge(pos, neg, "contradicts", 0.95, "updated span")
    edges2 = kg.dependency_edges()
    assert len(edges2) == 2
    assert next(x for x in edges2 if x["rel_type"] == "contradicts")["confidence"] == 0.95

    kg.g.query("MATCH (n) DETACH DELETE n")
