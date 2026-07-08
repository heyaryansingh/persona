"""T4: idea-graph edge build scales (inverted index, not O(n^2)) + stays correct on small input.
Run: python tests/test_idea_graph_scale.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.store import BeliefStore, Claim                          # noqa: E402
from persona.graph.idea_graph import build_idea_graph                 # noqa: E402


def test_shared_entity_edges_are_correct():
    s = BeliefStore()
    s.add_claim(Claim("a", "microglia drive neuroinflammation", entities=["microglia", "neuroinflammation"]))
    s.add_claim(Claim("b", "microglia clear amyloid", entities=["microglia", "amyloid"]))
    s.add_claim(Claim("c", "insulin regulates glucose", entities=["insulin", "glucose"]))
    g = build_idea_graph(s)
    shares = [e for e in g["edges"] if e["kind"] == "shares"]
    pairs = {frozenset((e["source"], e["target"])) for e in shares}
    assert frozenset(("a", "b")) in pairs, "a,b share 'microglia' -> edge"
    assert frozenset(("a", "c")) not in pairs and frozenset(("b", "c")) not in pairs
    s.close()


def test_scales_to_thousands_fast():
    # 3000 claims, 300 entities -> the old O(n^2) scan is ~4.5M pair-checks; the inverted index
    # is far cheaper. Assert it builds well under a generous time budget.
    s = BeliefStore()
    for i in range(3000):
        e1, e2 = f"ent{i % 300}", f"ent{(i * 7) % 300}"
        s.add_claim(Claim(f"c{i}", f"{e1} relates {e2}", entities=[e1, e2]))
    t0 = time.time()
    g = build_idea_graph(s, max_nodes=3000)
    dt = time.time() - t0
    assert len(g["nodes"]) == 3000
    assert g["edges"], "should find shared-entity edges"
    assert dt < 20.0, f"edge build too slow: {dt:.1f}s (inverted index should be fast)"
    print(f"  3000-node graph built in {dt:.2f}s, {len(g['edges'])} edges")
    s.close()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} idea-graph scale tests passed.")
