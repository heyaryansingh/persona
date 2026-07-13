"""F1.10 — `open_from_conflict` seam (contradiction → falsifiable investigation).

Resolves a conflict to a directional question + two opposing stances via the belief graph, fans them
into a branch plan (F1.1), pins the exact colliding claims into the analyze steps, dedups against a
live investigation, and auto-launches. Falls back to a linear plan when the graph can't resolve the
claims. Uses the real in-memory TaskQueue — no mocks on the queue.
"""
import types

from persona import context
from persona.paths import Paths
from persona.daemon.queue import TaskQueue
from persona.research.investigation import Investigation


class _FakeKG:
    def __init__(self, claims):
        self._c = claims

    def provenance(self, cid):
        return self._c.get(cid, {})


def _persona(tmp_path, kg=None):
    p = types.SimpleNamespace()
    p.paths = Paths(tmp_path)
    p.paths.ensure()
    q = TaskQueue(str(tmp_path / "q.db"))
    p.queue = lambda: q
    p.kg = kg
    return p


def _first_investigate_task(queue):
    """Drive the queue past gather/harvest to the first leasable investigate task."""
    for _ in range(20):
        t = queue.lease()
        if t is None:
            return None
        if t.type == "investigate":
            return t
        queue.complete(t.id, "ok")
    return None


def test_branches_and_pins_evidence(tmp_path):
    kg = _FakeKG({"clm_pos": {"subject": "APOE4", "object": "Alzheimer risk", "effect_sign": "+"}})
    p = _persona(tmp_path, kg=kg)
    with context.use(p):
        inv = Investigation.open_from_conflict("cfx1", evidence_claim_ids=["clm_pos", "clm_neg"])
        # resolved → two directional stances → two investigate branches
        analyze = [s for s in inv.meta["steps"] if s["type"] == "investigate"]
        assert len(analyze) == 2
        assert inv.meta["evidence_claim_ids"] == ["clm_pos", "clm_neg"]
        assert inv.meta["origin"]["conflict_id"] == "cfx1"
        # auto-launched: an analyze task carries the pinned evidence + a directional sub-question
        t = _first_investigate_task(p.queue())
        assert t is not None
        assert t.params.get("evidence_claim_ids") == ["clm_pos", "clm_neg"]
        assert t.params.get("question") in ("APOE4 raises Alzheimer risk", "APOE4 lowers Alzheimer risk")


def test_dedups_same_conflict(tmp_path):
    kg = _FakeKG({"c": {"subject": "X", "object": "Y", "effect_sign": "+"}})
    p = _persona(tmp_path, kg=kg)
    with context.use(p):
        a = Investigation.open_from_conflict("cfx", evidence_claim_ids=["c"])
        b = Investigation.open_from_conflict("cfx", evidence_claim_ids=["c"])
        assert a.slug == b.slug                      # idempotent: one investigation, not two


def test_generic_linear_fallback_without_kg(tmp_path):
    p = _persona(tmp_path, kg=None)
    with context.use(p):
        inv = Investigation.open_from_conflict("cfx9", evidence_claim_ids=["c1"])
        analyze = [s for s in inv.meta["steps"] if s["type"] == "investigate"]
        assert len(analyze) == 1                     # unresolved → linear DEFAULT_PLAN
        assert inv.meta["evidence_claim_ids"] == ["c1"]
        assert "cfx9" in inv.question
