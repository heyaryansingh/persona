"""A paper (Source) node exposes its extracted claims as first-class 'main points', and
crosscheck surfaces the supports/contradictions those claims participate in — the data behind
the clickable paper idea-graph. Real FalkorDB behavior; skips without a graph DB.
"""
import os
import socket

import pytest


def _falkor_up() -> bool:
    host = os.environ.get("PERSONA_FALKOR_HOST", "127.0.0.1")
    port = int(os.environ.get("PERSONA_FALKOR_PORT", "6379"))
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return True
    except OSError:
        return False


@pytest.mark.skipif(not _falkor_up(), reason="FalkorDB not reachable on :6379")
def test_source_node_returns_main_points_and_crosscheck_finds_supports():
    from persona.memory.kg import KG
    kg = KG(name="kg_paper_graph_test")
    kg.g.query("MATCH (n) DETACH DELETE n")
    # paper A asserts X->Y (+); paper B (independent lab) asserts the same -> a support
    kg.upsert_source({"slug": "paperA", "title": "Paper A", "year": 2020, "doi": "10.1/a",
                      "affiliations": ["MIT"]})
    kg.upsert_source({"slug": "paperB", "title": "Paper B", "year": 2021, "affiliations": ["Stanford"]})
    kg.add_claim({"claim_id": "x", "subject": "drugX", "relation": "raises", "object": "outcomeY",
                  "effect_sign": "+", "confidence": 0.8, "provenance": "READ"}, "paperA")
    kg.add_claim({"claim_id": "x", "subject": "drugX", "relation": "raises", "object": "outcomeY",
                  "effect_sign": "+", "confidence": 0.8, "provenance": "READ"}, "paperB")

    node = kg.node("source:paperA")
    assert node["type"] == "source"
    assert node.get("slug") == "paperA"
    claims = node.get("claims", [])
    assert claims, "paper node must expose its extracted claims (main points)"
    assert any("drugx" in c["text"].lower() and "outcomey" in c["text"].lower() for c in claims)

    cc = kg.crosscheck("drugX", "outcomeY", "+")
    assert len(cc["support"]) >= 1, "the same-sign claim from another lab is a support"
    assert cc["contradict"] == []
    kg.g.query("MATCH (n) DETACH DELETE n")
