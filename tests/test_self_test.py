"""Self-test loop tests. Run: python tests/test_self_test.py"""
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.store import BeliefStore, Claim                    # noqa: E402
from persona.membrane import ContradictionEvent                 # noqa: E402
from persona.loops.self_test import (                           # noqa: E402
    run_self_test, apply_result_with_signoff, hypothesize,
    MockDatasetScout, GEODatasetScout, HeuristicTester,
)
from persona.ingest.base import DiskCache                       # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ingest"


def _event():
    return ContradictionEvent("k", "microglia drive neuroinflammation in AD",
                              "true-refutation", 2, 1, "one side single-source")


def test_loop_closes_and_is_human_gated():
    s = BeliefStore()
    res = run_self_test(_event(), MockDatasetScout(), HeuristicTester())
    assert res.dataset is not None and res.outcome == "supports"
    assert res.is_replay is True, "must be honestly labelled a replay without a real backend"
    # no write without human sign-off
    assert apply_result_with_signoff(s, res, human_ok=False, truth=1) is None
    assert s.get_claim("k") is None
    # with sign-off -> written and anchored; a REPLAY result is HUMAN_CONFIRMED (not TESTED,
    # since no data was computed — provenance honesty, v3 T0.3)
    c = apply_result_with_signoff(s, res, human_ok=True, truth=1)
    assert c.provenance_state == "HUMAN_CONFIRMED" and c.anchor
    s.close()


def test_hypothesize_is_falsifiable():
    h = hypothesize(_event())
    assert h.claim_key == "k" and h.predicts != 0 and h.test_description
    assert "dataset" in h.test_description.lower()


def test_geo_scout_live_or_skip():
    hyp = hypothesize(_event())
    scout = GEODatasetScout(cache=DiskCache(root=str(FIXTURES)))
    try:
        hits = scout.search(hyp, limit=3)
        assert isinstance(hits, list)
        print(f"PASS test_geo_scout_live: {len(hits)} GEO dataset candidate(s)"
              + (f"; e.g. {hits[0].accession}" if hits else ""))
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"SKIP test_geo_scout_live: no network ({e})")


if __name__ == "__main__":
    test_loop_closes_and_is_human_gated()
    print("PASS test_loop_closes_and_is_human_gated")
    test_hypothesize_is_falsifiable()
    print("PASS test_hypothesize_is_falsifiable")
    test_geo_scout_live_or_skip()
    print("\nself-test loop tests passed.")
