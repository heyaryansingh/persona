"""Researcher facade end-to-end (offline via the committed fixture cache).
Run: python tests/test_researcher.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.researcher import Researcher                  # noqa: E402
from persona.ingest import EuropePMCAdapter                # noqa: E402
from persona.ingest.base import DiskCache                  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ingest"
CACHED_QUERY = "neuroinflammation AND alzheimer AND microglia"   # matches the committed fixture


def test_full_researcher_cycle():
    with tempfile.TemporaryDirectory() as d:
        r = Researcher(root=d, name="Ada", seed_interests=["neuroinflammation", "microglia", "tau"],
                       adapter=EuropePMCAdapter(cache=DiskCache(root=str(FIXTURES))))
        try:
            summary = r.tick(queries=[CACHED_QUERY])
            assert summary["docs_read"] == 8, summary
            assert summary["candidates"] >= 1

            dash = r.dashboard()
            assert dash["name"] == "Ada" and dash["interests"] and "agenda" in dash

            beliefs = r.beliefs()
            assert isinstance(beliefs, list)
            nb = r.notebook()
            assert any("read 8" in ln for ln in nb)

            # contradictions were flagged -> the handoff inbox has open dossiers
            handoffs = r.handoffs()
            assert len(handoffs) >= 1, "expected at least one contradiction dossier"
            key = handoffs[0]["claim_key"]

            # self-test the loop (replay-labelled, human-gated)
            st = r.self_test(key)
            assert st["is_replay"] is True and st["outcome"] in ("supports", "refutes", "inconclusive")

            # human resolves -> belief anchored
            res = r.resolve_handoff(key, handoffs[0]["candidate_explanations"][0], truth=1)
            assert res["anchor"] and res["provenance_state"] == "HUMAN_CONFIRMED"

            arts = r.artifacts()
            assert "Unresolved dissents" in arts["mini_review"]
        finally:
            r.close()


if __name__ == "__main__":
    test_full_researcher_cycle()
    print("PASS test_full_researcher_cycle")
    print("\nresearcher facade test passed.")
