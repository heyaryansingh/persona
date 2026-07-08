"""Idea-graph builder test. Run: python tests/test_idea_graph.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.store import BeliefStore                     # noqa: E402
from persona.membrane import Membrane                     # noqa: E402
from persona.swarm.reader import Candidate                # noqa: E402
from persona.graph import build_idea_graph                # noqa: E402

_N = [0]


def _cand(key, stmt, group):
    _N[0] += 1
    return Candidate(key, stmt, +1.0, group, f"{group}:d{_N[0]}", confidence=0.7)


def test_idea_graph_has_nodes_and_entity_edges():
    s = BeliefStore()
    m = Membrane(s)
    # two claims sharing the entity "neuroinflammation"; one unrelated
    for g in ("A", "B"):
        m.submit(_cand("k1", "microglia increase neuroinflammation", f"J_{g}"))
        m.submit(_cand("k2", "neuroinflammation increases tau pathology", f"J_{g}"))
        m.submit(_cand("k3", "amyloid beta forms plaques", f"J_{g}"))
    m.harvest()
    g = build_idea_graph(s)
    ids = {n["id"] for n in g["nodes"]}
    assert {"k1", "k2", "k3"} <= ids, ids
    # k1 and k2 share "neuroinflammation" -> an edge; k3 shares nothing with them
    entity_edges = {(e["source"], e["target"]) for e in g["edges"] if e["kind"] == "shares"}
    linked = entity_edges | {(b, a) for a, b in entity_edges}
    assert ("k1", "k2") in linked or ("k2", "k1") in linked, entity_edges
    assert ("k1", "k3") not in linked and ("k3", "k1") not in linked
    # nodes carry temporal + provenance info for the scrubber
    n1 = next(n for n in g["nodes"] if n["id"] == "k1")
    assert n1["provenance_state"] and "state" in n1 and n1["entities"]
    assert isinstance(g["timeline"], list) and len(g["timeline"]) >= 1
    s.close()


if __name__ == "__main__":
    test_idea_graph_has_nodes_and_entity_edges()
    print("PASS test_idea_graph_has_nodes_and_entity_edges")
    print("\nidea-graph test passed.")
