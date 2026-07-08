"""T0.3: the acting loop CLOSES — a signed-off self-test writes back into the belief-state,
with honest provenance (TESTED only when real computation ran). Run: python tests/test_acting_loop.py
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.researcher import Researcher                           # noqa: E402
from persona.ingest import EuropePMCAdapter                         # noqa: E402
from persona.ingest.base import DiskCache                           # noqa: E402
from persona.loops.self_test import SelfTestResult, Hypothesis      # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ingest"


def _researcher(d):
    return Researcher(root=d, adapter=EuropePMCAdapter(cache=DiskCache(root=str(FIXTURES))))


def _pending(claim_key, is_replay):
    hyp = Hypothesis(text=f"{claim_key} tested", claim_key=claim_key, predicts=+1.0,
                     test_description="t")
    return SelfTestResult(hypothesis=hyp, dataset=None, outcome="supports", confidence=0.7,
                          detail="d", is_replay=is_replay)


def test_replay_signoff_writes_human_confirmed_not_tested():
    with tempfile.TemporaryDirectory() as d:
        r = _researcher(d)
        try:
            r._pending_tests["k1"] = _pending("k1", is_replay=True)   # reasoning/replay
            assert r.me.store.get_claim("k1") is None
            out = r.resolve_self_test("k1", human_ok=True, truth=1)
            assert out["written"] is True
            c = r.me.store.get_claim("k1")
            assert c.anchor and c.provenance_state == "HUMAN_CONFIRMED", c.provenance_state
        finally:
            r.close()


def test_real_compute_signoff_writes_tested():
    with tempfile.TemporaryDirectory() as d:
        r = _researcher(d)
        try:
            r._pending_tests["k2"] = _pending("k2", is_replay=False)  # real computation ran
            r.resolve_self_test("k2", human_ok=True, truth=1)
            assert r.me.store.get_claim("k2").provenance_state == "TESTED"
        finally:
            r.close()


def test_decline_does_not_write():
    with tempfile.TemporaryDirectory() as d:
        r = _researcher(d)
        try:
            r._pending_tests["k3"] = _pending("k3", is_replay=True)
            out = r.resolve_self_test("k3", human_ok=False, truth=1)
            assert out["written"] is False and r.me.store.get_claim("k3") is None
        finally:
            r.close()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"\n{len(tests)} acting-loop tests passed.")
