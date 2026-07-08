"""Inner-loop end-to-end test (offline, deterministic). Run: python tests/test_inner_loop.py

Real papers -> extract -> membrane -> belief + notebook, wired end to end, with a fake
adapter so it needs no network.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.self_state import Self                 # noqa: E402
from persona.membrane import Membrane               # noqa: E402
from persona.swarm.reader import HeuristicExtractor  # noqa: E402
from persona.loops import run_inner_loop            # noqa: E402
from persona.ingest.base import Document            # noqa: E402


class FakeAdapter:
    def __init__(self, docs):
        self._docs = docs

    def search(self, query, limit=8):
        return self._docs[:limit]


def test_inner_loop_reads_extracts_commits():
    docs = [
        Document("A:1", "Microglia and neuroinflammation in Alzheimer",
                 "Microglia increase neuroinflammation in Alzheimer disease.",
                 source="fake", group="Journal_A"),
        Document("B:1", "Microglial drive of neuroinflammation",
                 "Microglia promote neuroinflammation and neurodegeneration.",
                 source="fake", group="Journal_B"),   # 2nd independent group -> converges
        Document("C:1", "A dissenting cohort",
                 "In this cohort, microglia showed no association with neuroinflammation.",
                 source="fake", group="Journal_C"),    # contradicting direction
    ]
    with tempfile.TemporaryDirectory() as d:
        me = Self(d).hydrate()
        try:
            mem = Membrane(me.store)
            summary = run_inner_loop(me, FakeAdapter(docs), HeuristicExtractor(), mem,
                                     queries=["microglia neuroinflammation"], limit=8)
            assert summary.docs_read == 3
            assert summary.candidates >= 2
            assert summary.committed >= 1, "two independent groups agreeing should commit"
            # a belief now exists and the notebook recorded the move
            assert any(c.predicted == 1 for c in me.store.core_claims())
            nb = me.notebook_path.read_text(encoding="utf-8")
            assert "read 3" in nb and "committed" in nb
        finally:
            me.close()   # close SQLite before tempdir cleanup (Windows file lock)


if __name__ == "__main__":
    test_inner_loop_reads_extracts_commits()
    print("PASS test_inner_loop_reads_extracts_commits")
    print("\ninner-loop test passed.")
