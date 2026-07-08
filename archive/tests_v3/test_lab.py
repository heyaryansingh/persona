"""Lab (two researchers) test. Run: python tests/test_lab.py

Two dispositions -> different membrane strictness -> different bodies of belief; their
disagreement is the signal (BUILD_PLAN 7.1).
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.lab import build_default_lab                 # noqa: E402
from persona.ingest import EuropePMCAdapter               # noqa: E402
from persona.ingest.base import DiskCache                 # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ingest"
CACHED_QUERY = "neuroinflammation AND alzheimer AND microglia"


def test_two_researchers_disagree():
    with tempfile.TemporaryDirectory() as d:
        adapter = EuropePMCAdapter(cache=DiskCache(root=str(FIXTURES)))
        lab = build_default_lab(root=d, adapter=adapter)
        try:
            lab.run([CACHED_QUERY])
            ada, bo = lab.researchers
            # skeptic (Ada, quorum 3) commits no more than the explorer (Bo, quorum 2)
            n_ada = len(ada.me.store.core_claims())
            n_bo = len(bo.me.store.core_claims())
            assert n_ada <= n_bo, (n_ada, n_bo)
            dis = lab.disagreements()
            assert len(dis) >= 1, "expected the two dispositions to diverge"
            assert any(x.kind == "coverage" for x in dis)
        finally:
            lab.close()


if __name__ == "__main__":
    test_two_researchers_disagree()
    print("PASS test_two_researchers_disagree")
    print("\nlab test passed.")
