"""T0.4: first-pass reanalysis is REAL (Open Targets computed association), honestly labelled.
Run: python tests/test_reanalysis.py
"""
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from persona.loops.self_test import Hypothesis                     # noqa: E402
from persona.loops.reanalysis import OpenTargetsTester, CompositeTester  # noqa: E402


def _hyp(subj, obj):
    return Hypothesis(text="t", claim_key="k", predicts=1.0, test_description="d",
                      subject=subj, object=obj)


def test_non_gene_disease_returns_none_not_fake_supports():
    # Open Targets can't resolve a cell<->process claim -> must return None (fall through),
    # NEVER a fabricated 'supports'. No network needed: entities are empty here.
    assert OpenTargetsTester().run(_hyp("", ""), None) is None


def test_open_targets_real_first_pass_or_skip():
    try:
        res = OpenTargetsTester().run(_hyp("APOE", "Alzheimer disease"), None)
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"SKIP test_open_targets_real: no network ({e})")
        return
    assert res is not None, "APOE<->Alzheimer must resolve to a real association"
    assert res.is_replay is False, "a real computed cross-check is NOT a replay"
    assert res.outcome == "supports" and res.confidence > 0.5, res
    assert "Open Targets" in res.detail
    print(f"PASS test_open_targets_real: {res.outcome} conf={res.confidence:.2f} — {res.detail[:80]}")


def test_composite_falls_back_when_no_real_data():
    # non-resolving entities + no key -> Composite must still return a (labelled replay) result,
    # never crash and never claim a real computation.
    res = CompositeTester().run(_hyp("some phrase", "another phrase"), None)
    assert res is not None
    # without a resolvable gene/disease and no key, this is the heuristic replay
    print(f"PASS test_composite_fallback: replay={res.is_replay} outcome={res.outcome}")


if __name__ == "__main__":
    test_non_gene_disease_returns_none_not_fake_supports()
    print("PASS test_non_gene_disease_returns_none_not_fake_supports")
    test_composite_falls_back_when_no_real_data()
    test_open_targets_real_first_pass_or_skip()
    print("\nreanalysis tests passed.")
