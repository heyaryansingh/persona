"""exp_multipersona_isolation (v5 P3, gating) — two personas share ZERO mutable state.

Creates two personas via the manager, writes different claims/events/spend to each (under each's
context), then asserts their knowledge graphs, event logs, budgets, and workspaces are disjoint.
This is the whole multi-persona claim: isolated minds in one process. Deterministic (no reads).
Run: python experiments/exp_multipersona_isolation.py    (needs FalkorDB on :6379)
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from persona import context, selfmind                                 # noqa: E402
from persona.manager import PersonaManager                            # noqa: E402
from persona.memory import membrane                                   # noqa: E402


def _write(p, subj, obj, sign, lab):
    with context.use(p):
        kg = p.kg
        kg.upsert_source({"slug": f"s_{subj}_{lab}", "title": "t", "year": 2024, "affiliations": [lab]})
        kg.add_claim({"claim_id": "x", "subject": subj, "relation": "affects", "object": obj,
                      "effect_sign": sign, "confidence": 0.8, "provenance": "READ"}, f"s_{subj}_{lab}")
        p.events.emit("claim", f"{subj} {obj}")
        p.budget.add(0.01)


def main():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        mgr = PersonaManager(root=Path(d))
        a = mgr.create("Alice", interests=["photonics"])
        b = mgr.create("Bob", interests=["genomics"])
        print(f"created: {a.id} (graph {a.graph_name}), {b.id} (graph {b.graph_name})")
        # clean each graph
        for p in (a, b):
            p.kg.g.query("MATCH (n) DETACH DELETE n")

        # Alice learns 3 distinct claims; Bob learns 1
        _write(a, "laser", "coherence", "+", "MIT")
        _write(a, "photon", "entanglement", "+", "Caltech")
        _write(a, "cavity", "loss", "-", "Stanford")
        _write(b, "gene", "expression", "+", "Broad")

        # assertions
        sa, sb = a.kg.stats(), b.kg.stats()
        print(f"Alice KG: {sa}  |  Bob KG: {sb}")
        ok_graph = sa["claims"] == 3 and sb["claims"] == 1
        ok_events = a.events.latest_id() == 3 and b.events.latest_id() == 1
        ok_budget = abs(a.budget.spent_today() - 0.03) < 1e-9 and abs(b.budget.spent_today() - 0.01) < 1e-9
        ok_paths = a.paths.workspace != b.paths.workspace and a.graph_name != b.graph_name
        with context.use(a):
            ok_self_a = [n for n, _ in selfmind.interests()] == ["photonics"]
        with context.use(b):
            ok_self_b = [n for n, _ in selfmind.interests()] == ["genomics"]
        print(f"graphs disjoint: {ok_graph} | events disjoint: {ok_events} | "
              f"budgets disjoint: {ok_budget} | paths/graph disjoint: {ok_paths} | "
              f"selves disjoint: {ok_self_a and ok_self_b}")
        # registry persistence
        mgr2 = PersonaManager(root=Path(d))
        ok_persist = {p.id for p in mgr2.list()} == {a.id, b.id}
        print(f"registry persists across reload: {ok_persist}")
        for p in (a, b):
            p.kg.g.query("MATCH (n) DETACH DELETE n")
        allok = ok_graph and ok_events and ok_budget and ok_paths and ok_self_a and ok_self_b and ok_persist
        print(f"\nVERDICT: {'PASS' if allok else 'FAIL'} — two personas are fully isolated")
        assert allok


if __name__ == "__main__":
    main()
