"""F1.1 — branching/DAG investigations.

A question with ≥2 independent sub-hypotheses fans out into one `investigate` branch per hypothesis
(all sharing the harvest step), joined by a single synthesize step (the DAG join the queue's lease()
already supports). <2 sub-hypotheses falls back to the linear DEFAULT_PLAN, byte-identical to today.
No model calls — pure plan construction + the real in-memory TaskQueue.
"""
import types

from persona import context
from persona.paths import Paths
from persona.daemon.queue import TaskQueue
from persona.research.investigation import Investigation, DEFAULT_PLAN


def _stub_persona(tmp_path):
    p = types.SimpleNamespace()
    p.paths = Paths(tmp_path)
    p.paths.ensure()
    return p


def test_branch_plan_shape(tmp_path):
    with context.use(_stub_persona(tmp_path)):
        inv = Investigation.create("Does X cause Y?",
                                   sub_hypotheses=["X raises Y", "X lowers Y"])
        steps = inv.meta["steps"]
        analyze = [s for s in steps if s["type"] == "investigate"]
        harvest = next(s for s in steps if s["type"] == "harvest")
        synth = next(s for s in steps if s["type"] == "consolidate")
        # one branch per sub-hypothesis, each carrying its own question, each after harvest
        assert len(analyze) == 2
        assert {s["q"] for s in analyze} == {"X raises Y", "X lowers Y"}
        assert all(s["deps"] == [harvest["idx"]] for s in analyze)
        # a SINGLE synthesize step joins BOTH branches (the DAG join)
        assert sorted(synth["deps"]) == sorted(s["idx"] for s in analyze)


def test_default_plan_byte_identical(tmp_path):
    with context.use(_stub_persona(tmp_path)):
        inv = Investigation.create("a plain linear question")
        # no branch metadata leaks onto the default path
        assert all("deps" not in s and "q" not in s for s in inv.meta["steps"])
        assert [s["type"] for s in inv.meta["steps"]] == [t for _, t, _ in DEFAULT_PLAN]
        # plan.md renders exactly as the legacy format for the linear plan
        expected = "# plan\n\n" + "".join(
            f"{i+1}. **{r}** — {d}\n" for i, (r, t, d) in enumerate(DEFAULT_PLAN))
        assert (inv.folder / "plan.md").read_text(encoding="utf-8") == expected


def test_single_sub_hypothesis_falls_back_to_linear(tmp_path):
    with context.use(_stub_persona(tmp_path)):
        inv = Investigation.create("q", sub_hypotheses=["only one"])
        assert [s["type"] for s in inv.meta["steps"]] == [t for _, t, _ in DEFAULT_PLAN]


def test_branch_dag_join(tmp_path):
    """The synthesize join must lease ONLY after BOTH analyze branches reach a terminal state —
    exercises queue.lease()'s real DAG join, no mocks."""
    with context.use(_stub_persona(tmp_path)):
        q = TaskQueue(str(tmp_path / "q.db"))
        inv = Investigation.create("Does X cause Y?",
                                   sub_hypotheses=["X raises Y", "X lowers Y"])
        inv.launch(q)
        # synthesize was enqueued depending on BOTH analyze task-ids
        by_type = {}
        for s in inv.meta["steps"]:
            by_type.setdefault(s["type"], []).append(s)
        analyze_tids = {s["task_id"] for s in by_type["investigate"]}
        assert len(analyze_tids) == 2

        leased_types = []
        analyze_done = 0
        synth_leased_after = None
        for _ in range(60):
            t = q.lease()
            if t is None:
                break
            leased_types.append(t.type)
            if t.type == "consolidate":
                synth_leased_after = analyze_done          # how many branches were done first
            q.complete(t.id, f"ok:{t.type}")
            if t.type == "investigate":
                analyze_done += 1
        # the join saw BOTH branches complete before it became leasable
        assert synth_leased_after == 2, leased_types
        # and it ran strictly after both branches
        last_analyze = max(i for i, ty in enumerate(leased_types) if ty == "investigate")
        assert leased_types.index("consolidate") > last_analyze
