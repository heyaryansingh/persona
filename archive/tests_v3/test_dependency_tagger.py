"""T0.5: the dependency tagger writes candidate edges so load_bearing/VoI light up.
Run: python tests/test_dependency_tagger.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.store import BeliefStore, Claim                                  # noqa: E402
from persona.engine.dependency import load_bearing                           # noqa: E402
from persona.swarm.dependency_tagger import (tag_dependencies,               # noqa: E402
    HeuristicDependencyTagger, candidate_pairs)


def _store():
    s = BeliefStore()
    data = [("f", "amyloid accumulates in alzheimer", ["amyloid", "alzheimer"], "HUMAN_CONFIRMED", True, 5),
            ("d1", "microglia respond to amyloid", ["microglia", "amyloid"], "READ", False, 2),
            ("d2", "microglia drive neuroinflammation", ["microglia", "neuroinflammation"], "READ", False, 1)]
    for cid, stmt, ents, prov, anc, n in data:
        s.add_claim(Claim(cid, stmt, logit=(6.0 if anc else 1.0), provenance_state=prov,
                          anchor=anc, entities=ents))
        for k in range(n):
            s.add_source(cid, f"{cid}_{k}", f"g_{cid}_{k}")
    return s


def test_load_bearing_empty_without_edges():
    s = _store()
    assert load_bearing(s) == {}, "no dependency edges -> load_bearing must be empty (audit #5 baseline)"
    s.close()


def test_tagger_creates_edges_and_lights_up_load_bearing():
    s = _store()
    n = tag_dependencies(s, HeuristicDependencyTagger())
    assert n >= 1, "heuristic must find at least one dependency among these foundational/derived claims"
    lb = load_bearing(s)
    assert lb, "after tagging, load_bearing is non-empty (the flagship graph lights up)"
    # the foundation everything derives toward is scored (load_bearing up-weights under-replicated
    # foundations via inv_support, so it need not be the max — but it must be present and non-trivial)
    assert lb.get("f", 0) > 0, lb
    s.close()


def test_tagging_is_idempotent():
    s = _store()
    a = tag_dependencies(s, HeuristicDependencyTagger())
    b = tag_dependencies(s, HeuristicDependencyTagger())   # re-run adds nothing new
    assert b == 0, f"re-tagging must be a no-op, added {b}"
    s.close()


def test_candidate_pairs_only_co_mentions():
    s = _store()
    pairs = candidate_pairs(s)
    for a, b in pairs:
        ea = {e.lower() for e in a.entities}
        eb = {e.lower() for e in b.entities}
        assert ea & eb, "candidate pairs must share an entity"
    s.close()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} dependency-tagger tests passed.")
