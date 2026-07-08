"""T2.3: persistent daily budget accumulates across restarts; escalation ambiguity signal.
Run: python tests/test_budget.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.store import BeliefStore                          # noqa: E402
from persona.budget import DailyBudget                         # noqa: E402
from persona.membrane import Membrane                          # noqa: E402
from persona.swarm.orchestrator import AsyncSwarm              # noqa: E402
from persona.swarm.reader import Candidate                     # noqa: E402
from persona.ingest.base import Document                       # noqa: E402


def test_accumulates_and_caps():
    s = BeliefStore()
    b = DailyBudget(s, cap_usd=1.0)
    assert b.spent_today() == 0.0 and b.can_spend()
    b.add(0.4); b.add(0.4)
    assert abs(b.spent_today() - 0.8) < 1e-9 and b.can_spend()
    b.add(0.3)
    assert b.spent_today() >= 1.0 and not b.can_spend() and b.remaining() == 0.0
    s.close()


def test_persists_across_restart():
    with tempfile.TemporaryDirectory() as d:
        path = str(Path(d) / "s.db")
        s1 = BeliefStore(path); DailyBudget(s1, 5.0).add(2.5); s1.close()
        s2 = BeliefStore(path)
        assert abs(DailyBudget(s2, 5.0).spent_today() - 2.5) < 1e-9, "spend must survive restart"
        s2.close()


def _swarm():
    s = BeliefStore()
    async def _noop(doc):
        return []
    return AsyncSwarm(Membrane(s), extract_fn=_noop, confidence_floor=0.5)


def test_ambiguity_signal():
    sw = _swarm()
    long_doc = Document(doc_id="d", title="t", text="x" * 250, source="s")
    short_doc = Document(doc_id="d", title="t", text="short", source="s")
    lowconf = [Candidate("k", "s", 1.0, "g", "d", confidence=0.3)]
    highconf = [Candidate("k", "s", 1.0, "g", "d", confidence=0.8)]
    assert sw._ambiguous(long_doc, []) is True                # substantive abstract, 0 claims
    assert sw._ambiguous(short_doc, []) is False              # too short to be suspicious
    assert sw._ambiguous(long_doc, lowconf) is True           # all below floor
    assert sw._ambiguous(long_doc, highconf) is False
    sw.store.close()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} budget tests passed.")
