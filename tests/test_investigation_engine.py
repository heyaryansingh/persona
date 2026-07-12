"""The investigation/team engine: a research program is a dependency-chained team of role-steps.

Offline (no model calls, no FalkorDB): create an Investigation, launch it into a real TaskQueue, and
assert the steps lease in strict plan order (the team runs the pipeline gather→…→finalize), that a
step is blocked until its predecessor completes, and that finalize aggregates into findings.md.
"""
import types
from pathlib import Path

from persona import context
from persona.paths import Paths
from persona.daemon.queue import TaskQueue
from persona.research.investigation import Investigation, DEFAULT_PLAN


def _stub_persona(tmp_path: Path):
    p = types.SimpleNamespace()
    p.paths = Paths(tmp_path)
    p.paths.ensure()
    return p


def test_investigation_launches_a_dependency_chained_team(tmp_path):
    with context.use(_stub_persona(tmp_path)):
        q = TaskQueue(str(tmp_path / "q.db"))
        inv = Investigation.create("What bounds f(n) for the Erdős–Straus equation?",
                                   specialization="number theory")
        # the folder + legible docs exist
        assert (inv.folder / "investigation.json").exists()
        assert (inv.folder / "question.md").exists()
        assert (inv.folder / "plan.md").exists()

        ids = inv.launch(q)
        assert len(ids) == len(DEFAULT_PLAN)

        # the steps must lease in EXACT plan order — each blocked until the previous completes
        leased_types = []
        guard = 0
        while guard < 50:
            guard += 1
            t = q.lease()
            if t is None:
                break
            leased_types.append(t.type)
            q.complete(t.id, f"ok:{t.type}")
        assert leased_types == [s[1] for s in DEFAULT_PLAN], leased_types

        # finalize aggregates the outcomes into a findings doc and closes the investigation
        inv2 = Investigation.load(inv.slug)
        inv2.finalize(q)
        assert inv2.meta["status"] == "done"
        assert (inv.folder / "findings.md").exists()
        steps = q.investigation_steps(inv.id)
        assert len(steps) == len(DEFAULT_PLAN)
        assert all(s["status"] == "done" for s in steps)


def test_dependent_step_blocks_until_predecessor_done(tmp_path):
    with context.use(_stub_persona(tmp_path)):
        q = TaskQueue(str(tmp_path / "q.db"))
        inv = Investigation.create("Q?", specialization="x")
        inv.launch(q)
        first = q.lease()                     # gather
        assert first.type == "gather"
        assert q.lease() is None              # harvest is blocked until gather completes
        q.complete(first.id, "ok")
        second = q.lease()
        assert second.type == "harvest"
